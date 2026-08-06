# Potential Roadmap: Provider-Neutral B2B Authorization

Status: **proposed; not committed**

This roadmap describes how Userverse could become a secure, self-hosted B2B
membership and authorization control plane without becoming an OAuth 2.0
Authorization Server or OpenID Connect Provider.

The intended product position is:

> Userverse keeps company membership and authorization consistent across
> authentication providers and gives applications simple, current, auditable
> access decisions.

Applications remain responsible for interactive authentication, or use an
existing identity provider. Userverse owns stable internal user identities,
company membership, roles, permissions, access decisions, and audit history.

## Why this direction

Organizations, roles, and login are already offered together by large identity
platforms. Rebuilding their protocol surface would give Userverse a large
security burden without creating a clear distinction. Userverse can instead be
valuable as the independent domain layer that survives a change of identity
provider.

This direction should provide:

- Stable Userverse user and company IDs that do not change during an IdP
  migration.
- Explicit membership lifecycle and immediate offboarding.
- Company-scoped roles and permissions that are evaluated from current data.
- Explainable allow/deny decisions and a useful audit trail.
- A small operational footprint and a straightforward developer experience.

This direction does **not** include:

- OAuth 2.0 authorization-server endpoints, consent, client registration, or
  third-party token issuance.
- OpenID Connect Provider discovery or ID tokens.
- SAML, SCIM, enterprise identity brokering, or a general policy language in
  the first release.
- Automatic account linking based only on matching email addresses.

## Target architecture

```text
Authentication provider
        |
        | signed identity token
        v
Application / Userverse trusted-token boundary
        |
        | validated (issuer, subject) identity
        v
Userverse identity link -> company membership -> roles -> permissions
                                                   |
                                                   v
                                  allow/deny decision + explanation
                                                   |
                                                   v
                                             audit event
```

The main security boundary is between authentication and authorization:

- Authentication establishes who the external subject is.
- An `identity_link` maps `(issuer, subject)` to a stable Userverse user.
- The requested company is treated as authorization context, not identity.
- Userverse evaluates current membership and permission records for every
  sensitive decision.
- Token claims may identify a subject but are not authoritative for current
  Userverse roles or membership state.

## Roadmap overview

Estimates are engineering-effort ranges, not delivery commitments. They assume
one engineer familiar with the existing FastAPI and SQLAlchemy codebase.

| Milestone | Outcome | Tickets | Estimate |
| --- | --- | --- | --- |
| 0. Boundaries and baseline | Agreed security and product invariants | UV-ACP-001 to 003 | 1-2 weeks |
| 1. Secure identity foundation | Truthful identities and revocable sessions | UV-SEC-001 to 004 | 3-5 weeks |
| 2. Authorization product | Current, explainable tenant-scoped decisions | UV-AUTHZ-001 to 006 | 5-8 weeks |
| 3. Bring-your-own identity | Strict inbound validation and safe identity linking | UV-IDP-001 to 004 | 3-5 weeks |
| 4. Adoption and operations | SDK, webhooks, access reviews, and examples | UV-DX-001 to 004 | 4-7 weeks |

Milestones should be delivered in order. Do not start external identity-provider
integration until the internal identity, membership, and tenant-isolation rules
are stable.

## Milestone 0: Boundaries and baseline

### UV-ACP-001: Record the product and protocol boundary

**Goal**

Create an architecture decision record stating that Userverse is an
authorization and membership system, not an OAuth/OIDC provider.

**Work**

- Define the authentication systems Userverse trusts and the data Userverse
  owns.
- Define stable identifiers for users, companies, memberships, and external
  identities.
- Document how applications authenticate to Userverse separately from how an
  end-user identity is established.
- Document which OAuth/OIDC responsibilities remain outside Userverse.

**Acceptance criteria**

- The trust boundary and non-goals are unambiguous.
- There is no proposed endpoint that exchanges an external identity token for
  a general-purpose third-party access token.
- Userverse user IDs remain stable when external identity providers change.

**Look out for**

- Accidentally designing token exchange or delegated authorization and calling
  it "identity validation." That would move Userverse back toward being an
  authorization server.
- Treating an email address as a permanent identity key.

### UV-ACP-002: Produce a tenant-aware threat model

