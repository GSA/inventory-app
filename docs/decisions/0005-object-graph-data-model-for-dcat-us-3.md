---
title: "Store DCAT-US 3.0 metadata as a versioned object graph in Postgres"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Data Handling"
nist_controls: ["AU-2", "AU-3", "AU-10", "AC-3", "SI-10", "SI-12", "CM-3", "SC-28"]
impact_level: "moderate"
ato_relevance: "yes-internal"
risk_treatment: "mitigate"
---

# Store DCAT-US 3.0 metadata as a versioned object graph in Postgres

## Context and Problem Statement

The stated reason for leaving CKAN is that *"the CKAN metadata model is not very
compatible with the nested object classifications of DCAT-US 3.0."* DCAT-US 3.0
introduces `DatasetSeries`, `DataService`, `CatalogRecord`,
`Concept`/`ConceptScheme`, and `Location`; promotes `contactPoint` from a single
vCard to one or more `Kind` objects; and allows catalogs to embed other
catalogs. CKAN's flat package-plus-extras model cannot express this without
encoding structure into string keys. v2 must choose a storage model, and because
the data model *is* the reason for the rewrite, this decision carries more weight
than the framework choice.

The model must also support requirements that the storage layer determines:
per-object `draft`/`live` state excluded from export, class/object reuse across
datasets, version history with editor attribution, and catalog-to-catalog
sharing.

## Decision Drivers

- **Reuse is a first-class requirement, not an optimization.** The wiki: *"The
  classes and objects will be able to be created/defined for re-use by metadata
  providers... This will keep agencies consistent within their catalogs."* A
  shared `Kind` or `Organization` must have independent identity.
- **Versioning with editor attribution is required.** *"We will maintain
  historical object tracking along with user edit information. All changes will
  be available for auditability"* (AU-2, AU-3, AU-10).
- **Draft state is per object, not per catalog.** *"Classes/objects in `draft`
  state are not exported in the catalog."*
