---
title: "Provision user accounts just-in-time on first Login.gov authentication, with authorization held in per-catalog permissions"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Authentication and Identity"
nist_controls: ["AC-2", "AC-2(3)", "AC-3", "AC-6", "AC-5", "AU-2", "AU-3", "IA-8", "PS-4"]
impact_level: "moderate"
ato_relevance: "yes-internal"
risk_treatment: "mitigate"
---

# Provision user accounts just-in-time on first Login.gov authentication, with authorization held in per-catalog permissions

## Context and Problem Statement

Inventory v1 requires accounts to be created **before** a user can authenticate:
`create_user_via_saml=false` and `create_user_via_web=false`
(`config/ckan.ini:190`, `:110`). A successful Login.gov authentication by an
unknown or soft-deleted user is rejected. v2 must decide whether to keep
pre-provisioning or create the account on first successful authentication.

This is worth an explicit record because the current design and the v2 design
intent disagree. The wiki states: *"Since users can create their own catalogs
and mark them as `draft` or `live`, there is no reason to lock accounts. With
PIV card authentication, there is no further level of identity management that
the data.gov team can make to make sure a user is who they say they are."*

## Decision Drivers

- **Pre-provisioning is the direct cause of a large body of custom code.**
  Because CKAN cannot create users via web or SAML, v1 needed custom actions and
  a custom admin UI to do it: `create_inventory_user` and `reactivate_user`
  (`ckanext/datagov_inventory/action.py`, 152 lines), four blueprint views
  (`create_user_form`, `reactivate_user_form`, `user_org_roles_table`, plus
  helpers), and `templates/user_org_roles_table.html` (115 lines). About 278
  of the 532 lines in `plugin.py` exist to work around pre-provisioning, backed
  by 214 lines of tests in `tests/logic/action/test_user_management.py`.
- **The manual process is operationally heavy.** Per the wiki, adding a user
  requires a ticket in `datagov-account-management`, then a
  `cf run-task inventory --command "ckan user add ..."`, then a UI step to add
  the user to an organization — and the same wiki warns that using the UI's own
  "Add a User" button "will only confuse SAML and cause issues."
- **Deleted-user reactivation is a recurring failure mode.** The wiki documents
  a whole recovery procedure for "username is taken" errors caused by
  soft-deleted users who cannot log in, requiring DB queries to recover a
  username from an email address. `reactivate_user` exists solely for this.
- **Identity assurance is already established upstream (IA-8).** Under
  ADR 0003, every authentication is AAL3 + HSPD-12 (PIV/CAC). Account existence
  gates nothing that Login.gov has not already proven; it only gates
  *authorization*, which should be modeled directly.
- **Least privilege must be preserved (AC-6).** Removing the account gate must
  not grant any access. This is the crux: the decision separates
  *authentication* from *authorization*.
- **Account management must remain auditable (AC-2, AU-2, AU-3).**
- **Offboarding must remain possible (PS-4).** Automatic account creation must
  not make deprovisioning harder.

## Considered Options

1. **Just-in-time provisioning with zero default authorization.** First
   successful Login.gov authentication creates a `user_account` row keyed on the
   Login.gov subject identifier. The new user holds **no** `catalog_permission`
   rows, so they can authenticate and see an empty workspace, and nothing else.
   Access is granted per catalog afterward.
2. **Keep pre-provisioning.** Port `create_inventory_user`, `reactivate_user`,
   and the roles-table admin UI to the new stack; retain the
   ticket-then-`cf run-task` workflow.
3. **JIT provisioning restricted by an email-domain allowlist** (e.g. `.gov`,
   `.mil`, plus exceptions). Accounts auto-create only for allowlisted domains;
   others are rejected at callback.
4. **JIT provisioning with automatic catalog assignment** derived from the
   user's email domain mapped to an organization.

## Decision Outcome

Chosen option: **Option 1 — just-in-time provisioning with zero default
authorization**, because identity is already proven to AAL3/HSPD-12 by
Login.gov before the application sees the request, and modeling authorization
explicitly in `catalog_permission` enforces least privilege more directly than
account existence ever did.

Option 4 is rejected outright: inferring authorization from an email domain is
implicit privilege grant, and it is exactly the kind of accidental access
AC-6 exists to prevent.

Option 3 is **deferred, not rejected** — see the open question below.

### Open question: is an email-domain allowlist wanted?

Option 1 permits anyone with a Login.gov account meeting AAL3+HSPD-12 to obtain
an Inventory `user_account` row with no permissions. The security consequence is
small — they see an empty workspace — but it is not zero:

- It creates an unbounded, externally-triggerable table of user rows (a minor
  resource-exhaustion and log-noise surface; mitigate with rate limiting at the
  proxy and an alert on anomalous creation rates).
- It means "has an account" no longer signals "is a known government data
  manager," which may surprise administrators reading the user list.

