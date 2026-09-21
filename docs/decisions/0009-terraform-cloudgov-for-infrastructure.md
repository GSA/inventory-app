---
title: "Provision cloud.gov infrastructure with GSA-TTS/terraform-cloudgov modules"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Deployment and Infrastructure"
nist_controls: ["CM-2", "CM-3", "CM-6", "CM-8", "CM-9", "SC-7", "SC-12", "SC-28", "AC-3", "AC-5", "SA-8", "SR-3"]
impact_level: "moderate"
ato_relevance: "yes-boundary"
risk_treatment: "mitigate"
---

# Provision cloud.gov infrastructure with GSA-TTS/terraform-cloudgov modules

## Context and Problem Statement

Inventory v1 provisions its cloud.gov services with `create-cloudgov-services.sh`
— 40 lines of `cf service … || cf create-service`, backgrounded with `wait`, then
asserting every service reports `succeeded`. It covers four brokered services and
nothing else.

v2 has infrastructure the script never covered: a ClamAV scanner application
([ADR 0006](0006-quarantine-then-scan-antivirus.md)), an egress proxy with an
allowlist for Login.gov and ClamAV signature updates, container-network policies
between three apps, and per-space CI deployer accounts. Today those exist as
manual `cf` commands, a stale README section, and tribal knowledge. We must decide
how v2 provisions and records its infrastructure.

## Decision Drivers

- **The infrastructure that is *not* in the v1 script is the infrastructure most
  likely to be misconfigured.** Network policies
  (`cf add-network-policy inventory-proxy → inventory` on 61443, and in v2
  `inventory → inventory-scanner`), egress allowlists, and deployer service keys
  are all undocumented manual steps. This is the same class of problem the v2
  rewrite exists to fix.
- **Three environments must stay in sync.** v1 approximates this with an
  `if space = prod` branch inside a shell script.
- **A configuration baseline must be inspectable and diffable (CM-2, CM-6).**
  A shell script says how to create a thing once; it does not describe the
  intended state, and it cannot detect drift.
- **Accidental destruction of a production database is the failure mode that
  matters.** Any tooling that can create a database can delete one.
- **Secrets must not leak into a state file (SC-12, SC-28).** This constrains
  *what* Terraform may manage, and is the main risk this decision introduces.
- **Platform consistency cuts both ways.** Neither sibling application
  (`datagov-catalog`, `datagov-harvester`) uses Terraform; both use
  `cf push` via a composite GitHub action. Diverging needs justification.