**Goal**

Document threats and required controls before adding new authorization paths.

**Work**

- Model IDOR and cross-company access, confused-deputy behavior, privilege
  escalation, stale permissions, account linking, session theft, malicious
  issuer configuration, signing-key substitution, and audit-log leakage.
- Define security invariants and map each invariant to tests and monitoring.
- Identify actions that require reauthentication or administrator approval.

**Acceptance criteria**

- Every sensitive operation has an actor, company, required permission, and
  audit requirement.
- Cross-company failure cases are documented alongside successful cases.
- Each high-risk threat has a preventative or detective control.

**Look out for**

- Focusing only on token validation. Most likely failures will be tenant
  filtering, membership state, or administrative authorization mistakes.
- Superuser behavior bypassing audit or company-scope checks invisibly.

### UV-ACP-003: Establish security regression and migration gates

**Goal**

Create shared checks that all later tickets must satisfy.

**Work**

- Add a reusable cross-company test matrix for users, memberships, roles, and
  future permission checks.
- Add migration tests for SQLite and the production database engines supported
  by Userverse.
- Define compatibility checks for existing HTTP response shapes and first-party
  authentication.

**Acceptance criteria**

- A test fails when a user from company A can read or mutate company B data.
- Forward migrations work against a representative pre-change schema.
- Existing APIs remain compatible unless a breaking change is explicitly
  versioned and documented.

**Look out for**

- Tests that seed only one company; they cannot prove tenant isolation.
- Authorization tests that mock repositories and therefore miss an incorrect
  database filter.

## Milestone 1: Secure identity foundation

### UV-SEC-001: Make identity claims truthful and stable

**Goal**

Remove ambiguity from the internal user record before external identities are
linked.

**Work**

- Add a normalized unique username without replacing the UUID user ID.
- Add `email_verified_at`; do not infer verification from an `Active` status.
- Separate account status, email verification, and membership status.
- Define safe compatibility and backfill rules for existing users.

**Acceptance criteria**

- UUID remains the canonical Userverse subject.
- Existing accounts are not marked email-verified without evidence.
- Username collisions and soft-deleted records are handled deterministically.
- User creation remains backward-compatible or is explicitly versioned.

**Look out for**

- Case-sensitive uniqueness differences between SQLite, PostgreSQL, and MySQL.
- Storing security-critical state only in mutable JSON metadata.
- Reusing a username or email in a way that links a new person to an old
  identity.

### UV-SEC-002: Introduce per-device, revocable sessions

**Goal**

Replace global refresh-token versioning with explicit session and token-family
records.

**Work**

- Create a session per successful login with idle and absolute expiry.
- Issue random refresh tokens, store only hashes, and rotate on every refresh.
- Detect reuse of an already-rotated refresh token and revoke the entire token
  family.
- Support listing and revoking individual sessions or all sessions for a user.
- Revoke relevant sessions after password reset, account closure, or a high-risk
  security event.

**Acceptance criteria**

- Signing in on one device does not silently revoke another device.
- Refresh-token replay revokes the affected family and creates a security
  event.
- Raw refresh tokens never appear in the database, logs, traces, or audit data.
- Concurrent refresh requests have deterministic behavior.

**Look out for**

- Race conditions that allow the same refresh token to rotate twice.
- Comparing token hashes without constant-time comparison where applicable.
- Keeping access valid after the underlying user is suspended or closed.

### UV-SEC-003: Define access-token and signing-key policy

**Goal**

Make first-party bearer-token validation explicit and safely rotatable without
turning it into a public OAuth token service.

**Work**

- Decide between opaque access tokens and short-lived signed first-party JWTs.
- If JWTs remain, require issuer, audience, token type, issued-at, expiry, and a
  session identifier; use an asymmetric algorithm when multiple services must
  validate tokens.
- Define active and retiring key handling and emergency key revocation.
- Separate password-reset and email-verification signing contexts from access
  sessions.

**Acceptance criteria**

- A token intended for verification or password reset cannot authenticate an
  API request.
- Wrong issuer, audience, algorithm, token type, or key ID is rejected.
- A documented rotation exercise succeeds without accepting unknown keys.

**Look out for**