Because an HSPD-12 PIV credential already implies federal affiliation, a domain
allowlist is arguably redundant. Recommendation is to **start with Option 1 and
add the allowlist only if the empty-account rate proves to be a nuisance**,
treating the allowlist as a configuration change rather than a redesign. Confirm
this is acceptable before this record is accepted.

### Positive Consequences

- **~278 lines of `plugin.py`, all 152 lines of `action.py`, and the 115-line
  admin template are not ported.** The `datagov-account-management` ticket step
  and the `cf run-task ... ckan user add` procedure disappear from the runbook.
- **The deleted-user reactivation failure mode is eliminated by construction.**
  Offboarding removes `catalog_permission` rows (revoking access) rather than
  soft-deleting the account, so there is no state in which a valid PIV holder is
  authenticated but unusable. `reactivate_user` has nothing to do.
- Authorization becomes a single readable table rather than an emergent property
  of CKAN organization membership plus 15 chained auth functions, 2 rewritten
  auth functions, a regex path carve-out (`plugin.py:80-81`), and two
  `before_app_request` hooks.
- Supports the wiki's catalog-sharing model natively: `catalog_permission` has
  both `principal_user_id` and `principal_catalog_id`, so catalog-to-catalog
  sharing is the same mechanism rather than a special case.
- A user's first login is a recorded, timestamped audit event rather than an
  out-of-band administrative action performed by someone else.

### Negative Consequences

- The user table grows without administrative action and can be grown by any
  eligible Login.gov user (see open question). Requires rate limiting and a
  creation-rate alert.
- Administrators lose a coarse implicit signal ("account exists ⇒ vetted") and
  must read `catalog_permission` to reason about access. Acceptable — the
  permission table is the accurate answer and the old signal was misleading.
- **Someone must still grant the first permission on a new catalog**, and that
  bootstrap step is not resolved by this ADR. Initial catalog creation and the
  first `admin` grant need a defined path (likely a Data.gov sysadmin role),
  otherwise JIT provisioning produces users who can do nothing and no way to fix
  it. This is a required follow-on design item.
- The account-to-Login.gov binding must key on the **subject identifier**, not
  email. Email is mutable and reusable; keying on it risks conflating two
  people. v1 used email as the SAML attribute (`config/ckan.ini:181`), so this
  is a deliberate change.

### Compliance Consequences

- **AC-2 (Account Management)** — *changed, and must be re-documented.* Account
  creation becomes automatic-on-authentication rather than administratively
  approved. The compensating control is that account existence conveys no
  privilege. The SSP account-management section must state this explicitly; an
  assessor reading "accounts are created automatically" without the
  zero-privilege clause would reasonably flag it.
- **AC-2(3) (Disable Inactive Accounts)** — an inactivity policy should still
  apply to dormant accounts; JIT creation does not remove that obligation.
- **AC-3, AC-6 (Access Enforcement, Least Privilege)** — *strengthened.*
  Default privilege is exactly none, enforced by the absence of
  `catalog_permission` rows rather than by configuration flags.
- **AC-5 (Separation of Duties)** — permission grants are performed by a
  catalog `admin`, who cannot grant themselves access to catalogs they do not
  administer. Grant and revoke events must be audit-logged with actor, subject,
  catalog, and level.
- **AU-2, AU-3** — new audit events required: account created (with Login.gov
  subject, `acr`, timestamp), permission granted, permission revoked, permission
  level changed. These are ATO-relevant evidence.
- **PS-4 (Personnel Termination)** — offboarding is permission revocation. The
  wiki's "remove from orgs before deleting the user" ordering hazard goes away,
  since revocation is the primary mechanism and account deletion is optional.
- **Orphaned-catalog audit.** The wiki requires an audit for "all catalogs with
  no admin (no longer accessible/manageable)." Under this model that is a single
  query over `catalog_permission` — implemented as the `flask audit orphans`
  scheduled task.

## Links

- [Inventory Beta Re-design — User and Data Management](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design#user-and-data-management)
- [inventory.data.gov — Adding a User / Deleting a User / Updating a User](https://github.com/GSA/data.gov/wiki/inventory.data.gov) — the manual procedures this decision retires
- [ADR 0003](0003-login-gov-oidc-instead-of-saml.md) — the authentication decision this builds on
- [ADR 0005](0005-object-graph-data-model-for-dcat-us-3.md) — defines `catalog_permission` alongside the metadata model
- `config/ckan.ini:104-113,190` — current `create_user_via_*` settings
- `ckanext/datagov_inventory/action.py`, `ckanext/datagov_inventory/plugin.py:91-127,218-344,410-519` — code this decision removes
- NIST SP 800-53 Rev 5.2 — AC-2, AC-3, AC-5, AC-6, AU-2, AU-3, IA-8, PS-4
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