- **Reusing audited modules beats writing resources (SR-3).**
  [`GSA-TTS/terraform-cloudgov`](https://github.com/GSA-TTS/terraform-cloudgov)
  is maintained within GSA, versioned (currently `v2.5.0`), has Terraform tests,
  and is already used by `rails-template`-based apps and the FAC.

## Considered Options

1. **`GSA-TTS/terraform-cloudgov` modules** on the official
   `cloudfoundry/cloudfoundry` provider, pinned by tag.
2. **Hand-written Terraform** using provider resources directly, following the
   pattern in [`GSA/datagov-ssb`](https://github.com/GSA/datagov-ssb).
3. **A shell script**, as v1 does, extended to cover network policies, the
   egress proxy, and the scanner app.
4. **`cf` CLI in the existing composite GitHub action**, matching
   `datagov-catalog` — no separate infrastructure tooling.

## Decision Outcome

Chosen option: **Option 1 — `GSA-TTS/terraform-cloudgov` modules**, pinned at a
released tag, because the modules already encapsulate three of v2's genuinely
novel components (ClamAV scanner, egress proxy, egress space), they are maintained
and tested inside GSA, and they are built on the **official provider** rather than
the deprecated v2 API.

```hcl
module "database" {
  source          = "github.com/GSA-TTS/terraform-cloudgov//database?ref=v2.5.0"
  space           = data.cloudfoundry_space.app_space
  name            = "inventory-db"
  rds_plan_name   = var.rds_plan_name          # small-psql | medium-psql-redundant
  prevent_destroy = (var.environment == "prod")
  tags            = ["postgres", "inventory"]
}

module "s3"    { source = "github.com/GSA-TTS/terraform-cloudgov//s3?ref=v2.5.0" ... }

module "clamav" {
  source         = "github.com/GSA-TTS/terraform-cloudgov//clamav?ref=v2.5.0"
  name           = "inventory-scanner"
  max_file_size  = var.max_file_size           # see ADR 0006
  clamav_memory  = "3072M"                     # module default; see below
  proxy_server   = module.egress_proxy.domain
  proxy_port     = module.egress_proxy.port
  ...
}

module "egress_proxy" {
  source    = "github.com/GSA-TTS/terraform-cloudgov//egress_proxy?ref=v2.5.0"
  allowlist = ["secure.login.gov:443", "database.clamav.net:443"]
  allowports = [443, 61443]                    # see New Relic note below
  ...
}
```

### Why not the `datagov-ssb` pattern

`datagov-ssb` is the team's existing Terraform, so it is the obvious template —
and it is the wrong one. Its `versions.tf` pins
`cloudfoundry-community/cloudfoundry ~> 0.54.0`, which targets the **Cloud
Foundry v2 API, deprecated 2025-06-06**. `terraform-cloudgov` modules `>= 2.0.0`
use `cloudfoundry/cloudfoundry >= 1.4.0`, the official provider, and document v2
deprecation compatibility explicitly.

Adopting `datagov-ssb`'s approach would mean starting v2 on the far side of a
deprecation. This should also prompt a separate look at `datagov-ssb` itself,
which is out of scope here but worth tracking.

### Scope boundary: Terraform owns topology, not secret values

**This is the constraint that makes the decision safe, and it is not negotiable.**
`cloudfoundry_service_key` attributes and user-provided-service credentials are
stored in Terraform state in plaintext. Managing `inventory-secrets` values in
Terraform would place the Login.gov OIDC private key and the Flask secret key
into an S3 object, converting a well-contained secrets story into a new
high-value target.

| Terraform manages | Stays outside Terraform |
|---|---|
| `aws-rds` instance and plan, per environment | `inventory-secrets` **credential values** (`cf cups` / `cf uups`) |
| `s3` instance | Key rotation procedures |
| ClamAV scanner app (`clamav` module) | |
| Egress proxy and its allowlist (`egress_proxy`) | |
| Egress space (`cg_space`) | |
| Container-network policies between apps | |
| Space roles and CI deployer service accounts | |
| Existence of the `inventory-secrets` UPS, not its contents | |

**Application deployment stays `cf push --strategy rolling`** via a composite
GitHub action, matching `datagov-catalog`. The modules include `application`,
`drupal`, and `spiffworkflow` deployment modules; v2 does **not** use them.
Terraform is for infrastructure lifecycle; app deploys are frequent, rolling, and
already well served.

### Three facts the modules supply that this design had wrong or missing

Reading the module source corrected the architecture document, which is itself an
argument for adopting them:

1. **The scanner needs ~3 GB, not ~2 GB.** `clamav/variables.tf` defaults
   `clamav_memory = "3072M"` with `disk_quota = 2048M` and
   `health_check_invocation_timeout = 600`. ADR 0006 and `architecture.md` §2 said
   ~2 GB — a guess, now corrected against a module used in production.
2. **New Relic needs `allowports = [443, 61443]` through the egress proxy.**
   Documented in the module README as discovered on the FAC, which uses the same
   Python agent and the same FedRAMP `gov-collector.newrelic.com` endpoint v2 will
   use. Without this, telemetry silently fails.
3. **The ClamAV app gets an `apps.internal` route**, no public route — consistent
   with ADR 0006's requirement that the scanner is not publicly reachable, and now
   enforced by the module rather than by our own care.

### Positive Consequences

- Network policies, egress allowlists, the scanner app, and deployer accounts
  become version-controlled, reviewable configuration instead of undocumented
  manual steps. This is the primary benefit.
- `prevent_destroy = (var.environment == "prod")` gives a hard guard against
  accidental production database destruction, using the module's documented
  pattern.
- Environment differences become a `tfvars` file per environment rather than an
  `if` branch in a shell script.
- `terraform plan` on pull requests surfaces intended infrastructure changes for
  review before they happen (CM-3), and detects drift (CM-6).
- The component inventory required for the ATO (CM-8) can be derived from
  configuration rather than assembled by hand.
- Module upgrades arrive as reviewed version bumps with an `UPGRADING.md`, rather
  than as ad-hoc `cf` command changes.

### Negative Consequences

- **A second toolchain in the app repository** — Terraform/OpenTofu, a state
  backend, provider lockfile, and CI wiring — for a team whose other two
  application repos have none.
- **Bootstrap paradox.** The S3 bucket holding Terraform state cannot itself be
  managed by that state. It must be created out-of-band and documented.
- **Divergence from `datagov-catalog` and `datagov-harvester`**, weakening the
  platform-consistency driver used in ADRs 0001 and 0002. Justified by v2 having
  materially more infrastructure (scanner, egress proxy, three-app network
  policies), but it is a real cost and should be revisited if that turns out not
  to be true.
- **State becomes sensitive even under the boundary above.** Service instance
  GUIDs and binding metadata are not secrets, but the state file still warrants
  encryption at rest, access restriction, and versioning.
- **Drift detection is worthless if nobody reads the plan.** A `terraform plan`
  posted on a PR and ignored buys nothing. This requires a review habit, not just
  a workflow file.
- **Module dependency is a supply-chain dependency (SR-3).** Pinning by tag
  (`?ref=v2.5.0`) rather than branch is mandatory, and upgrades need review.
- **`prevent_destroy` on an existing database requires a manual state migration**
  per the module's `UPGRADING.md`. Cheaper to enable at creation — another reason
  to adopt this before the first production deploy, not after.

### Compliance Consequences

- **CM-2 (Baseline Configuration)** — *strengthened.* Infrastructure becomes a
  declarative, version-controlled baseline rather than an imperative script.
- **CM-3 (Configuration Change Control)** — infrastructure changes flow through
  pull request with a visible plan, under the same protected-branch review as
  code (ADR 0001).
- **CM-6 (Configuration Settings)** — drift between intended and actual state
  becomes detectable.
- **CM-8 (Component Inventory)** — derivable from configuration; useful ATO
  evidence.
- **CM-9 (Configuration Management Plan)** — the Terraform layout, state backend,
  and apply workflow must be documented before first production use.
- **SC-7 (Boundary Protection)** — **the reason this record is
  `yes-boundary`.** Egress allowlist and container-network policies are boundary
  controls, and moving them into Terraform makes them auditable artifacts. The
  allowlist (`secure.login.gov:443`, `database.clamav.net:443`) becomes reviewable
  configuration rather than a remembered command.
- **SC-12, SC-28 (Key Management, Protection at Rest)** — addressed by the scope
  boundary: no secret values in state. The state bucket must be encrypted,
  versioned, and access-restricted regardless.
- **AC-3, AC-5 (Access Enforcement, Separation of Duties)** — space roles and
  deployer service accounts become explicit. The CI service account's permissions
  should be scoped to what the plan requires, and the credentials used for
  `apply` must not be reusable for ad-hoc production changes.
- **SR-3 (Supply Chain)** — modules pinned by tag; `.terraform.lock.hcl`
  committed; module and provider upgrades reviewed.

### Blockers before acceptance

1. **Verify the module set against `variables.tf` for each module used.** The
   README describes the modules as serving `rails-template`-based apps. Nothing in
   `database`, `s3`, `clamav`, `egress_proxy`, or `cg_space` appeared
   Rails-coupled on inspection, but each should be confirmed for a Flask app
   before commitment.
2. **Decide Terraform vs. OpenTofu.** `datagov-ssb` uses OpenTofu
   (`install-opentofu.sh`, `tofu init`). Licensing and agency direction should
   determine this, not this record.
3. **Provision and document the state backend** — a dedicated, encrypted,
   versioned S3 bucket with restricted access, created out-of-band.
4. **Decide whether Terraform manages CI deployer service keys.** It can
   (`cloudfoundry_service_key`), but those keys are credentials and land in state.
   Recommendation: manage the *service account*, create the *key* manually — but
   this needs confirmation.
5. **Confirm `logshipper` scope.** The module builds a log-drain app with New
   Relic credentials. `datagov-catalog`'s wiki describes "Logstack (cloud.gov log
   drain)." Whether v2 adopts the module or the catalog's existing arrangement is
   undecided and out of scope here.

## Links

- [GSA-TTS/terraform-cloudgov](https://github.com/GSA-TTS/terraform-cloudgov) — module source, `v2.5.0`
- [terraform-cloudgov UPGRADING.md](https://github.com/GSA-TTS/terraform-cloudgov/blob/main/UPGRADING.md) — `prevent_destroy` migration, clamav and egress-proxy network policy examples
- [cloud.gov v2 API deprecation](https://cloud.gov/2025/01/07/v2api-deprecation/) — why the `datagov-ssb` provider pin is not the model to follow
- [GSA/datagov-ssb](https://github.com/GSA/datagov-ssb) — the team's existing Terraform, on the deprecated community provider
- [ADR 0001](0001-repository-topology-for-inventory-v2.md) — the repository this Terraform lives in
- [ADR 0006](0006-quarantine-then-scan-antivirus.md) — the scanner this provisions; amended by this record's 3 GB and `max_file_size` findings
- [`docs/architecture.md`](../architecture.md) §6 — deployment
- NIST SP 800-53 Rev 5.2 — CM-2, CM-3, CM-6, CM-8, CM-9, SC-7, SC-12, SC-28, AC-3, AC-5, SA-8, SR-3
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