- **The v1 visibility model is a documented mess and must not be reproduced.**
  The current wiki describes three overlapping concepts — CKAN `private`,
  DCAT `accessLevel`, and Inventory publishing status — that interact
  confusingly, with resources publicly visible while datasets are not
  (GSA/data.gov#2095). v2 needs exactly one authoritative state field.
- **The authoritative validator operates on assembled JSON.** `validator.py`
  validates a complete nested catalog against `Catalog.json`. Storage must
  round-trip losslessly to that shape (SI-10).
- **Schema evolution must be cheap.** DCAT-US 3.0 point releases should be a
  `_external/dcat-us` submodule bump, not a migration.
- **Import must produce reuse automatically.** Agencies onboard by importing a
  flat `data.json` (ADR 0008); reuse should emerge from import rather than
  requiring manual deduplication.
- **Scale is modest.** Inventory holds thousands of datasets per organization,
  not `catalog.data.gov`'s 515,000 — so normalization costs are affordable and
  search does not require a dedicated engine.

## Considered Options

1. **Hybrid object graph.** A `metadata_object` table with `dcat_class`, `state`,
   and a `JSONB payload` holding only that object's *own scalar* properties.
   Nesting and reuse are edges in an `object_reference` table
   (`parent_object_id`, `child_object_id`, `property`, `ordinal`). Version
   history in an append-only `object_version` table.
2. **Document store.** One `JSONB` column per catalog holding the entire nested
   document; validate on write.
3. **Fully normalized relational schema.** A table per DCAT class with typed
   columns and foreign keys.
4. **Triplestore / RDF.** Model DCAT-US natively as RDF in a graph database.

## Decision Outcome

Chosen option: **Option 1 — hybrid object graph**, because it is the only option
in which independent object identity (required for reuse, per-object draft state,
and per-object version history) and cheap schema evolution are both true at once.

Option 2 cannot give an embedded `Kind` its own identity, `state`, or version
history without inventing addressing conventions inside the document — which is
CKAN's mistake in a new costume. Option 3 makes every schema point release a
migration, directly contradicting the submodule-bump requirement. Option 4 is
the most semantically faithful option and is genuinely defensible, but it
introduces an unfamiliar datastore, no cloud.gov brokered service, and a
SPARQL-shaped operational skill gap for a system whose interchange format is
JSON Schema, not RDF — the fidelity is not worth the platform cost here.

### Shape

```
user_account      ── created ──▶ catalog                  (creator; not a tenant boundary)
catalog           ── catalog_link ──▶ catalog            (embedded catalogs, live only)
catalog           ── catalog_member ──▶ metadata_object  (top-level dataset[]/service[]/datasetSeries[])
catalog           ── catalog_permission ──▶ user_account | catalog   (read | edit | admin)

metadata_object(id, catalog_id, dcat_class, state, payload JSONB,
                payload_hash, current_version_id, search_vector tsvector)
object_reference(parent_object_id, child_object_id, property, ordinal)
object_version(id, object_id, version_no, payload JSONB,
               editor_user_id, created_at, change_summary)
```

Three properties do the work, each mapping to a stated requirement:

- **`object_reference` is the reuse mechanism.** One `Kind` row referenced by
  fifty datasets. Export is a recursive walk that assembles nested JSON; import
  is the inverse.
- **`payload_hash` is content-addressed**, so importing a flat catalog that
  repeats the same contact point 50 times **automatically converges on one
  shared object**. "Start from a current DCAT-US 3.0 catalog" and "classes
  defined for re-use" are satisfied by one mechanism rather than two features.
- **`state` on `metadata_object`** makes "drafts are not exported" a
  `WHERE state = 'live'` predicate on the export walk — one authoritative field,
  replacing the v1 three-way confusion.

Search uses Postgres full-text search (`tsvector` + GIN) on
`metadata_object.search_vector`. **OpenSearch is explicitly not adopted**;
`catalog.data.gov` needs it at 515k datasets, Inventory does not.

### Positive Consequences

- Every DCAT-US 3.0 class is representable, including ones with no CKAN analogue
  (`DatasetSeries`, `DataService`, `CatalogRecord`, `ConceptScheme`).
- Adding or changing a class is a submodule bump plus form-model regeneration —
  no DDL migration, because class-specific fields live in `payload`.
- Version history is append-only with `editor_user_id`, satisfying AU-2/AU-3
  and AU-10 without `sqlalchemy-continuum`, temporal tables, or trigger magic.
- Catalog-to-catalog sharing is native: `catalog_permission` accepts either a
  user or a catalog as principal. Since that feature is MVP scope, the model
  carries it from the first release rather than requiring a later schema change.
- **No tenant entity.** v1's CKAN agency/bureau organization is not carried
  forward: agency silos are not a first-class concept in v2, so the isolation
  boundary is the catalog and nothing is inherited from an enclosing container.
  `user_account ── created ──▶ catalog` is provenance for audit, not ownership,
  and conveys no privilege. See
  [`architecture.md` §4](../architecture.md#there-is-no-agencybureau-tenant-entity).
- Draft autosave (ADR 0002) writes `object_version` rows with
  `change_summary='autosave'`, making in-progress work both recoverable and
  auditable.
- One Postgres service. With the DataStore retired (ADR 0007) and Redis dropped,
  v2 has a single stateful backing service where v1 had three.

### Negative Consequences

- **Export requires a recursive graph walk**, which is more code than
  `SELECT payload` and is the highest-risk correctness surface in the system.
  Mitigations: assembly lives in the pure-Python library with property-based
  round-trip tests (assemble∘decompose ≡ identity), and every export is
  validated against `Catalog.json` before delivery.
- **Cycles are possible** — embedded catalogs and `object_reference` edges can
  both form loops. The walk needs cycle detection with a depth bound, and
  `catalog_link` needs an acyclicity check on write. A cycle discovered only at
  export time is a denial-of-service against the export path. **This is MVP work,
  not deferrable:** catalog-to-catalog sharing is MVP scope (see
  [`architecture.md` §4](../architecture.md#catalog-to-catalog-sharing-is-mvp-scope)),
  so embedded catalogs — and therefore the cycle risk — exist from the first
  release.
- **`JSONB payload` is schemaless at the database layer**, so the database will
  not catch a malformed payload; validation is entirely an application
  responsibility (SI-10). This is deliberate — it is what buys cheap schema
  evolution — but it means validator coverage is load-bearing.
- **Shared objects create shared blast radius.** Editing a `Kind` used by 50
  datasets changes all 50. The UI must show reference counts before editing, and
  copy-on-write must be offered. Without this, reuse becomes a footgun.
- Reference counting is needed to identify genuinely orphaned objects, and
  "orphan" is ambiguous for a reusable object deliberately kept unattached.
- More joins than a document store. Acceptable at this scale; mitigated by
  indexes on `object_reference(parent_object_id)` and
  `metadata_object(catalog_id, dcat_class, state)`.

### Compliance Consequences

- **AU-2, AU-3 (Audit Events, Content)** — *addressed.* `object_version` is
  append-only with actor, timestamp, full payload, and change summary. Inserts
  only; no `UPDATE`/`DELETE` grant on that table for the application role.
- **AU-10 (Non-repudiation)** — editor attribution on every version, bound to a
  Login.gov subject via `user_account` (ADR 0003, ADR 0004).
- **AC-3 (Access Enforcement)** — every query is scoped by `catalog_id` and
  checked against `catalog_permission`. **Object identifiers must not be
  treated as authorization**; a direct-object-reference check is required on
  every object route, since reusable objects are addressable independently of
  the catalog a user reached them through. This is the model's main new access
  risk and must be an explicit test case.
  Because catalog-to-catalog sharing is MVP scope, authorization resolution must
  handle a **catalog** principal and **transitive** grants through embedded
  catalogs from the first release — not only the direct user-to-catalog case.
  Transitive resolution is the harder half and needs its own test coverage.
- **SI-10 (Input Validation)** — all imports and exports validated against
  DCAT-US JSON Schema (Draft 2020-12) by the single Python validator.
- **SI-12 (Information Management and Retention)** — append-only history implies
  unbounded growth; a retention policy for `object_version` is required and is
  not decided here. Note that a "delete my data" request cannot be satisfied by
  deleting a row, by design — the audit trail is the point. Metadata is public
  open data, so this is low-risk, but it should be stated rather than discovered.
- **CM-3 (Configuration Change Control)** — schema version (`_external/dcat-us`
  submodule commit) should be recorded on `export_run` so an export is
  reproducible against the schema that validated it.
- **SC-28 (Protection at Rest)** — encryption at rest provided by the cloud.gov
  RDS brokered service. No field-level encryption: DCAT metadata is public open
  data by definition and contains no PII beyond publicly published contact
  points.

### Open question: what becomes of the publishers reference data?

`config/data/inventory_publishers.csv` (~270 rows encoding a department → bureau
hierarchy) was v1's organization registry. With no tenant entity in v2 it is no
longer structural data, and its only remaining candidate purpose is **seed data
for reusable DCAT `Organization` objects** so that agency staff select a canonical
publisher instead of typing one.

That is a convenience feature and it is not designed. Open sub-questions: whether
the department → bureau hierarchy is represented at all (DCAT-US 3.0 has no
required parent/child relation between `Organization` objects); whether seeded
objects are global or copied per catalog; and whether the existing
`update_publishers.yml` workflow still has anything to update. **Decide before
building the publisher picker, not after.**

## Links

- [Inventory Beta Re-design](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design)
- [DCAT-US 3.0](https://github.com/GSA/data.gov/wiki/DCAT-US-3.0) and [DCAT-US 1.1 vs 3.0](https://github.com/GSA/data.gov/wiki/DCAT-US-1.1-vs-3.0) — structural differences driving this model
- [DCAT-US 3.0 Catalog class](https://resources.data.gov/standards/catalog/dcat-us-3/catalog/#catalog) — embedded-catalog semantics
- [GSA/data.gov#2095](https://github.com/GSA/data.gov/issues/2095) — the v1 visibility confusion this model replaces
- [ADR 0002](0002-ui-rendering-architecture-for-inventory-v2.md) — consumes the schema→form model and autosave
- [ADR 0004](0004-jit-user-provisioning-and-catalog-rbac.md) — `catalog_permission` semantics
- [ADR 0008](0008-onboard-via-data-json-reimport.md) — import path that produces the shared-object structure
- `ckanext/datagov_inventory/dcat/` — validator, transforms, and converter to be extracted
- NIST SP 800-53 Rev 5.2 — AU-2, AU-3, AU-10, AC-3, SI-10, SI-12, CM-3, SC-28
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
