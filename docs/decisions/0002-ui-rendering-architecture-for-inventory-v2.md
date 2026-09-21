---
title: "Use server-rendered Jinja + USWDS with JavaScript islands for the Inventory v2 metadata editor"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Input Validation and Output Handling"
nist_controls: ["SI-10", "SI-15", "SC-18", "AU-2", "AU-3", "AC-12", "SA-8", "SA-15"]
impact_level: "moderate"
ato_relevance: "yes-internal"
risk_treatment: "mitigate"
---

# Use server-rendered Jinja + USWDS with JavaScript islands for the Inventory v2 metadata editor

> **Status note:** This record is `proposed`, not `accepted`. The decision is
> downstream of an unresolved *product* question (see
> [Unresolved question: which editing model?](#unresolved-question-which-editing-model)).
> The outcome below records the engineering recommendation and the explicit
> conditions that would change it. Do not mark this `accepted` until the
> editing model is confirmed.

## Context and Problem Statement

Inventory v2 replaces the current CKAN 2.11.5 implementation with a custom
application whose central feature is DCAT-US 3.0 catalog authoring "by class and
re-use" — a metadata model of nested, independently reusable objects
(`Dataset`, `DatasetSeries`, `DataService`, `Distribution`, `Kind`,
`Organization`, `Concept`, `Location`). We must decide how the authoring UI is
rendered: server-rendered HTML with progressive enhancement, or a client-side
single-page application.

This decision is being recorded because an earlier framing of it was wrong and
should not be relied on. The v1 pain-point list cites both "UI revamp/rewrite
required to be 508 compliant" and "custom React app data entry form... will need
complete re-write for 3.0," which invites the inference that React caused the
accessibility problem. It did not. [U.S. Web Design System](https://designsystem.digital.gov/)
(USWDS) is CSS plus vanilla JS and has a mature React binding
([`@trussworks/react-uswds`](https://github.com/trussworks/react-uswds)) used
widely across federal projects. **USWDS adoption and rendering architecture are
independent choices.** The v1 form's need for a rewrite was caused by
hard-coding DCAT-US 1.1 field structure into components, not by its framework;
a schema-coupled server-rendered form would need the same rewrite.

## Decision Drivers

- **Single source of truth for validation (SI-10).** The authoritative DCAT-US
  validator is Python: `ckanext/datagov_inventory/dcat/validator.py` (620 lines,
  772 lines of tests) using `jsonschema` Draft 2020-12 with `referencing`. Any
  second validator implementation in JavaScript creates two artifacts that will
  drift, and drift in a validator is a correctness failure that reaches agency
  publishers as bad exports.
- **Single source of truth for schema interpretation.** The wiki requires field
  descriptions to be sourced *from the schema definition* so that DCAT-US 3.0
  point releases are absorbed by bumping the `_external/dcat-us` submodule. This
  means a schema → form-model renderer exists; the question is whether it exists
  once or twice.
- **Section 508 / WCAG 2.1 AA conformance** is the top-stated v1 pain point and
  a statutory obligation, not a quality goal.
- **Auditability of in-progress work (AU-2, AU-3).** The v2 data model records
  an append-only `object_version` history with `editor_user_id`. Drafts that
  exist only in a client-side buffer are absent from that audit trail until
  submitted.
- **Session timeout interaction (AC-12).** v1 enforces a 900-second idle
  timeout (`config/ckan.ini:33-35`). Long metadata forms and short idle
  timeouts interact badly; the mitigation differs by architecture.
- **Output sanitization (SI-15, SC-18).** Rendering untrusted metadata
  (agency-supplied strings, URLs) requires contextual escaping wherever it is
  rendered. Rendering in one place is easier to review than two.
- **Platform consistency (SA-8, SA-15).** `catalog.data.gov`
  ([GSA/datagov-catalog](https://github.com/GSA/datagov-catalog)) is Flask +
  Jinja + USWDS + HTMX with `pa11y-ci` and `axe-playwright-python` in CI;
  `harvest.data.gov` ([GSA/datagov-harvester](https://github.com/GSA/datagov-harvester))
  is Flask server-rendered. A third pattern means a third build chain, a third
  accessibility-test setup, and a third on-call skill set.
- **Anonymous browser-memory editing.** The wiki specifies public catalogs
  "stored in browser memory" with no backend — inherently a client-side
  capability. The wiki feature table marks it **Long Term: Yes / MVP: No**;
  the team has since scheduled it as **2.1** — i.e. the increment immediately
  following MVP. See [Reversal condition triggered](#reversal-condition-triggered).
- **Interaction richness required by the editing model.** Reference pickers,
  `Location` geometry/bbox entry, and a "show what this will look like in
  catalog" preview are genuinely interactive. How interactive the *core* editing
  loop must be is the unresolved question below.

## Considered Options

1. **Server-rendered Jinja + USWDS + HTMX, with scoped JavaScript islands.**
   Flask renders pages and form partials. HTMX handles partial swaps and
   autosave. Discrete mounted components ("islands") handle the few genuinely
   interactive widgets. One Python schema-renderer, one Python validator.

2. **Full single-page application (React + `@trussworks/react-uswds`)**
   against a stateless JSON API. Client owns routing and editing state. The
   Python validator remains authoritative and is called over HTTP; optionally a
   client-side `ajv` pre-check provides instant feedback.

3. **Stateless HTMX round-trip.** Server-rendered with *no* server-side
   persistence of in-progress state: the browser holds the catalog in IndexedDB
   and POSTs the relevant subtree on each interaction; the server renders HTML
   back and stores nothing. This is the shape that would let one codebase serve
   both authenticated and anonymous users.

## Decision Outcome

Chosen option: **Option 1 — server-rendered Jinja + USWDS + HTMX with scoped
JavaScript islands**, conditional on the editing model being the *decomposed*
one (see below), because it keeps schema interpretation and validation in a
single Python implementation, starts from accessible native HTML, makes draft
autosave auditable by construction, and matches the two sibling Data.gov
applications.

Three commitments make this choice reversible at low cost, and they are part of
the decision rather than implementation detail:

- **API-first.** All DCAT logic lives in a pure-Python library with no web
  framework dependency (validate, 1.1→3.0 transform, decompose/assemble object
  graph, schema→form-model), exposed through a stateless APIFlask surface:
  `POST /api/validate`, `POST /api/convert`, `POST /api/export`,
  `GET /api/schema/{class}/form`.
- **`GET /api/schema/{class}/form` returns the form model as JSON**, not only
  rendered HTML. The Jinja renderer consumes it server-side today; a future SPA
  or the anonymous client consumes the identical endpoint. This is the single
  piece of extra discipline that preserves optionality.
- **Islands are mounted components, not a router.** An island owns a widget; it
  never owns the page. Initial scope: the class-reference picker (search and
  attach an existing reusable object), `Location` geometry/bbox entry, and the
  catalog preview. `@trussworks/react-uswds` is acceptable inside an island.

### Unresolved question: which editing model?

"Entry by class and re-use" admits two materially different products, and the
rendering decision follows from it:

- **(A) Decomposed.** You edit one `Dataset` on its own page, then *attach* an
  existing `Kind` or `Organization` from a picker. Each screen is small and
  shallow. Option 1 fits well and an SPA buys little.
- **(B) Unified editor.** One workspace: live catalog tree, detail pane, inline
  nested editing, instant preview. Option 2 is the right tool and
  server-rendering fights the interaction model.

The engineering lean toward (A) is not merely a preference for Option 1: reuse
is only a coherent requirement if objects have independent identity and their
own edit surface, which is what (A) describes. But this is a product and user-
research call, and it has not been made.

### Conditions that reverse this decision

Adopt **Option 2** if any of the following becomes true:

- The confirmed editing model is **(B) unified editor**.
- Anonymous browser-memory editing is pulled into the MVP or the immediately
  following increment, rather than remaining "long term."
- Team staffing is materially React-strong and Jinja-weak, which would invert
  the platform-consistency driver.

### Reversal condition triggered

**The second reversal condition above has been met.** The team has scheduled
anonymous browser-memory editing as **2.1** — the increment immediately following
MVP — rather than as indefinite "long term" work. That is precisely the trigger
this record named.

This does not automatically select Option 2, but it changes the weighing in three
ways and this record must not be accepted without addressing them:

1. **The deferred cost is now dated.** The "acknowledged debt" in Negative
   Consequences below is no longer an open-ended maybe; it lands one increment
   after MVP. Building the MVP in a way that makes that increment cheap is worth
   more than it appeared when the feature was undated.
2. **Option 3 (stateless HTMX round-trip) moves from an also-ran to a serious
   contender**, because it is the option that serves both the authenticated and
   anonymous cases from one codebase. Its cost — anonymous draft metadata
   transiting the server while the wiki promises browser-only storage, with the
   attendant logging/APM exclusion obligation and ATO boundary review — must now
   be priced rather than noted.
3. **The `GET /api/schema/{class}/form` commitment stops being cheap insurance
   and becomes load-bearing.** It is the seam the 2.1 client will be built
   against. It should be designed and tested as a real contract in MVP, not
   added as an afterthought.

Two paths remain defensible, and choosing between them is a scheduling judgement
as much as a technical one:

- **Stay with Option 1 for MVP**, treat the API-first commitments as firm
  requirements rather than hedges, and build the 2.1 anonymous client as a
  separate small client against the same stateless API. Accepts some duplication
  of form-rendering logic in exchange for an accessible, conventional MVP.
- **Adopt Option 2 now**, accepting a higher MVP accessibility burden in exchange
  for one editing implementation serving both audiences.

This should be decided together with the editing-model question, since (B) plus
2.1 anonymous editing points clearly at Option 2, whereas (A) plus 2.1 does not.

### Positive Consequences

- One validator and one schema interpreter. DCAT-US 3.0 point releases are
  absorbed by a submodule bump plus a Python change, in one place.
- Forms begin as native HTML — real `<label>` association, native focus order,
  native validation, functional without JS — so accessibility work is *reducing
  regressions* rather than *reconstructing semantics*.
- The accessibility surface requiring bespoke audit shrinks to three islands
  instead of the whole application.
- Server-side autosave into `object_version` (with
  `change_summary='autosave'`) means long-form work survives the AC-12 idle
  timeout **and** appears in the audit trail — a v1 complaint and a compliance
  gap closed by one mechanism.
- Tooling, CI accessibility gates, and operational runbooks are shared with
  `datagov-catalog`.
- No client-side build chain, bundler, or JS dependency tree on the critical
  path for the MVP.

### Negative Consequences

- **Every meaningful validation is a network round-trip.** Mitigated, not
  eliminated, by the fact that authoritative validation is a round-trip in
  Option 2 as well — but Option 2 can offer an instant approximate check and
  Option 1 cannot.
- **Option 1 does not directly serve the anonymous browser-memory feature.** An
  earlier characterization of this as "the same forms with an IndexedDB storage
  adapter" was hand-waving and is withdrawn. When that feature is scheduled it
  requires either the Option 3 round-trip (with the data-flow consequence noted
  below) or a separate client. This is a real, acknowledged debt — **and it is
  now dated at 2.1**, not open-ended; see
  [Reversal condition triggered](#reversal-condition-triggered).
- **USWDS JS components must be re-initialized after HTMX swaps.** A known,
  solved problem, but a recurring source of subtle breakage that needs an
  explicit pattern and a test.
- **HTMX is not accessible by default.** A partial swap that does not move
  focus or announce via `aria-live` fails the same WCAG criteria an SPA would.
  Option 1 buys a better *starting point*, not an outcome; focus and
  announcement handling must be an explicit, tested requirement.
- Two rendering idioms coexist (Jinja partials and island components). Boundary
  discipline is required to keep islands from growing into a de facto SPA.

### Compliance Consequences

- **SI-10 (Input Validation)** — *addressed.* A single authoritative
  server-side validator; no client-side validator is trusted for correctness.
  Client-side checks, if ever added, are advisory only.
- **SI-15 / SC-18 (Output Filtering / Mobile Code)** — *addressed.* Jinja
  autoescaping covers the primary render path; the reduced JS surface narrows
  where DOM-injection review is needed. Island code remains in scope for review.
- **AU-2 / AU-3 (Audit Events / Content)** — *strengthened.* Server-side
  autosave puts in-progress edits in the `object_version` trail with
  `editor_user_id` and timestamp, rather than leaving them invisible in a
  client buffer.
- **AC-12 (Session Termination)** — *mitigated.* Autosave decouples "work
  preserved" from "session alive," so the 900-second idle timeout can be
  retained without data loss as the justification for relaxing it.
- **Section 508 / WCAG 2.1 AA** — verification is required regardless of
  option. `pa11y-ci` plus `axe` in CI as blocking gates, matching
  `datagov-catalog`, with manual keyboard and screen-reader testing on each
  island. This decision does not by itself establish conformance.
- **Boundary implication of Option 3 (for future reference).** Under Option 3,
  anonymous users' draft metadata transits the server while the wiki promises
  browser-only storage. That must be provably excluded from application logs,
  New Relic traces, and any persistence — a data-flow claim requiring
  verification and an ATO boundary review. Option 1 as scoped for the MVP does
  not create this exposure.
- **ATO documentation.** `ato_relevance: yes-internal` for the MVP scope.
  Revisit to `yes-boundary` if Option 3 is adopted for anonymous editing.

## Links

- [Inventory Beta Re-design](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design) — v2 feature list and user/data management model
- [DCAT-US 3.0](https://github.com/GSA/data.gov/wiki/DCAT-US-3.0) and [GSA/dcat-us](https://github.com/GSA/dcat-us) — schema and `_external/dcat-us` submodule source
- [GSA/datagov-catalog](https://github.com/GSA/datagov-catalog) — sibling Flask + Jinja + USWDS + HTMX application; precedent for this option
- [GSA/datagov-harvester](https://github.com/GSA/datagov-harvester) — sibling Flask application; owns the shared harvest DB
- [USWDS](https://designsystem.digital.gov/) and [`@trussworks/react-uswds`](https://github.com/trussworks/react-uswds) — design system and its React binding
- `ckanext/datagov_inventory/dcat/` — validator, transforms, and converter to be extracted as the pure-Python library
- NIST SP 800-53 Rev 5.2 — SI-10, SI-15, SC-18, AU-2, AU-3, AC-12, SA-8, SA-15
- Section 508 / WCAG 2.1 AA — [Section 508 standards](https://www.section508.gov/)
- Related pending ADRs: Login.gov OIDC over SAML; object-graph data model; quarantine-then-scan antivirus
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
