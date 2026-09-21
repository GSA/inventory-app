---
title: "Use Login.gov OpenID Connect instead of SAML 2.0 for Inventory v2 authentication"
status: "proposed"
date: "2026-09-21"
decision_makers: ["Data.gov engineering team"]
category: "Authentication and Identity"
nist_controls: ["IA-2", "IA-2(1)", "IA-2(12)", "IA-5", "IA-8", "SC-8", "SC-12", "SC-13", "SC-17", "AC-12"]
impact_level: "moderate"
ato_relevance: "yes-internal"
risk_treatment: "mitigate"
---

# Use Login.gov OpenID Connect instead of SAML 2.0 for Inventory v2 authentication

## Context and Problem Statement

Inventory v1 authenticates government data managers through Login.gov using
SAML 2.0, implemented by a GSA fork of `ckanext-saml2auth` and enforcing
PIV/CAC-backed authentication at the IdP. Inventory v2 removes CKAN, so the
SAML integration cannot be carried over unchanged — it must either be
reimplemented natively or replaced with Login.gov's OIDC interface. The
authenticator assurance posture must not regress in either case.

## Decision Drivers

- **No regression in authenticator assurance (IA-2).** v1 sets
  `ckanext.saml2auth.requested_authn_context = http://idmanagement.gov/ns/assurance/aal/3?hspd12=true`
  (`config/ckan.ini:189`), i.e. AAL3 with HSPD-12, which in practice means
  PIV/CAC. This is a hard requirement and the primary constraint on this
  decision.
- **Eliminate the native XML-signature toolchain.** SAML requires `pysaml2`,
  which requires the `xmlsec1` system binary, which is the *sole* reason
  `manifest.yml:6-8` carries the `apt-buildpack` ahead of `python_buildpack`.
  Removing SAML collapses each app to a single buildpack.
- **Reduce credential-rotation toil (IA-5, SC-17).** The SP certificate is
  inlined into all three `vars.*.yml` files (~37 lines each) and the private key
  is base64-encoded in a user-provided service, decoded to a `mktemp` directory
  at boot (`.profile:47-50,130-131`). The current certificate expires
  **2027-04-19**, and Login.gov's annual March rotation has a dedicated wiki
  runbook. Certificate rotation is a coordinated swap with a hard deadline and
  an outage if missed.
- **Current SAML integration has zero automated test coverage.** It is omitted
  from the local plugin list (`.env.sample:36`), local development uses password
  login that production forbids
  (`ckanext.saml2auth.enable_ckan_internal_login=false`,
  `config/ckan.ini:188`), and this is acknowledged in-tree at
  `e2e/cypress/integration/ckan_extensions.cy.js:22-23`. "Keep SAML" is
  therefore not the low-risk option it appears to be — the production auth path
  is exercised by no test in any environment.
- **Transport and token cryptography must be FIPS-appropriate (SC-8, SC-13).**
- **Platform consistency.** Neither sibling application
  (`datagov-catalog`, `datagov-harvester`) carries a SAML stack.

## Considered Options