- Algorithm confusion or trusting an algorithm selected by the token.
- Using one symmetric secret for unrelated token purposes.
- Publishing a JWKS endpoint unless an actual external validation use case
  requires it.

### UV-SEC-004: Consolidate authentication abuse controls

**Goal**

Apply consistent controls to every unauthenticated credential and recovery
endpoint.

**Work**

- Apply per-account and per-network throttles to login, verification, password
  reset, and invitation acceptance.
- Standardize account-enumeration-resistant responses.
- Record security events for repeated failures, refresh reuse, session
  revocation, and identity-link changes.
- Define secret redaction for application logs, traces, errors, and audit events.

**Acceptance criteria**

- Unknown and known accounts have equivalent public recovery responses.
- Rate limits are covered by deterministic tests.
- Sensitive values are redacted before structured logging.

**Look out for**

- In-memory-only rate limits behaving differently with multiple workers.
- Logging request bodies on token, password, or linking endpoints.

## Milestone 2: Authorization product

### UV-AUTHZ-001: Formalize role and permission semantics

**Goal**

Define an authorization schema that preserves the global role catalog while
making company context explicit.

**Recommended model**

- `permission`: global immutable key such as `invoice.approve`, plus display
  metadata.
- `role`: reusable global role template.
- `role_permission`: permissions supplied by a role template.
- `company_role`: roles enabled for a company.
- A membership-to-role join table so a membership can hold multiple enabled
  company roles.

**Work**

- Decide whether companies can override a global role template. Defer overrides
  in v1 unless a concrete use case requires them.
- Define names, keys, deletion behavior, and versioning for roles and
  permissions.
- Migrate the current single `association_user_company.role_id` safely.

**Acceptance criteria**

- Every assigned role is enabled for the same company as the membership.
- Permission keys are stable machine identifiers and cannot be silently renamed.
- Deleting or closing a role cannot leave an active unauthorized assignment.
- Existing role APIs have documented compatibility behavior.

**Look out for**

- Assuming a globally shared role can be edited independently by each company.
- Role-name authorization checks; use stable IDs and permission keys.
- Soft-delete uniqueness preventing a safe recreation or causing an old record
  to regain authority.

### UV-AUTHZ-002: Add explicit membership lifecycle and multiple roles

**Goal**

Represent how and when a person belongs to a company rather than treating the
association as a boolean.

**Work**

- Add `invited`, `active`, `suspended`, `expired`, and `removed` states.
- Record activation, suspension, expiry, and removal timestamps and actors.
- Support multiple roles on an active membership.
- Define invitation acceptance and role-change rules.
- Prevent removal of the last effective company owner through a transactional
  invariant.

**Acceptance criteria**

- Only active, unexpired memberships contribute permissions.
- Suspending or removing a membership affects new decisions immediately.
- State transitions reject invalid paths and are audited.
- Last-owner protection is safe under concurrent requests.

**Look out for**

- Trusting a role requested in an invitation without rechecking the inviter's
  current authority when the invitation is accepted.
- Time comparisons using local time instead of UTC.
- Updating several authorization records without one transaction.

### UV-AUTHZ-003: Implement the authorization decision service

**Goal**

Provide one authoritative, deny-by-default path for application authorization.

**Initial interface**

```http
POST /authorization/check
```

```json
{
  "user_id": "52619b0b-9e97-4672-b525-611d2dfb",
  "company_id": "69d87dc8-8dd1-4639-b0c5-bd94a5fc47a5",
  "resource": "invoice",
  "action": "approve"
}
```

```json
{
  "allowed": true,
  "permission": "invoice.approve",
  "roles": ["finance_manager"],
  "policy_version": 12,
  "reason": "Granted by an active company role"
}
```

**Work**

- Resolve `resource.action` to a registered permission.
- Evaluate account state, company state, membership state and expiry, enabled
  company roles, and role permissions.
- Return stable machine-readable reason codes as well as a human explanation.
- Record a correlation ID and policy version.
- Define whether the caller may check only itself or another user.

**Acceptance criteria**

- Missing data and unexpected states deny access.
- Company A roles never authorize a company B request.
- The response explains which current role granted access without exposing
  unrelated membership data.
- Authorization logic is implemented in one domain service and reused by route
  guards.

**Look out for**

