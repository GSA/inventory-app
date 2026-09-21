---
title: "Onboard agencies by re-importing published data.json rather than migrating from CKAN"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Deployment and Infrastructure"
nist_controls: ["CM-3", "SI-10", "SI-12", "CP-9", "CM-4", "SA-8"]
impact_level: "moderate"
ato_relevance: "yes-internal"
risk_treatment: "accept"
---

# Onboard agencies by re-importing published data.json rather than migrating from CKAN

## Context and Problem Statement

Inventory v1 holds agency metadata in CKAN's database as DCAT-US 1.1 datasets.
v2 uses a different data model (ADR 0005) and a different metadata version
(DCAT-US 3.0). We must decide whether to build a migration path from the v1
CKAN database into v2, or have agencies re-establish their catalogs in v2 by
importing their published `data.json`.

## Decision Drivers

- **Every agency's metadata is already published and publicly reachable.** The
  entire purpose of Inventory is to generate a `data.json` that the agency hosts
  at `agency.gov/data.json`. The migration source is therefore public, canonical,
  and available without any access to the v1 database.
- **A 1.1 → 3.0 converter already exists and is well tested.**
  `ckanext/datagov_inventory/dcat/` contains `transforms.py` (469 lines, 12
  dataset-level transforms), `validator.py` (620 lines), and
  `dcat_converter.py` (281 lines) — which is *already* a standalone CLI that
  fetches a remote v1.1 catalog, converts it, validates both sides, and reports
  counts. It is backed by ~1,600 lines of tests. The migration tool is largely
  written.
- **A database-level migration would have to bridge both a model change and a
  schema-version change simultaneously**, and would need to reproduce CKAN's
  `package_extras` conventions — the exact thing v2 exists to escape.
- **Import produces reuse automatically.** Under ADR 0005, `payload_hash`
  content-addressing means importing a flat catalog converges repeated contact
  points and publishers onto shared objects. Import is not a lossy shortcut; it
  is the mechanism that produces the desired structure.
- **v1 remains available during transition.** Nothing is deleted by this
  decision; v1 continues serving until agencies have re-established in v2.
- **1.1 → 3.0 is not a lossless mechanical mapping.** Some 3.0 constructs
  (`DatasetSeries`, `DataService`, `Concept` vocabularies, structured `Location`)
  have no 1.1 source and require human authoring regardless of migration
  approach.

## Considered Options

1. **Re-import from published `data.json`.** Agencies (or Data.gov staff on their
   behalf) import the agency's public DCAT-US 1.1 catalog; the existing converter
   produces a 3.0 catalog in `draft` state for review before going `live`.
2. **Database migration from CKAN.** Read the v1 CKAN database directly,
   convert packages and extras to v2 objects, and populate v2.
3. **Export/import via the v1 DCAT-US 3.0 export.** Use v1's existing
   `/organization/<id>/dcat-v3.json` endpoint as the source rather than the
   agency's published 1.1 file.
4. **Dual-run with synchronization** during a transition window.

## Decision Outcome

Chosen option: **Option 1 — re-import from published `data.json`**, because the
source data is already public and canonical, the conversion tooling already
exists and is tested, and the import path produces the shared-object structure
v2 wants rather than faithfully reproducing the CKAN structure v2 is abandoning.

Option 3 deserves note as a close variant and a useful fallback: v1's
`generate_dcat_v3` view (`plugin.py:345-407`) already emits a 3.0 catalog per
organization, which would skip the conversion step entirely. It is not chosen as
the primary path because it requires v1 to be running and reachable at migration
time, whereas the agency's published file does not — but it is the right tool for
any organization whose published `data.json` is stale or unreachable.

Option 4 is rejected: synchronizing two different data models across two metadata
versions is substantial engineering for a transition that needs no continuity
guarantee.

### Notable consequence: agencies can rehearse before v2 exists

Because the input is the agency's own public file and `dcat_converter.py` is
already a CLI with a `--dry-run` flag, an agency (or Data.gov staff) can convert
and validate a catalog today and see the exact error report v2 would produce.
This turns migration risk into a pre-launch activity rather than a launch-day
surprise, and it gives the conversion code real-world exercise before it is on
the critical path.

### What is not migrated

- **User accounts.** Not needed: ADR 0004 creates accounts just-in-time on first
  Login.gov authentication.
- **Version history.** v1's CKAN revision history is not carried into
  `object_version`. v2's audit trail begins at import. This is the main accepted
  loss — see below.
- **Draft datasets.** Anything not in the published `data.json` is not imported.
  Agencies with unpublished drafts in v1 must re-enter them or use the Option 3
  fallback (v1 has an "Export Drafts" capability at
  `templates/organization/read.html:9`, which makes this recoverable).
