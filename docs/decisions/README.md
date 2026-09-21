# Architecture Decision Records

Decision records for the inventory.data.gov v2 re-design, using
[MADR](https://adr.github.io/madr/) format with federal compliance frontmatter
extensions (`nist_controls`, `impact_level`, `ato_relevance`, `risk_treatment`).

ADR numbers are sequential and are never reused, including for superseded
records, to preserve the audit trail.

> **These documents are temporarily hosted in the v1 repository.**
> [ADR 0001](0001-repository-topology-for-inventory-v2.md) decides that v2 is
> built in a new repository (`GSA/datagov-inventory`); this `docs/` tree moves
> there once it exists. All v1 code citations are pinned to
> [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c)
> (2026-09-04) so they stay accurate after the move.

## Records

| # | Title | Status | Date | ATO | NIST controls |
|---|-------|--------|------|-----|---------------|
| [0001](0001-repository-topology-for-inventory-v2.md) | Build Inventory v2 in a new GSA/datagov-inventory repository | proposed | 2026-09-21 | yes-internal | CM-2, CM-3, CM-9, AC-3, SA-5, SA-8, SR-3, RA-5 |
| [0002](0002-ui-rendering-architecture-for-inventory-v2.md) | Use server-rendered Jinja + USWDS with JavaScript islands for the Inventory v2 metadata editor | proposed | 2026-09-21 | yes-internal | SI-10, SI-15, SC-18, AU-2, AU-3, AC-12, SA-8, SA-15 |
| [0003](0003-login-gov-oidc-instead-of-saml.md) | Use Login.gov OpenID Connect instead of SAML 2.0 for Inventory v2 authentication | proposed | 2026-09-21 | yes-internal | IA-2, IA-2(1), IA-2(12), IA-5, IA-8, SC-8, SC-12, SC-13, SC-17, AC-12 |
| [0004](0004-jit-user-provisioning-and-catalog-rbac.md) | Provision user accounts just-in-time on first Login.gov authentication, with authorization held in per-catalog permissions | proposed | 2026-09-21 | yes-internal | AC-2, AC-2(3), AC-3, AC-6, AC-5, AU-2, AU-3, IA-8, PS-4 |
| [0005](0005-object-graph-data-model-for-dcat-us-3.md) | Store DCAT-US 3.0 metadata as a versioned object graph in Postgres | proposed | 2026-09-21 | yes-internal | AU-2, AU-3, AU-10, AC-3, SI-10, SI-12, CM-3, SC-28 |
| [0006](0006-quarantine-then-scan-antivirus.md) | Scan uploaded data files with a quarantine-then-scan antivirus service and cap hosted files at 500 MB | proposed | 2026-09-21 | **yes-boundary** | SI-3, SI-3(1), SI-3(2), SI-7, SI-10, SC-7, AC-3, AU-2, AU-3, IR-4, IR-6 |
| [0007](0007-retire-tabular-datastore-api.md) | Retire the tabular DataStore API in Inventory v2 | proposed | 2026-09-21 | **yes-boundary** | CM-7, SA-8, AC-3, SI-10, CM-4 |
| [0008](0008-onboard-via-data-json-reimport.md) | Onboard agencies by re-importing published data.json rather than migrating from CKAN | proposed | 2026-09-21 | yes-internal | CM-3, SI-10, SI-12, CP-9, CM-4, SA-8 |
| [0009](0009-terraform-cloudgov-for-infrastructure.md) | Provision cloud.gov infrastructure with GSA-TTS/terraform-cloudgov modules | proposed | 2026-09-21 | **yes-boundary** | CM-2, CM-3, CM-6, CM-8, CM-9, SC-7, SC-12, SC-28, AC-3, AC-5, SA-8, SR-3 |

**By status:** 9 proposed, 0 accepted, 0 deprecated, 0 superseded.

**Boundary-affecting:** ADR 0006 (new in-boundary scanner component and outbound
signature-update flow), ADR 0007 (a brokered data store and a public API endpoint
leave the boundary), and ADR 0009 (egress allowlist and container-network policies
become managed boundary controls). All three require SSP component-inventory and
data-flow diagram updates and should be reviewed by the ISSO.

## Reading order

For a reviewer coming to this cold, [`docs/architecture.md`](../architecture.md)
first, then the records in numeric order. 0001 is deliberately first because it
determines where every other decision is recorded and built. 0005 is the
technical core — the CKAN data-model mismatch is the reason v2 exists at all.

## Controls referenced across all records

`AC-2`, `AC-2(3)`, `AC-3`, `AC-5`, `AC-6`, `AC-12`, `AU-2`, `AU-3`, `AU-10`,
`CM-2`, `CM-3`, `CM-4`, `CM-6`, `CM-7`, `CM-8`, `CM-9`, `CP-9`, `IA-2`,
`IA-2(1)`, `IA-2(12)`, `IA-5`, `IA-8`, `IR-4`, `IR-6`, `PS-4`, `RA-5`, `SA-5`,
`SA-8`, `SA-15`, `SC-7`, `SC-8`, `SC-12`, `SC-13`, `SC-17`, `SC-18`, `SC-28`,
`SI-3`, `SI-3(1)`, `SI-3(2)`, `SI-7`, `SI-10`, `SI-12`, `SI-15`

## Blockers before any record is accepted

Every record is `proposed`. These are verification tasks that gate acceptance,
not follow-ups. Each should be a tracked issue (AGENTS.md §15.5).

| ADR | Blocker | Type |
|-----|---------|------|
| 0001 | Request `GSA/datagov-inventory` per the [new-repository checklist](https://github.com/GSA/data.gov/wiki/Checklist-for-new-repositories); decide where the shared DCAT-US library lives (needs harvester team input, since `datagov-harvester` already validates DCAT-US). | Organizational + design |
| 0002 | Confirm the editing model: **(A)** decomposed per-object screens vs. **(B)** unified tree-plus-detail workspace. Option (B) reverses the decision toward an SPA. **A reversal condition has already been triggered** — anonymous browser-memory editing is now scheduled 2.1, not long-term — so Options 1, 2, and 3 must be re-weighed together with the editing model. | Product |
| 0003 | Login.gov must confirm OIDC client registration with `acr_values` AAL3 + HSPD-12 per environment, and the returned `acr` claim must be verified in the sandbox. If unavailable, fall back to SAML. | External dependency |
| 0004 | Confirm whether an email-domain allowlist is wanted, and define how the *first* `admin` permission on a new catalog is granted (bootstrap path). | Product + design |
| 0005 | Decide what `inventory_publishers.csv` becomes now that there is no tenant entity — seed data for reusable DCAT `Organization` objects, whether the department→bureau hierarchy is represented, and global vs. per-catalog seeding. Decide before building the publisher picker. | Design |
| 0006 | Query existing S3 objects for actual file-size distribution to confirm 500 MB is the right cap rather than inheriting ClamAV's defaults. | Data |
| 0007 | Query production access logs and New Relic for `datastore_search`, `datastore_search_sql`, and `/datastore/*` consumers before announcing removal. Required CM-4 impact analysis. | Data |
| 0008 | Records officer determination on whether v1 edit history requires NARA retention; if so, archive the v1 database before decommissioning. | Compliance |
| 0009 | Verify each module's `variables.tf` for a Flask (non-Rails) app; decide Terraform vs. OpenTofu; provision and document the encrypted state backend; decide whether Terraform manages CI deployer service keys; confirm `logshipper` scope. | Design + organizational |

**Start ADR 0003 first.** It is the only blocker with an external dependency and
a lead time outside the team's control, it spans three environments, and ADR 0004
builds on its outcome. Every other blocker is answerable internally within days.

## Status lifecycle

```
proposed → accepted → deprecated
                    → superseded (by a newer ADR, which must be named in superseded_by)
```

**Merging these records does not accept them.** Standard MADR practice is to
merge while `proposed`, then flip `status` to `accepted` in a separate follow-up
pull request per record once its blockers clear and its decision makers have
signed off.

`decision_makers` is recorded as the **Data.gov engineering team** on every
record. When a record is accepted, narrowing that to the named individuals who
signed off makes the audit trail more useful — team membership changes over time,
and an assessor reading this in 2028 will want to know who actually decided.

## Provenance

These records and [`../architecture.md`](../architecture.md) were **drafted by an
AI coding agent** (opencode) from the
[Inventory Beta Re-design](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design)
feature list, the Data.gov wiki, and a read of the v1 codebase at
[`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c).
Factual claims — file paths, line numbers, line counts, configuration values, and
dependency versions — were verified against that commit. The reasoning,
recommendations, and rejected alternatives were **not** verified by anyone and
require human review.

Read them accordingly. Two cautions in particular:

- Several records make recommendations on **product questions** (the editing
  model in ADR 0002, the domain allowlist in ADR 0004, the file-size cap in
  ADR 0006) where an agent has no standing to judge. Those are flagged as
  blockers, not settled.
- The **sizing figures** in `architecture.md` §6 (Postgres plans, scanner memory)
  are proposals, not measurements.

No AI agent is listed in `decision_makers`; accountability for these decisions
rests with the humans who accept them.

## Conventions

- Filename: `NNNN-slugified-title.md`, zero-padded to four digits.
- Required frontmatter: `title`, `status`, `date`, `decision_makers`,
  `category`, `nist_controls`, `impact_level`, `ato_relevance`.
- NIST control IDs use the `XX-N` or `XX-N(N)` form.
- v1 code citations are pinned to a commit, not a branch.
- Update this index when adding a record.