- Letting the request body choose an unrestricted `user_id` or `company_id`.
- Returning `allowed=true` when a dependency fails or times out.
- Treating a platform superuser as an undocumented unconditional bypass.

### UV-AUTHZ-004: Add batch checks and decision-aware SDK types

**Goal**

Avoid N+1 authorization calls without weakening the decision model.

**Work**

- Add a bounded batch-check endpoint.
- Preserve input order and return a decision for every item.
- Set request and item-count limits.
- Add typed Python models and error semantics suitable for an SDK.

**Acceptance criteria**

- Batch and individual checks produce identical decisions.
- A malformed item does not accidentally grant or obscure another decision.
- Limits prevent unbounded database work.

**Look out for**

- Partial failure behavior that applications interpret as allowed.
- Loading every role or permission in a company for each item.

### UV-AUTHZ-005: Enforce repository-level tenant boundaries

**Goal**

Make it difficult for new routes to omit company isolation accidentally.

**Work**

- Introduce tenant-aware repository query helpers.
- Require an explicit company context for company-owned data access.
- Add route/service authorization helpers that call the decision service.
- Add cross-tenant tests for reads, writes, pagination, filters, and soft-deleted
  records.

**Acceptance criteria**

- Company-owned repositories cannot perform an unscoped list or mutation by
  default.
- Negative tenant tests cover every company route.
- Pagination totals do not leak records from another tenant.

**Look out for**

- Fetching a record globally by ID and checking its company only after mutation.
- Search, count, export, and error messages leaking cross-company existence.

### UV-AUTHZ-006: Add authorization audit and access review

**Goal**

Make access changes and effective access explainable over time.

**Work**

- Create append-only events for membership, role, permission, and privileged
  administrative changes.
- Add queries for "why does this user have access?" and "who has this
  permission?"
- Add an access-review export showing active, suspended, expiring, and privileged
  memberships.
- Define audit retention and redaction policies.

**Acceptance criteria**

- Every privilege-changing transaction creates its audit event atomically.
- Audit events capture actor, subject, company, before/after identifiers,
  reason, timestamp, and request ID.
- Audit output contains no passwords, bearer tokens, invitation tokens, or
  external raw identity tokens.

**Look out for**

- Writing audit events after commit and losing them on a process failure.
- Storing excessive PII or mutable display values as the only identifiers.
- Claiming an audit table is tamper-proof without an actual integrity control.

## Milestone 3: Bring-your-own identity

### UV-IDP-001: Add a trusted issuer registry

**Goal**

Explicitly configure which external identity tokens Userverse will accept.

**Work**

- Store an exact issuer, allowed audiences, allowed algorithms, fixed discovery
  or JWKS location, activation state, and ownership metadata.
- Begin with platform-approved environment-level issuers. Defer company
  self-service issuer registration.
- Define cache, rotation, outage, and emergency-disable behavior.

**Acceptance criteria**

- Unregistered issuers and audiences are rejected.
- Issuer comparison is exact after one documented normalization step.
- Disabling an issuer prevents new authentication immediately.

**Look out for**

- Letting arbitrary company-provided URLs trigger server-side HTTP requests.
- SSRF through discovery, redirects, DNS rebinding, or private-network JWKS URLs.
- Using a key from one issuer to validate a token claiming another issuer.

### UV-IDP-002: Implement strict inbound JWT validation

**Goal**

Authenticate external subjects without issuing replacement OAuth tokens.

**Work**

- Validate signature, fixed algorithm allow-list, issuer, audience, expiry,
  not-before, issued-at, and required subject.
- Support controlled clock skew and bounded JWKS caching.
- Refresh keys safely on an unknown `kid` without fetching on every bad token.
- Return a provider-neutral external principal containing the trusted issuer and
  subject.

**Acceptance criteria**

- Tokens with `alg=none`, wrong algorithms, issuer, audience, or key are
  rejected.
- Key rotation succeeds while unknown-key abuse remains rate-limited.
- Raw tokens and full claim sets are not logged.

**Look out for**

- Accepting an audience merely because it appears in an unvalidated claim.
- Unbounded cache entries or network requests driven by attacker-controlled
  `kid` values.
- Treating a valid token as authorization for every Userverse company.

### UV-IDP-003: Add explicit external identity linking