1. **Login.gov OIDC**, authorization code flow with PKCE (S256) and
   `private_key_jwt` client authentication, via
   [Authlib](https://authlib.org/). Assurance requested through
   `acr_values`.
2. **Login.gov SAML 2.0**, reimplemented natively on Flask with `pysaml2`,
   carrying forward the existing SP entity IDs, certificate, and rotation
   runbook.
3. **Login.gov OIDC with a SAML fallback** retained behind configuration during
   a transition window.

## Decision Outcome

Chosen option: **Option 1 — Login.gov OIDC with PKCE and `private_key_jwt`**,
because it preserves the AAL3/HSPD-12 posture through `acr_values` while
removing the `xmlsec1` native dependency, the extra buildpack, the inlined
per-environment certificates, and the annual certificate-rotation deadline.

Client configuration, per environment:

```
client_id:   urn:gov:gsa:openidconnect.profiles:sp:sso:gsa:datagov-{env}-inventory
auth method: private_key_jwt          # keypair in inventory-secrets UPS; JWKS-published
flow:        authorization_code + PKCE (S256)
acr_values:  http://idmanagement.gov/ns/assurance/aal/3?hspd12=true
scope:       openid email
```

Option 3 was rejected as scope creep: maintaining two authentication paths
doubles the security-review surface for a system that has no users to migrate
gradually (v2 is a new deployment, and ADR 0008 establishes that agencies
onboard by re-importing `data.json` rather than being migrated).

### Prerequisite, not an implementation detail

**This decision is blocked on Login.gov confirming the OIDC client registration
with `acr_values` AAL3 + HSPD-12 for each environment, and on verifying the
returned `acr` claim is asserted as expected.** The claim "OIDC gives equivalent
assurance to the current SAML `requested_authn_context`" is the entire
justification for this ADR and must be verified against the Login.gov sandbox
before the record moves to `accepted`. If Login.gov cannot provide equivalent
assurance via OIDC, fall back to Option 2 — the assurance requirement outranks
every convenience driver listed above.

### Positive Consequences

- AAL3 + HSPD-12 preserved; no change to the user's authentication experience.
- `pysaml2`, `xmlsec1`, `apt.yml`, and the `apt-buildpack` entry are all
  removed. One buildpack per app.
- Deleted: `config/login.production.idp.xml`, `config/login.sandbox.idp.xml`,
  `config/saml2/`, `config/who.ini` (repoze.who, vestigial since CKAN 2.9), and
  ~110 lines of inlined certificate across the three `vars.*.yml` files.
- **Key rotation becomes non-breaking.** Publishing both the new and old public
  keys in a JWKS, then retiring the old, replaces a coordinated certificate
  swap with a deadline. This is the most durable operational win.
- `acs` and `slo` disappear from the nginx path allowlist
  (`proxy/nginx.conf:48`), replaced by a single OIDC callback route.
- The auth path becomes testable: OIDC flows can be exercised against the
  Login.gov sandbox and mocked deterministically in CI, closing the coverage
  gap that exists today.

### Negative Consequences

- **Requires a Login.gov configuration change**, which is an external
  dependency with its own lead time and is a hard blocker (see above).
- Discards a working, in-production integration — a real if unexciting asset —
  and its accumulated operational knowledge.
- Introduces `authlib` as a new dependency on the authentication critical path.
  It must be pinned exactly and monitored (Snyk already scans dependencies
  weekly).
- The app now requires **outbound** network access to Login.gov for OIDC
  discovery and JWKS retrieval, where SAML used locally stored IdP metadata.
  This adds an egress-proxy allowlist entry (`secure.login.gov`) and a runtime
  dependency on that endpoint being reachable. Discovery and JWKS documents
  must be cached with a bounded TTL so a transient outage does not deny all
  logins.
- Private-key JWT signing requires correct clock discipline; skew causes
  confusing intermittent auth failures.

### Compliance Consequences

- **IA-2, IA-2(1), IA-2(12)** — *addressed, pending verification.* PIV/CAC
  multi-factor authentication preserved via `acr_values` AAL3+HSPD-12. Evidence
  for the ATO package is the `acr` claim observed in a sandbox authentication
  response, not the configuration value alone.
- **IA-8** — *addressed.* Identification of non-organizational users remains
  federated to Login.gov; Inventory asserts no independent identity proofing,
  consistent with the wiki's position that no further identity management is
  available to the Data.gov team beyond PIV.
- **IA-5** — *improved.* Client keypair held in a cloud.gov user-provided
  service; rotation via JWKS overlap rather than a synchronized swap. Rotation
  procedure must be documented in the runbook before `accepted`.
- **SC-8, SC-13** — TLS 1.2+ for all Login.gov communication; token signature
  verification uses Login.gov's published JWKS. Signing algorithm must be an
  approved asymmetric algorithm (RS256 or ES256); `none` and symmetric
  algorithms must be rejected explicitly, not merely unused.
- **SC-12, SC-17** — Key generation and lifecycle for the client keypair
  replace X.509 SP certificate management.
- **AC-12** — Session lifetime is unchanged by this decision and is governed
  separately; the 900-second idle timeout (`config/ckan.ini:33-35`) carries
  forward with server-side sessions in Postgres.
- **Required security review items.** The implementation must verify: `state`
  and `nonce` are generated per request and checked on callback; PKCE
  `code_verifier` is bound to the session; the `id_token` signature, `iss`,
  `aud`, `exp`, and `acr` claims are all validated (an unchecked `acr` silently
  voids the AAL3 control); and the redirect URI is exact-matched.
- **ATO documentation.** Authentication section of the SSP requires update.
  `ato_relevance: yes-internal` — the authentication method changes but the IdP
  and the authorization boundary do not.

## Links

- [Inventory Beta Re-design](https://github.com/GSA/data.gov/wiki/Inventory-Beta-Re%E2%80%90design)
- [Add Login.gov as Authentication](https://github.com/GSA/data.gov/wiki/Add-Login.gov-as-Authentication) and [SAML2 authentication](https://github.com/GSA/data.gov/wiki/SAML2-authentication) — current-state wiki pages
- [Login.gov SAML certificate rotation steps](https://github.com/GSA/data.gov/wiki/Login.gov-SAML-certificate-rotation-steps) — the runbook this decision retires
- [Login.gov developer documentation](https://developers.login.gov/oidc/) — OIDC integration and `acr_values`
- `config/ckan.ini:171-190` — current SAML SP configuration being replaced
- `.profile:30,47-50,130-131` — current SAML key/cert staging
- [ADR 0004](0004-jit-user-provisioning-and-catalog-rbac.md) — account provisioning, which this decision enables but does not itself decide
- NIST SP 800-63-3 — AAL definitions; NIST SP 800-53 Rev 5.2 — IA-2, IA-5, IA-8, SC-8, SC-12, SC-13, SC-17
- **v1 code citations** in this record refer to [`GSA/inventory-app@9fc0003a`](https://github.com/GSA/inventory-app/tree/9fc0003a7f2aeac92bab852c7ad7e5418925de5c) (2026-09-04), the v1 HEAD at the time of writing. Line numbers are pinned to that commit.