- **`config/data/inventory_publishers.csv`** (271 lines, ~350 organizations) is
  *reference* data, not migration data. It is **not** a tenant registry in v2 —
  agency/bureau silos are not a first-class concept
  ([`architecture.md` §4](../architecture.md#there-is-no-agencybureau-tenant-entity)) —
  so its only candidate purpose is seeding reusable DCAT `Organization` objects.
  That purpose is not yet designed; see the open question in
  [ADR 0005](0005-object-graph-data-model-for-dcat-us-3.md#open-question-what-becomes-of-the-publishers-reference-data).

### Positive Consequences

- No CKAN database reader, no dual-write, no reconciliation tooling to build,
  test, and then throw away.
- The onboarding path and the migration path are the **same** code path, so it is
  exercised continuously by new agencies rather than once at cutover.
- Import produces `draft` state, forcing human review before anything is
  published — a correctness gate a database migration would bypass.
- Agencies get a genuine opportunity to clean up metadata rather than porting
  accumulated problems forward.
- `dcat_converter.py`'s existing machine-readable `RESULTS:{...}` /
  `COUNTS:{...}` output makes migration progress measurable per organization.

### Negative Consequences

- **Version history does not survive.** v1's edit history is not carried into
  `object_version`. If historical attribution has a retention obligation, the v1
  database must be preserved separately as an archive — this ADR does not create
  that archive, and someone must decide whether one is required (see below).
- **Work is pushed onto agency staff**, across ~350 organizations. Each needs
  review of the converted draft and authoring of genuinely new 3.0 fields.
  This is coordination effort, not engineering effort, but it is not free.
- **Stale published files produce stale imports.** An agency whose
  `data.json` has not been regenerated recently will import outdated metadata.
  Mitigated by the Option 3 fallback.
- **Anything in v1 but not in the published export is silently absent.** The
  import cannot report what it never saw. Per-organization dataset counts should
  be compared between v1 and the imported result as a reconciliation check.
- **Conversion is imperfect by nature.** 1.1 has no `DatasetSeries`,
  `DataService`, structured `Location`, or `Concept` vocabularies, so imported
  catalogs will be valid 3.0 but will not exploit 3.0's new capabilities without
  human authoring.

### Compliance Consequences

- **SI-10 (Input Validation)** — imports validate against DCAT-US 1.1 on input
  and 3.0 on output, using the existing dual-validation path in
  `dcat_converter.py`. Import is an untrusted-input boundary: imported catalogs
  come from public URLs and must be treated as untrusted data, with URL fetching
  going through the egress proxy and subject to the live-catalog URL scanning the
  wiki already requires.
- **SI-12 (Information Management and Retention)** — **the open question.** v2's
  audit trail begins at import, so v1's history exists only in the v1 database.
  Whether that constitutes a record requiring retention under NARA schedules is
  a question for the records officer, not an engineering judgment. If retention
  is required, the v1 database must be archived before decommissioning, and that
  should be tracked as its own item.
- **CP-9 (System Backup)** — the v1 database must not be decommissioned until
  every agency has completed and verified re-import. A per-organization
  completion checklist gates v1 shutdown.
- **CM-3 (Configuration Change Control)** — each import should record the
  `_external/dcat-us` submodule commit used, so an import is reproducible against
  the schema version that validated it (consistent with ADR 0005).
- **CM-4 (Impact Analysis)** — the dataset-count reconciliation per organization
  is the impact analysis for this transition and should be recorded.
- **Risk treatment is `accept`**, not `mitigate`: the accepted risk is loss of
  v1 edit history in v2, accepted because the metadata itself is public and
  canonical elsewhere, and because v1's database can be archived independently
  if a retention obligation is identified.

## Links

- [Inventory Beta Re-design](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design) — import/export from a current DCAT-US 3.0 catalog
- [DCAT-US 3.0 migration guide](https://resources.data.gov/resources/dcat-us-3-migration/) and [M-25-05 crosswalk](https://resources.data.gov/resources/dcat-us-3-crosswalk/)
- [GSA/dcat-us 1.1→3.0 conversion script](https://github.com/GSA/dcat-us/blob/main/jsonschema/convert_dcat_1_1_to_3_0.py) — upstream reference implementation
- [ADR 0005](0005-object-graph-data-model-for-dcat-us-3.md) — `payload_hash` content-addressing that makes import produce reuse
- [ADR 0004](0004-jit-user-provisioning-and-catalog-rbac.md) — why user accounts need no migration
- `ckanext/datagov_inventory/dcat/dcat_converter.py` — existing CLI converter with `--dry-run`
- `ckanext/datagov_inventory/plugin.py:345-407` — v1 `generate_dcat_v3` export, the Option 3 fallback
- `config/data/inventory_publishers.csv` — reference data; role in v2 undecided (see ADR 0005)
- NIST SP 800-53 Rev 5.2 — CM-3, CM-4, SI-10, SI-12, CP-9, SA-8
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