**Goal**

Map a validated `(issuer, subject)` to one stable Userverse user safely.

**Work**

- Add an `identity_link` table with a unique `(issuer_id, subject)` constraint.
- Store provider display/email claims only as non-authoritative observations.
- Support linking through an already-authenticated account or administrator
  workflow.
- Support unlinking with safeguards against locking out the user.
- Audit every link and unlink operation.

**Acceptance criteria**

- Matching email alone never creates or changes a link.
- One external identity cannot be linked to multiple active Userverse users.
- Provider email changes do not change the Userverse user ID.
- Linking requires proof of control or explicit authorized administration.

**Look out for**

- Account takeover through auto-linking, recycled email addresses, or unverified
  email claims.
- Deleting and recreating links in a way that erases security history.
- Allowing the last usable authentication method to be removed accidentally.

### UV-IDP-004: Integrate external principals with authorization

**Goal**

Allow selected Userverse APIs to authenticate a linked external subject and
authorize it using current Userverse data.

**Work**

- Add a principal dependency that distinguishes first-party sessions, external
  identities, service credentials, and superusers.
- Map the external principal through `identity_link` before membership lookup.
- Keep authentication method and authorization result visible in request
  context and audit events.
- Roll out to read-only endpoints before privileged mutations.

**Acceptance criteria**

- An external token grants no access without an active identity link and
  company membership.
- Role claims from the external token do not override Userverse permissions.
- Existing first-party authentication remains distinguishable and compatible.

**Look out for**

- Choosing an authentication path based on an unverified token header or claim.
- Ambiguous fallback behavior where a failed external token is retried as a
  first-party token.

## Milestone 4: Adoption and operations

### UV-DX-001: Publish a FastAPI authorization package

**Goal**

Make the secure path easier than duplicating authorization logic in applications.

**Work**

- Provide typed clients for individual and batch decisions.
- Provide FastAPI dependencies such as `require_permission("invoice.approve")`.
- Define timeout behavior as deny-by-default for protected operations.
- Propagate correlation IDs without propagating credentials.

**Acceptance criteria**

- An example application can protect a route with a small, documented
  integration.
- Errors distinguish unauthenticated, unauthorized, unavailable, and invalid
  requests without granting on failure.

**Look out for**

- SDK-side caching extending access after a membership is revoked.
- Framework helpers trusting a tenant ID directly from user-controlled input.

### UV-DX-002: Add a transactional outbox and signed webhooks

**Goal**

Let applications react reliably to identity and authorization changes.

**Work**

- Write an outbox event in the same transaction as each domain change.
- Deliver signed, versioned webhook envelopes with retry and replay protection.
- Include stable identifiers and event versions, not secrets or unnecessary PII.
- Provide endpoint disablement and secret rotation.

**Acceptance criteria**

- Domain changes cannot commit without their required outbox event.
- Duplicate delivery is expected and documented; consumers can deduplicate by
  event ID.
- Signatures cover timestamp and raw body and reject stale replays.

**Look out for**

- Assuming exactly-once network delivery.
- Webhook URLs reaching private infrastructure without SSRF controls.
- Retrying permanent `4xx` failures forever.

### UV-DX-003: Create reference applications and integration guides

**Goal**

Prove the provider-neutral story with realistic applications.

**Work**

- Build one B2B FastAPI example with two companies and negative tenant tests.
- Demonstrate two upstream identity providers mapping to the same Userverse user.
- Document invitations, suspension, role changes, permission checks, identity
  linking, and offboarding.
- Publish migration guidance from application-owned role tables.

**Acceptance criteria**

- A developer can run the example locally from a clean checkout.
- The example visibly denies cross-company access and revoked membership.
- No example bypasses the public SDK by querying authorization tables directly.

### UV-DX-004: Add access-review and administration workflows

**Goal**

Give company administrators practical, safe self-service workflows.

**Work**

- Provide APIs for membership review, expiring access, privileged roles, and
  identity links.
- Add bulk operations with preview, per-item results, and audit reasons.
- Consider an embeddable UI only after the APIs and authorization rules are
  stable.

**Acceptance criteria**

- Company administrators can manage only their own company.
- Destructive bulk changes require confirmation and are recoverable where
  practical.
