---
title: "Retire the tabular DataStore API in Inventory v2"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Deployment and Infrastructure"
nist_controls: ["CM-7", "SA-8", "AC-3", "SI-10", "CM-4"]
impact_level: "moderate"
ato_relevance: "yes-boundary"
risk_treatment: "avoid"
---

# Retire the tabular DataStore API in Inventory v2

## Context and Problem Statement

Inventory v1 runs CKAN's DataStore alongside `ckanext-xloader`: uploaded CSV and
Excel files are ingested into a dedicated Postgres database and exposed as a
queryable HTTP API (`/api/action/datastore_search`). This requires a second RDS
instance, a read-only database user provisioned at boot, an ingest worker, and a
`/datastore` route through the proxy. v2 must decide whether to rebuild it.

The v2 feature list says *"Data file storage and public retrieval (inventory can
host datasets): MVP Yes"* — but the tabular query API is a distinct capability
from file hosting, and the wiki feature list does not mention it.

## Decision Drivers

- **The DataStore is not in the v2 feature list.** Rebuilding it is speculative
  work (AGENTS.md §15.2, YAGNI).
- **It is a disproportionate share of the infrastructure.** It accounts for
  `inventory-datastore` (a full RDS instance, `medium-psql-redundant` in prod),
  `ckanext-xloader`, `datastore-usersetup.py` (84 lines), `set_permissions.sql`
  (104 lines), `datastore/docker-entrypoint-initdb.d/datastore_ro.sql` (120
  lines), the `DS_RO_USER`/`DS_RO_PASSWORD` secrets, and the read/write URL
  split in `.profile:107-109`.
- **Retiring it is a precondition for other simplifications.** Together with
  dropping Redis, it reduces v2 to a single stateful backing service.
- **Rebuilding it is not cheap.** Type inference from CSV, a row-level query API
  with pagination and filtering, an ingest worker, and its own injection-risk
  surface (SI-10) — all of which CKAN provided for free and v2 would own.
- **It is a real, currently-live capability.** Not dead code: `datastore` and
  `xloader` are both in the active plugin list (`config/ckan.ini:143`), there is
  a dedicated e2e spec (`e2e/cypress/integration/datastore.cy.js`), and the
  wiki states *"some of GSA's hosted datasets are available by download or the
  datastore API."*

## Considered Options

1. **Retire it.** v2 hosts files for download; no row-level query API. Files
   above the hosting cap are referenced by agency-hosted URL.
2. **Rebuild it** on the v2 stack: CSV/XLSX ingest into Postgres tables plus a
   query API.
3. **Defer.** Ship v2 without it; add it later if demand is demonstrated.
4. **Delegate.** Point users at an existing Data.gov or third-party tabular
   service rather than hosting the capability in Inventory.

## Decision Outcome

Chosen option: **Option 1 — retire it**, because it is absent from the v2 feature
list, carries a large share of v2's infrastructure and code surface, and
Inventory's purpose is metadata authoring rather than data serving.

Option 3 is functionally the same near-term outcome; Option 1 is recorded
instead because it is the honest framing — the capability is being removed, and
saying "deferred" would understate the user impact and defer the conversation
with affected consumers. If demand is demonstrated later, this ADR should be
superseded rather than quietly reinterpreted.

### This is a user-visible regression and must be socialized

Uploaded files remain downloadable. **What goes away is the ability to query
their rows over HTTP.** Anyone currently calling
`/api/action/datastore_search` against `inventory.data.gov` will break.

**Required before this is announced as a simplification:** query production
access logs and New Relic for traffic to `/api/action/datastore_search`,
`/api/action/datastore_search_sql`, and `/datastore/*`, and identify any live
consumers. The wiki's mention of GSA-hosted datasets "available by download or
the datastore API" suggests at least one internal consumer may exist. Treating
this as a pure win without that check would be a self-inflicted outage for
someone else.

This verification is a prerequisite for moving this record to `accepted`, not a
follow-up task.

### Positive Consequences

- One fewer RDS instance per environment, including a
  `medium-psql-redundant` in production — the single largest infrastructure
  saving in the v2 design.
- Removed: `ckanext-xloader`, `datastore-usersetup.py`, `set_permissions.sql`,
  `datastore/docker-entrypoint-initdb.d/datastore_ro.sql`, the
  `DS_RO_USER`/`DS_RO_PASSWORD` secrets, the datastore read/write URL split, and
  the `/datastore` proxy route.
- Removes the local `postgres:9.6` container (EOL) from the development
  environment.
- Eliminates a SQL-injection-adjacent surface: `datastore_search_sql` accepts
  user SQL, which is an inherently sensitive capability v2 will not own (SI-10).
- Eliminates the xloader jobs-database quirk where the ingest worker's job state
  lives in the *main* database rather than the datastore
  (`.profile:124-125`) — a confusing arrangement nobody has to explain again.
- Narrows v2's scope to metadata authoring, which is the stated purpose.

### Negative Consequences

- **A capability is removed.** Unknown consumers may break (above).
- Agencies wanting a queryable API for a tabular file must host it themselves or
  use another service; Inventory can only describe it as a `Distribution` with
  an `accessURL`.
- If demand is demonstrated post-launch, rebuilding is more expensive than
  having carried it forward, because v2 will have no ingest infrastructure to
  extend.
- The `datastore.cy.js` e2e coverage is discarded rather than ported — a small
  loss of regression safety for file handling generally, since that spec
  incidentally exercised the upload path.

### Compliance Consequences

- **CM-7 (Least Functionality)** — *directly addressed.* Removes a network
  service and API surface not required by the documented mission.
- **SI-10 (Input Validation)** — *risk avoided.* The `datastore_search_sql`
  user-supplied-SQL surface is not rebuilt.
- **AC-3 (Access Enforcement)** — one fewer access path requiring authorization
  logic; removes the separate read-only database principal.
- **CM-4 (Impact Analysis)** — the consumer-traffic analysis above *is* the
  required impact analysis for removing a public API. It must be performed and
  its results recorded here before acceptance.
- **SC-7 / boundary** — `ato_relevance: yes-boundary` because a brokered data
  store and a public API endpoint leave the authorization boundary. The SSP
  component inventory and data-flow diagrams require update.
- **Attack surface** — net reduction: one fewer database, one fewer privileged
  DB role, one fewer public API.

## Links

- [Inventory Beta Re-design](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design) — feature list; DataStore API is absent
- [inventory.data.gov](https://github.com/GSA/data.gov/wiki/inventory.data.gov) — notes GSA datasets "available by download or the datastore API"
- [ADR 0006](0006-quarantine-then-scan-antivirus.md) — file hosting, which is retained
- [ADR 0005](0005-object-graph-data-model-for-dcat-us-3.md) — `Distribution` with `accessURL` as the alternative for externally-hosted tabular data
- `config/ckan.ini:59-94,143` — current DataStore and xloader configuration
- `create-cloudgov-services.sh:14,18` — the `inventory-datastore` service being removed
- `e2e/cypress/integration/datastore.cy.js` — coverage being discarded
- NIST SP 800-53 Rev 5.2 — CM-7, CM-4, SA-8, AC-3, SI-10
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