- Every administrative change is attributable and auditable.

**Look out for**

- Bulk requests bypassing the same invariant checks used by single-item APIs.
- Exports exposing users from another company or unnecessary identity-provider
  claims.

## Cross-cutting risks to watch

### Tenant isolation

- Never accept a company ID as sufficient proof of company access.
- Scope reads, counts, updates, deletes, exports, and error details.
- Test with at least two companies and overlapping role names in every suite.
- Prefer database queries that include the company predicate over fetch-then-check
  logic.

### Authorization freshness

- Do not treat role or permission claims in a long-lived token as current.
- Keep access-token lifetimes short and evaluate sensitive authorization from
  Userverse state.
- If decisions are cached, include membership/policy versions and invalidate on
  changes.

### Identity linking

- Use `(issuer, subject)` as the external key.
- Email is a display/contact attribute, not account-linking proof.
- Preserve historical link events even after unlinking.

### Role-model evolution

- The current global role catalog means a role definition may be shared by
  multiple companies. Confirm that every role mutation has the intended global
  effect.
- Do not add permissions until template-versus-company ownership is settled.
- Use permission keys in code; display names may change.

### Database portability and concurrency

- Exercise uniqueness, case normalization, transaction isolation, and locking
  on each supported production database.
- Protect last-owner, refresh rotation, invitation acceptance, and role-change
  invariants transactionally.
- Avoid JSON metadata for authoritative relationships that need constraints or
  indexed queries.

### Observability and privacy

- Record reason codes, timing, actor, company, and request ID.
- Never record passwords, reset codes, invitation tokens, bearer tokens, client
  secrets, or full external claim sets.
- Define audit retention, user-data deletion, and legal export behavior before
  promising compliance.

### Availability and fail-safe behavior

- Authorization-check failures must not become implicit allows.
- Define which low-risk reads may use a bounded stale cache and which operations
  must fail closed.
- Monitor latency, deny rates, issuer/JWKS failures, refresh reuse, and
  cross-tenant denial events.

## Decision gates

### Gate 1: Secure foundation

Proceed to the authorization product only when session replay tests, truthful
identity migration, and the cross-company regression matrix pass.

### Gate 2: Useful authorization

Proceed to external identity integration only when a reference application can
use the decision API for real permissions, explain decisions, revoke membership
immediately, and pass negative tenant tests.

### Gate 3: Provider neutrality

Claim provider neutrality only after two independent upstream issuers can map to
the same stable Userverse identity without email auto-linking or provider role
claims becoming authoritative.

### Gate 4: Broader standards work

Reconsider SCIM, SAML, or OAuth/OIDC provider functionality only when multiple
real customers require it and the security and operational ownership is funded.

## Success measures

- Zero known cross-company authorization paths.
- Membership suspension is reflected in new authorization decisions immediately.
- Every privilege change has an associated audit event.
- A new FastAPI application can protect its first company-scoped action in less
  than one hour using documented examples.
- Applications can change upstream IdP without changing Userverse user IDs or
  company memberships.
- Authorization check latency and availability meet a defined service-level
  objective before the decision API is placed on critical request paths.

## Common definition of done for tickets

A roadmap ticket is complete only when:

- Behavior and security invariants are documented.
- Unit, integration, negative tenant, and migration tests are included where
  applicable.
- Audit and observability behavior is defined.
- Existing API compatibility has been checked.
- No security-sensitive value is exposed in logs or response errors.
- Documentation and a rollback or disablement path are included.

## Reference landscape

These projects demonstrate that organization/RBAC functionality alone is not a
distinct market position:

- [Auth0 RBAC](https://auth0.com/docs/manage-users/access-control/rbac)
- [Clerk organization roles and permissions](https://clerk.com/docs/guides/organizations/control-access/roles-and-permissions)
- [WorkOS RBAC](https://workos.com/docs/rbac/integration)
- [Logto organization management](https://docs.logto.io/organizations/organization-management)
- [ZITADEL organizations](https://zitadel.com/docs/guides/manage/console/organizations-overview)

OpenFGA is a useful comparison for a broader relationship-based authorization
system. Userverse should remain more opinionated and simpler unless real use
cases justify a general model:

- [OpenFGA concepts](https://openfga.dev/docs/concepts)
