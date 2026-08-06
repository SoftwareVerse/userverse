# Userverse POPIA Compliance Audit

**Audit date:** 6 August 2026

**Reviewed revision:** `69dae481b3036997fd9b26254b1d9ac111a8289e` (`v0.6.38`)

**Scope:** Userverse backend, including API, authentication, authorization, persistence, migrations, email, logging, telemetry, configuration, CI, tests, and documentation

**Overall score:** **18/100**

**Overall risk:** **Critical**

## 1. Executive summary

Userverse is not presently able to demonstrate POPIA compliance. It has useful security foundations—bcrypt password hashing, short-lived JWTs, database-backed token-family invalidation, authenticated tenant checks on the primary company routes, generic error handling, soft-delete filtering on many reads, parameterized ORM queries, and a 366-test passing baseline—but those controls are incomplete and are not supported by the governance, notice, retention, rights, incident-response, or operator controls required by POPIA.

The Critical rating is driven by a concrete secret-disclosure pattern. Password reset OTPs and verification tokens are accepted in query strings, request middleware collects raw query strings, normal HTTP access infrastructure may record the request target, and the SMTP failure path prints complete transactional emails—including OTPs or reset links—to process stdout. Anyone with access to application/container logs may therefore obtain live account credentials. This rating is intentionally independent of the numerical score: one systemic credential exposure is sufficient for Critical risk.

The most material additional gaps are:

1. deletion is only an indefinite soft delete; no purge, anonymization, retention schedule, legal hold, or backup-erasure process exists;
2. there is no access/export, objection, restriction, correction-request, consent-withdrawal, or trackable data-subject request workflow;
3. a company administrator can immediately add an existing user without acceptance, and the repository can add and return a soft-deleted user with the user's email, phone, status, and `is_superuser` flag;
4. every active company member, including a Viewer, can retrieve those same full profile fields for every other active member;
5. the system has one-character passwords, a non-cryptographic OTP generator, no login throttling or MFA, process-local reset throttles, and compatibility code capable of accepting a legacy plaintext password;
6. there is no privacy notice, processing register, documented lawful-basis decision, Information Officer evidence, breach workflow, operator register, or international-transfer assessment; and
7. mutable JSON metadata duplicates complete actor profiles across records without a retention boundary or a trustworthy audit trail.

This is a technical assessment, not legal advice. Legal bases, statutory retention exceptions, PAIA obligations, processor contracts, deployment controls, and Information Officer registration require confirmation by Userverse's Information Officer and South African counsel.

## 2. Authority, method, and scoring

### 2.1 Authority

The audit uses the official [Protection of Personal Information Act 4 of 2013](https://www.justice.gov.za/legislation/acts/2013-004.pdf) as the primary source. The eight conditions are sections 8–25. Related review criteria include special personal information and children (sections 26–35), Information Officers (sections 55–56), prior authorisation (sections 57–59), direct marketing (section 69), automated decisions (section 71), and transborder flows (section 72).

Current implementation guidance was checked against the Information Regulator's [POPIA forms](https://inforegulator.org.za/popia-forms/), [Information Officer guidance](https://inforegulator.org.za/information-officers/), [security-compromise fact sheet](https://inforegulator.org.za/2025/08/19/fact-sheet-handling-of-security-compromises/), [guidance notes](https://inforegulator.org.za/guidance-notes/), and [prior-authorisation portal](https://inforegulator.org.za/prior-authorisation/).

### 2.2 Evidence method

- Enumerated all OpenAPI operations and traced request models/parameters through routers, services, repositories, ORM tables, email, logs, and response models.
- Reviewed all five ORM tables, their shared metadata columns, all seven Alembic revision files, and the local SQLite schema without extracting any personal values.
- Reviewed authentication, token, reset, verification, RBAC, tenant filtering, soft-delete, logging, email, telemetry, metrics, configuration, Docker, CI, tests, and documentation.
- Ran the full test suite: **366 passed, one warning, 113.87 seconds**.
- Ran Bandit over 6,514 application lines: 17 results (0 high, 1 medium, 16 low). The relevant result is B311 at `app/services/user/password.py:38`; the other password/token-string detections are false positives. Binding to all interfaces is a deployment hardening item.
- Ran `pip-audit 2.10.1` against a frozen production dependency export: Click 8.3.1 has `PYSEC-2026-2132`/`CVE-2026-7246`, fixed in 8.3.3. The vulnerable `click.edit()` function is not used in this repository, reducing immediate exploitability.
- Ran `detect-secrets 1.5.0`. Findings were test fixtures, documented placeholders, migration revision identifiers, and the known development JWT default; no verified production credential was found. Historical secret scanning and deployed secret stores were not available.
- Used an isolated in-memory database probe to confirm that `CompanyUserRepository.add_user_to_company` links a user whose `_closed_at` is already set and returns `email`, `first_name`, `last_name`, `phone_number`, `status`, `id`, `role`, and `is_superuser`.

### 2.3 Evidence statuses

| Status | Meaning | Score factor |
|---|---|---:|
| Compliant | Code and available evidence meet the tested control | 1.00 |
| Partial | A useful control exists but does not cover the obligation | 0.50 |
| Needs Verification | Compliance depends on unavailable operational/legal evidence | 0.25 |
| Non-compliant | Required control is absent or contradicted by evidence | 0.00 |

Each condition is worth 12.5 points. Control factors are averaged within the condition.

| Condition | Control factors | Calculation | Points |
|---|---|---:|---:|
| Accountability | NV, NC, Partial, Partial | `(0.25 + 0 + 0.5 + 0.5) / 4 × 12.5` | 3.91 |
| Processing limitation | NV, NC, Partial, NC | `(0.25 + 0 + 0.5 + 0) / 4 × 12.5` | 2.34 |
| Purpose specification | NC, NC, NC, NC | `0 / 4 × 12.5` | 0.00 |
| Further processing limitation | NC, NC, NV | `(0 + 0 + 0.25) / 3 × 12.5` | 1.04 |
| Information quality | Partial, Partial, Partial, NC | `(0.5 + 0.5 + 0.5 + 0) / 4 × 12.5` | 4.69 |
| Openness | NC, NC, NC, NC | `0 / 4 × 12.5` | 0.00 |
| Security safeguards | Partial, Partial, NC, NV, NC | `(0.5 + 0.5 + 0 + 0.25 + 0) / 5 × 12.5` | 3.13 |
| Data subject participation | NC, Partial, Partial, NC, NC | `(0 + 0.5 + 0.5 + 0 + 0) / 5 × 12.5` | 2.50 |
| **Total** |  |  | **17.60 (17.61 if the displayed row subtotals are summed) → 18/100** |

### 2.4 Validation outcomes

| Required probe | Result |
|---|---|
| Cross-company reads and mutations by role | Existing isolated HTTP/database tests and service/repository inspection confirm membership and Owner/Administrator guards on the principal tenant routes. The audit did not find a direct cross-tenant object bypass, but it did find immediate invitation processing, Viewer overexposure, globally shared role impact, and no exhaustive operation-by-role negative matrix. Treat the untested matrix as Partial, not proof of isolation. |
| Inactive, unverified, removed and soft-deleted users | HTTP/JWT tests reject inactive users and cover verification-disabled behavior; removed memberships are excluded by normal link checks. The targeted database probe demonstrated that the invitation repository can re-link and return a soft-deleted user (F-04). |
| Successful and error response exposure | OpenAPI schemas, response models and exception handlers were inspected. Full member responses expose email, phone, status and global privilege (F-05); debug exception details remain configuration-dependent (F-13). |
| Reset/verification expiry, replay, revocation and enumeration | Tests cover expired/wrong-type JWTs, reset-token expiry, revoked refresh families and generic reset/resend responses. Reset credentials remain plaintext in metadata, OTPs use non-cryptographic randomness, refresh tokens are replayable within their family lifetime, login responses can distinguish an unknown user from a wrong password, and query/email logging exposes secrets (F-01/F-06/F-11). |
| Access, export and deletion consequences | OpenAPI has no privacy/export/request route. Repository and migration inspection shows soft deletion without purge, anonymization, restriction, holds, backup propagation or deletion evidence (F-02/F-03). |
| Email, query, IP, user-agent and exception logging | Static inspection confirms query/IP/user-agent collection. The current JSON formatter drops the middleware's flat extra fields, but other handlers, default access logging, proxies and APM remain deployment-dependent. Complete email bodies and recipients are definitely printed on configured fallback/failure paths (F-01/F-13). |

### 2.5 Limitations

The tracked branch is the technical source of truth. No deployed environment, production traffic, production database, private infrastructure repository, operator contract, Information Officer record, PAIA manual, log platform, backup system, key store or cloud control plane was available. No personal values were extracted: local-database work was limited to schema metadata and aggregate counts. Tests and targeted probes used isolated/local state and are not a production penetration test. Dynamic proxy/access-log behavior, historical credential exposure, backup erasure, TLS, residency and operator performance therefore remain **Needs Verification**. Container/image scanning, historical Git secret scanning, external DAST and an SBOM/provenance verification were unavailable; these are recorded as remediation/evidence requests rather than silently treated as passed.

## 3. Personal information inventory

POPIA protects information about natural and identifiable juristic persons. Company contact and organizational records are therefore included rather than assumed non-personal.

| Field or category | Purpose / actual use | Table or location | Collection and API endpoints | Who can access it | Current retention | Necessary? | Likely justification / gap |
|---|---|---|---|---|---|---|---|
| User UUID | Identity, relationships, authorization | `user.id`; association FKs; JWT | Created at `POST /user/create`; returned by profile/member APIs | Subject; all members of shared companies; DB/log operators; JWT holder | Indefinite, including after soft deletion and in snapshots | Yes, but exposure can be narrower | Contract/legitimate interest; internal ID need not be in every response |
| First and last name | Profile display and email greeting | `user.first_name`, `last_name`; actor snapshots; JWT | Create/update; profile; company users; email | Subject; all company members; SMTP/operator; DB/log operators | Indefinite and duplicated | Optional | Consent is not necessarily required; purpose and optionality need notice |
| User email | Login, verification, reset, invitations, tenant membership lookup | `user.email`, unique index; actor snapshots; JWT; logs/email | Basic Auth, reset/resend bodies, invite body; profile/member outputs | Subject; all company members; inviting managers; SMTP/log/DB operators | Indefinite; logged without policy | Core login email is necessary; directory exposure is not | Contract/legitimate interest for authentication; section 18 notice missing |
| Phone number | Optional profile/contact data | `user.phone_number`; actor snapshots; JWT | Create/update; profile and company-user outputs | Subject; every company member; DB and token holder | Indefinite | Optional; excessive in default member response | Record purpose and hide unless role/use case requires it |
| Password hash / possible legacy plaintext | Authentication | `user.password` | Basic Auth create/login/update/reset | DB administrators; application process | Indefinite while soft-deleted | Hash needed while active; not after purge | Security/contract; plaintext compatibility must be removed after verified migration |
| Account status | Verification/access control | `user.primary_meta_data.status`; snapshots; JWT | System generated; returned in profile/member APIs | Subject; all company members; token holder | Indefinite | Internally necessary; broad disclosure unnecessary | Legitimate interest/security; minimize output |
| `is_superuser` | Global role authorization | `user.is_superuser`; snapshots; JWT | System/admin assignment outside exposed API; returned broadly | Subject; all company members; token holder | Indefinite | Internally necessary; response disclosure unnecessary | Security; separate internal principal from public profile |
| Password reset method, token, creation and expiry | Account recovery | `user.primary_meta_data.password_reset` | `/password-reset/*` | Application and DB operators; token/OTP also sent by SMTP/stdout | Cleared only after successful reset; expired/abandoned records persist | Temporary record needed; plaintext token is not | Security/legitimate interest; store a digest and purge on expiry |
| Refresh-token version | Revoke token family | `user.primary_meta_data.refresh_token_version`; JWT | Login/refresh/revoke/protected requests | Application, DB, token holder | Indefinite | Yes | Security safeguard; use dedicated typed field or session table |
| JWT user claims | Session authentication | Client-held access/refresh JWTs | Login/refresh responses and bearer requests | Client, intermediaries, anyone obtaining token | 15/60 minutes by default | User ID, token type/version needed; full profile is not | Minimize to `sub`, `type`, `jti`, `iat`, `exp`, issuer/audience and authorization version |
| Verification token/email | Verify ownership | JWT query parameter and verification email | `GET /user/verify`; resend/create email | Client/browser, SMTP, logs/stdout, application | Token valid 24 hours; log/email retention unknown | Temporary token needed | Use fragment/body exchange, redact logs, avoid email stdout |
| Reset OTP/magic link | Password recovery | Query/body, user JSON metadata, email | `/password-reset/*` | Client, SMTP, application, DB, logs/stdout | Default 60 minutes; template says 15; expired records persist | Temporary token needed | Cryptographic token; digest at rest; consistent expiry |
| Company UUID/name/description/industry | Tenant and business profile | `company` | Company CRUD and user-company list | Members; DB operators | Indefinite after soft deletion | Tenant ID/name necessary; other fields optional | Contract/legitimate interest; document each optional purpose |
| Company email/phone | Tenant contact | `company.email`, unique index; phone column | Create/get/user-company responses | Members; DB operators | Indefinite | Contact may be necessary; response scope should be justified | Juristic-person information; notice and retention required |
| Company address | Business address | `company.primary_meta_data.address` | Create/update/get/company list | Members; DB operators | Indefinite | Optional | Purpose, transfer, accuracy, and retention undocumented |
| Membership and role | Tenant access control | `association_user_company`; `company_role`; `role` | Company/user/role endpoints | Subject; company members/managers; superusers; DB operators | Soft-deleted indefinitely | Active relationship necessary; old history needs bounded policy | Contract/legitimate interest; invitation flow collects indirectly without notice |
| Actor snapshots (`added_by`, `removed_by`, `updated_by`, `created_by`, `deleted_by`, `assigned_by`) | Informal change attribution | JSON metadata on associations/roles/company-role | Company/member/role mutations | DB operators; potentially generic serializers | Indefinite, mutable, duplicated | Actor ID and event are useful; full profile is excessive | Replace with minimal immutable audit event and defined retention |
| Generic primary/secondary metadata | Status, address, reset, legacy role, actor data; unconstrained future data | Every ORM table via `TimestampMixin` | Repository JSON helpers | Application/DB operators | Indefinite | Some keys necessary; unrestricted buckets are not | Schema and purpose registry required; prevent unreviewed collection |
| Creation/update/closure timestamps | Record lifecycle and operations | Every table | System generated; mostly not returned | DB operators | Indefinite | Yes for lifecycle/audit | Retain only with parent purpose; use for automated lifecycle enforcement |
| IP address | Reset/resend abuse control and logs | In-memory limiter; application logs | Reset and resend endpoints | Application/log operators | Limiter: up to one hour per process; logs unknown | Necessary for security if proportionate | Legitimate interest/security; disclose, hash/truncate where possible, set log retention |
| User agent | Request diagnostics | Request middleware | Every request | Application/log operators if formatter/export changes | Unknown | Usually optional | Remove or document and bound; current formatter drops flat extras but other handlers may emit them |
| Raw query string | Diagnostics | Request middleware and HTTP access logs | Every query endpoint, including OTP/verification | Application/log/proxy operators | Unknown | Not necessary in raw form | Non-compliant for secret-bearing endpoints; allowlist/redact parameters |
| Request/correlation IDs, method, path, status, duration | Reliability/security diagnostics | Logs and response headers | Every request | Client and log operators | Unknown | Generally necessary | Document and retain briefly; paths may contain user/company UUIDs |
| Email recipient, subject and rendered body | Transactional delivery | Process memory, SMTP, stdout fallback, SMTP logs | Registration, verification, reset, invitation | SMTP operator, log operators, recipient | Operator dependent / unknown | Necessary for transaction; stdout copy is not | Operator agreement, transfer assessment, redaction and retention required |
| Prometheus metrics | Operations | Process metrics endpoint | `GET /metrics` | Unauthenticated network callers and scraper | Scraper dependent | Aggregate metrics useful | Authenticate/isolate; avoid raw endpoint IDs in labels |
| OpenTelemetry spans | Optional tracing; currently not enabled in app factory | External collector if enabled | Potentially every request/outbound request | Telemetry operator | Unknown | Optional | Before enabling, configure URL/header/body redaction, DPA and transfer basis |
| Profiling files | Performance diagnosis | Local `profiles/*.prof` when enabled | Requests with local `X-Profile` header | Host/file operators | Indefinite | Optional and diagnostic | Disable in production or auto-delete; verify reverse-proxy client identity |
| Uploaded files/profile photos/device IDs/OAuth identities/API keys/cookies | No implementation found | None | None | None | N/A | N/A | Reassess before adding any such feature |

## 4. Database and migration review

The local database contains the five expected application tables (14 user, 20 company, 7 role, 73 company-role, and 40 membership rows at audit time). Only aggregate counts and schema metadata were inspected. `alembic heads` reports `a4e8c1b7d2f9`; `alembic current` reports no applied revision, while the schema is usable. This local database is therefore not reliable evidence that production migrations are controlled.

| Table | Personal/sensitive information | Index exposure | Deletion behavior | Encryption/retention assessment |
|---|---|---|---|---|
| `user` | Names, unique email, phone, bcrypt/legacy password, privilege, status, reset secret, token version, timestamps, arbitrary metadata | PK and unique email indexes contain identifiers | `_closed_at` only; row and secrets remain; associations remain | Field/DB/backup encryption Needs Verification; expired secrets need automated purge |
| `company` | Identifiable juristic-person details, contact data and address | PK and unique email | `_closed_at` only; membership and role links remain | Encryption and lawful retention Needs Verification |
| `role` | Role data plus full creator/deleter snapshots | PK and unique role-name | Soft delete; shared global record may be linked to many tenants | Minimize actor data; immutable audit event needed |
| `company_role` | Tenant-role link plus full assigner snapshot | Composite PK/unique pair | Soft unassignment; FK cascade exists for company/role only | Historical link needs retention purpose; actor snapshot excessive |
| `association_user_company` | User-company relationship, privilege, full add/remove/update actor snapshots | Composite PK | Soft removal; user/company FKs do not specify cascade; record survives account/company closure | Define active/history partitions, anonymization and purge |

All tables inherit unconstrained `primary_meta_data` and `secondary_meta_data` plus timestamps (`app/repository/database/base_model.py:26-49`). Generic serialization can expose every database column when called directly (`base_model.py:232-241`), although current public read models usually constrain responses.

The seven migration files create and repeatedly reconstruct personal-data tables. `4f9d2f8f6c13` copies user passwords and JSON metadata during integer-to-UUID migration; it does not verify that passwords are hashed or remove obsolete metadata. `a4e8c1b7d2f9` normalizes globally shared roles but retains generic metadata. No revision introduces retention, consent, privacy requests, immutable audit events, token digests, encryption, anonymization, or a purge job. Migration backups, access controls, rollback data exposure, and production revision state need verification.

## 5. Endpoint and data-flow ledger

| Endpoint | Input and processing | Persistence/output | Access and audit result |
|---|---|---|---|
| `GET /` | No personal input | Environment/version/repository metadata | Public; Low disclosure/hardening issue |
| `GET /metrics` | No auth; Prometheus registry | Process and endpoint metrics | Public; restrict to internal monitoring |
| `POST /user/create` | Basic email/password plus optional name/phone | User row, status metadata; full profile response; verification email | Public registration; no privacy notice or age/lawful-basis capture |
| `PATCH /user/login` | Basic email/password | Token-version increment; access/refresh JWTs with full profile | No brute-force limiter; enumeration differs between unknown user and wrong password |
| `POST /user/refresh` | Refresh token body | New token pair, same family version | No true one-time refresh rotation; replay remains possible until expiry/revoke |
| `POST /user/revoke` | Refresh token body | Increments family version | Good family invalidation; no session inventory or device-level revoke |
| `GET /user/verify` | Verification JWT in query | Status becomes Active | Token may reach access/proxy logs; no single-use token ID |
| `POST /user/resend-verification` | Email body and client IP | In-memory rate state; email/logs | Enumeration-safe response; process-local limiter and PII logs |
| `GET /user/get` | Bearer token | Full self profile | Authenticated self access, but not full section 23 export/recipient history |
| `PATCH /user/update` | Optional name/phone/password | User fields/hash; full profile response | Self-only; cannot correct email; one-character password accepted |
| `GET /user/companies` | Filters and pagination | Company contact/address and role output | Self-only, active links; useful tenant isolation |
| `DELETE /user/me` | Bearer token | Sets user `_closed_at` | Revokes effective access via active-user lookup, but does not delete/anonymize |
| `PATCH /password-reset/request` | Email/method body and client IP | Plain reset token in user JSON; email/log data | Enumeration-safe response; process-local rate limit |
| `PATCH /password-reset/reset-with-token` | Token and new password body | Linear scan of all active users; clears token on success | One-character password; token stored plaintext; expired token not purged |
| `PATCH /password-reset/validate-otp` | OTP query plus Basic email/new password | Password update and token removal | Secret in URL; non-cryptographic six-character OTP |
| `POST /company` | Company/contact/address data | Company, default links, owner membership, actor snapshot | Authenticated; no collection notice or purpose registry |
| `GET /company` | Company email or UUID query | Company contact/address response | Membership required; pre-auth lookup yields 404 vs 403 existence signal |
| `PATCH /company/{company_id}` | Optional company profile/address | Company update | Owner/Administrator only; no correction propagation/audit event |
| `DELETE /company/{company_id}` | Company UUID | Company soft delete only | Owner only; memberships and personal data persist |
| `GET /company/{company_id}/users` | User filters/pagination | Full member profile and role | Any company member including Viewer; excessive email/phone/status/privilege output |
| `POST /company/{company_id}/users` | Existing user's email and role | Immediate active membership and full actor snapshot; invite email; full target profile output | Owner/Administrator; no invite acceptance; soft-deleted target is eligible |
| `DELETE /company/{company_id}/user/{user_id}` | Target UUID | Soft-closes membership; remover snapshot; returns full target profile | Owner/Administrator; owner protection exists |
| `PATCH /company/{company_id}/user/{user_id}` | Target UUID and role name | Role update; updater snapshot; full target profile | Owner/Administrator; role must belong to tenant |
| `GET /company/{company_id}/roles` | Filters/pagination | Tenant role list | Owner/Administrator only; Viewer cannot list even though user list exposes assigned role |
| `POST /company/{company_id}/role` | New global role data | Global role and tenant assignment | Superuser only; actor snapshot retained |
| `PATCH /company/{company_id}/role/{name}` | Global role update | Mutates shared role row | Superuser only; change can affect every linked tenant and needs impact audit |
| `DELETE /company/{company_id}/role` | Delete/replacement role names | Reassigns users and soft-deletes global role/link | Superuser only; shared-role impact must be verified across tenants |
| `POST /company/{company_id}/roles/{role_id}` | Role UUID | Tenant-role assignment and actor snapshot | Tenant Owner/Administrator; controlled by membership checks |
| `DELETE /company/{company_id}/roles/{role_id}` | Role UUID | Soft-closes tenant-role assignment | Tenant Owner/Administrator; blocks active user assignments |
| `GET /roles` | Filters/pagination | All global roles | Any authenticated user; role data is low sensitivity but scope is broader than other management APIs |
| `POST /roles` | Role data | Global role and creator snapshot | Superuser only |
| `PATCH /roles/{role_id}` | Role update | Global role mutation | Superuser only |
| `DELETE /roles/{role_id}` | Role UUID | Global soft delete and deleter snapshot | Superuser only; active assignment check exists |
| `POST /roles/{role_id}/companies` | Company UUID list | Bulk assignments and actor snapshots | Superuser only; invalid/foreign company handling is not privacy-specific |

FastAPI also exposes `/docs`, `/redoc`, and `/openapi.json` without authentication. There are no OAuth, cookie-session, API-key, file-upload, object-storage, analytics, scheduled-job, or general worker implementations. Background tasks are limited to in-process email delivery.

## 6. Findings

### F-01 — Account secrets can be disclosed through URLs and email stdout

- **Severity / priority:** Critical / P0
- **Affected files:** `app/api/routers/user/user_password_routes.py:85-107`; `app/api/routers/user/user_verification_routes.py:28-39`; `app/api/middleware/logging.py:17-24`; `app/email/sender.py:67-77,112-131,275-297`; `app/main.py:149-170`
- **Affected endpoints:** `GET /user/verify`, `PATCH /password-reset/validate-otp`, all verification/reset email paths
- **POPIA:** sections 8, 10, 19–22
- **Description:** OTPs and verification credentials are placed in request URLs. Raw queries are collected by middleware and may also be recorded by Uvicorn, reverse proxies, APM, browser history, referrers, and support tooling. If SMTP configuration is absent or DNS resolution fails, the application prints the complete email text, recipient and subject to stdout; reset templates contain the OTP or full magic link.
- **Risk:** Log readers can activate accounts or reset passwords. Log aggregation may create additional operators and cross-border copies.
- **Recommended fix:** Move OTP/verification secrets to request bodies or exchange a URL fragment for a body token; configure parameter redaction at app, proxy and APM layers; never print email bodies outside an explicit local-only sink; fail closed in production; hash stored reset tokens; inventory and purge existing logs; rotate the JWT secret and notify affected subjects if exposure is confirmed.
- **Effort / breaking change:** Medium / Yes (verification and OTP clients)

### F-02 — Soft deletion is indefinite retention, not erasure

- **Severity / priority:** High / P0
- **Affected files:** `app/repository/base.py:44-48`; `app/repository/user.py:176-183`; `app/repository/company.py:172-180`; `app/repository/database/base_model.py:26-49`
- **Affected endpoints:** `DELETE /user/me`, `DELETE /company/{company_id}`, membership/role deletion endpoints
- **POPIA:** sections 13–15, 23–25
- **Description:** Delete operations only set `_closed_at`. Names, emails, phones, password hashes, reset data, addresses, memberships and actor snapshots remain reconstructable indefinitely. There is no retention policy, restriction state, legal hold, anonymization, purge worker, backup expiry, or deletion propagation.
- **Risk:** Userverse cannot honor destruction requests or prove that information is not retained longer than necessary.
- **Recommended fix:** Adopt the schedule in section 8; model deletion requests/holds; revoke sessions immediately; anonymize or hard-delete eligible data within 30 days; minimize preserved audit evidence; cascade/anonymize relationships and snapshots; expire backups; produce a deletion certificate.
- **Effort / breaking change:** Large / Yes (schema and semantics)

### F-03 — Data-subject participation APIs and procedures are missing

- **Severity / priority:** High / P0
- **Affected files:** `app/api/routers/user/user_profile_routes.py:32-143`; no privacy router/models/service/repository
- **Affected endpoints:** Existing `GET /user/get`, `PATCH /user/update`, `DELETE /user/me` are only partial substitutes
- **POPIA:** sections 5, 11(3), 14(6), 23–25
- **Description:** There is no confirmation/access response describing all records and recipients, portable export, formal correction request, objection, restriction, withdrawal, request tracking, identity-proofing, refusal reason, deadline, or downstream notification.
- **Risk:** Statutory requests cannot be received, actioned, evidenced, or completed consistently.
- **Recommended fix:** Implement the `/privacy` contract in section 10 with an auditable request workflow, identity re-verification, holds, tenant boundaries, operator propagation and prescribed-form compatibility.
- **Effort / breaking change:** Large / No for additive API; deletion semantics later break

### F-04 — Invitations disclose and process profiles without acceptance, including deleted users

- **Severity / priority:** High / P0
- **Affected files:** `app/repository/company_user.py:80-113`; `app/services/company/user.py:72-104`; `app/email/templates/company_invite.html:3-16`
- **Affected endpoint:** `POST /company/{company_id}/users`
- **POPIA:** sections 9–13, 15, 18, 23–24
- **Description:** Supplying an existing email immediately creates membership and returns the target's full profile. The target does not accept, reject, or receive a collection notice. The lookup omits `User._closed_at.is_(None)`; the isolated probe confirmed a soft-deleted user is linked and returned.
- **Risk:** A manager who knows an email can reprocess a deleted account and disclose profile/privilege data inside a new tenant context without the subject's participation.
- **Recommended fix:** Create a pending invitation with a random, hashed, single-use token and expiry; reveal only delivery status to the inviter; require authenticated acceptance; reject closed/inactive accounts; allow decline/report; notify the subject under section 18 and log the lawful basis.
- **Effort / breaking change:** Medium / Yes

### F-05 — Company-member responses expose unnecessary profile and privilege data

- **Severity / priority:** High / P1
- **Affected files:** `app/models/company/user.py:6-7`; `app/models/user/user.py:39-50`; `app/repository/company_user.py:27-48,190-223`; `app/services/company/user.py:170-182`
- **Affected endpoints:** `GET/POST /company/{company_id}/users`, delete/update member responses
- **POPIA:** sections 9–10, 13, 19
- **Description:** Any active company member can list every member's email, phone, account status and global `is_superuser` flag. Mutations also return the target's full profile. Viewer access is not field-minimized.
- **Risk:** Contact and security information is disclosed beyond what is necessary for a directory or role-management task.
- **Recommended fix:** Introduce purpose-specific projections: Viewer receives display name and tenant role; managers receive only justified contact fields; never return `is_superuser` or global status; make contact visibility subject-controlled where possible; add field-level authorization tests.
- **Effort / breaking change:** Medium / Yes (response schema)

### F-06 — Password and reset controls permit weak or legacy credentials

- **Severity / priority:** High / P0
- **Affected files:** `app/models/user/user.py:9-20`; `app/models/user/password.py:20-22`; `app/services/user/password.py:34-42`; `app/repository/user.py:65-73`; `app/utils/hash_password.py:14-36`
- **Affected endpoints:** create, login, update, and all password-reset endpoints
- **POPIA:** sections 19–21
- **Description:** Password models accept a single character. OTP generation uses `random.choice`, confirmed by Bandit B311. Login can compare an unrecognized stored value directly with the supplied password and then upgrade it, proving the code expects possible plaintext legacy credentials. There is no compromised-password check, strength policy, password-change notification, or MFA.
- **Risk:** Account compromise and unauthorized processing are materially easier; a database compromise may expose legacy plaintext credentials.
- **Recommended fix:** Require at least 12 characters or a modern strength estimator; use `secrets` for OTPs; store token digests; inventory and force-reset all non-bcrypt credentials, then remove plaintext compatibility; notify on password change; offer MFA/passkeys and recovery controls.
- **Effort / breaking change:** Medium / Yes (password policy)

### F-07 — Abuse controls are incomplete and process-local

- **Severity / priority:** High / P1
- **Affected files:** `app/utils/rate_limiter.py:26-106`; `app/services/user/password.py:81-115`; `app/services/user/verification.py:75-107`; `app/services/user/basic_auth.py:108-120`
- **Affected endpoints:** login, create, refresh, reset and verification resend
- **POPIA:** sections 19–21
- **Description:** Only reset/resend requests are throttled. State is memory-only per worker and resets on restart, so horizontal replicas multiply limits. Login, account creation and refresh have no throttling, lockout/risk signal, or distributed abuse telemetry.
- **Risk:** Brute force, credential stuffing, email flooding and resource abuse can lead to unauthorized access or availability loss.
- **Recommended fix:** Use an atomic shared limiter with per-account, per-IP/network and global limits; normalize trusted proxy IPs; add progressive delay and security events without permanent denial-of-service lockouts; protect login/create/refresh/reset/resend; alert on distributed attacks.
- **Effort / breaking change:** Medium / Potential 429 behavior

### F-08 — No privacy notice, processing register, lawful-basis register, or accountable owner is evidenced

- **Severity / priority:** High / P0
- **Affected files:** `README.md`, `docs/`, API schemas; no privacy/governance documentation
- **Affected endpoints:** Every collection endpoint
- **POPIA:** sections 8–18, 55–56; PAIA documentation referenced by section 17
- **Description:** The repository does not identify the responsible party or Information Officer, state collection purposes and mandatory/optional consequences, list recipients/transfers/retention, document lawful bases, or provide regulator/right details. Consent should not be substituted for another valid basis, but every purpose still needs a recorded basis.
- **Risk:** Collection is not transparent and Userverse cannot meet its burden of accountability.
- **Recommended fix:** Approve a processing register and section 18 notice; appoint/register the Information Officer; publish contact and request procedures; conduct a personal-information impact assessment; version notices and lawful-basis decisions; review on every schema/integration change.
- **Effort / breaking change:** Medium / No

### F-09 — Security-compromise and operator obligations are not implemented or evidenced

- **Severity / priority:** High / P0
- **Affected files:** No incident/breach module or runbook; `app/email/sender.py`; `app/api/middleware/otel.py`
- **Affected endpoints:** All processing
- **POPIA:** sections 19–22, 55
- **Description:** No detection-to-assessment workflow, affected-subject register, Information Officer escalation, notification template, evidence preservation, or Regulator eServices procedure exists. Written operator security clauses and immediate operator notification obligations for SMTP, hosting, database, backup, log and telemetry providers are not evidenced.
- **Risk:** A compromise may not be contained or reported as soon as reasonably possible. The Regulator's current guidance states that all security compromises must be reported, irrespective of risk.
- **Recommended fix:** Establish and exercise an incident plan aligned to SCN1/eServices; maintain an operator register and agreements; define 24/7 escalation, evidence, notification content, subject communication, decision log and post-incident review.
- **Effort / breaking change:** Medium / No

### F-10 — Mutable metadata duplicates full actor profiles without reliable auditability

- **Severity / priority:** Medium / P1
- **Affected files:** `app/repository/company_user.py:101-110,137-170`; `app/repository/company_role.py:115-128,363-400`; `app/repository/database/tables/role.py:267-295`; `app/repository/database/base_model.py:42-49`
- **Affected endpoints:** Company membership and role mutations
- **POPIA:** sections 8, 10, 13–16, 19
- **Description:** Full `UserReadModel` snapshots—including email, phone, status and superuser flag—are copied into mutable JSON. Keys can be overwritten, stale data cannot be rectified centrally, and there is no append-only audit record or integrity control.
- **Risk:** Unnecessary duplicate data persists and the supposed audit evidence is neither minimal nor trustworthy.
- **Recommended fix:** Store only actor UUID in domain rows; create an append-only audit-event table with event ID, tenant, actor, action, target, timestamp, outcome and minimal diff; restrict access; cryptographically protect/export events where warranted; apply retention and subject-access filtering.
- **Effort / breaking change:** Large / Data migration required

### F-11 — JWTs overcollect profile data and refresh tokens are replayable

- **Severity / priority:** Medium / P1
- **Affected files:** `app/api/security/jwt.py:39-78,113-195`; `app/models/user/user.py:39-69`; `app/repository/user.py:141-174`
- **Affected endpoints:** login, refresh, revoke and every protected endpoint
- **POPIA:** sections 10, 13, 19
- **Description:** Both tokens contain the full user profile. Tokens omit `sub`, `jti`, `iat`, issuer and audience. Refresh produces a new pair without advancing the family version, so the presented refresh token remains usable until expiry or explicit revocation.
- **Risk:** Token leakage exposes extra PII and permits replay. Claim validation is harder across services/environments.
- **Recommended fix:** Minimize claims; implement one-time refresh-token rotation and reuse detection in a hashed session store; add issuer/audience/issued-at/JTI; support device/session listing and selective revocation; keep short access lifetime.
- **Effort / breaking change:** Medium / Yes (token contract)

### F-12 — Consent, children, special information, and marketing controls are absent

- **Severity / priority:** Medium / P1
- **Affected files:** User and company request models; email templates; no consent/age/special-category model
- **Affected endpoints:** registration, optional profile collection, invitations, any future marketing/integration endpoint
- **POPIA:** sections 11, 18, 26–35, 57–59, 69, 71–72
- **Description:** The current code sends transactional messages and does not show analytics or marketing, so consent is not automatically the correct basis for core service processing. However, there is no age/competent-person handling, consent evidence for optional consent-based purposes, withdrawal, marketing suppression, automated-decision inventory, or prior-authorisation gate.
- **Risk:** The service cannot safely expand to children, special information, direct marketing, analytics, OAuth, or external matching; actual user demographics are unknown.
- **Recommended fix:** Confirm whether children can register; prohibit or implement competent-person/Regulator controls; create purpose-specific versioned consent only where consent is the chosen basis; maintain permanent marketing suppression; require privacy review/prior-authorisation assessment for new sensitive processing.
- **Effort / breaking change:** Medium / Potential registration changes

### F-13 — Deployment, storage, logging, and observability safeguards need verification and hardening

- **Severity / priority:** Medium / P1
- **Affected files:** `app/configs.py:62-194`; `app/main.py:49-82,95-118`; `app/repository/database/session_manager.py:62-88`; `app/exceptions.py:16,204-240`; `app/api/middleware/profiling.py`; `app/api/middleware/otel.py`
- **Affected endpoints:** All; especially `/metrics`, docs and debug/error paths
- **POPIA:** sections 19–22, 72
- **Description:** TLS termination, database/backup encryption, DB least privilege, key rotation, log retention/access, WAF, network isolation and restore testing are absent from repository evidence. Metrics and API docs are public. CORS allows all methods/headers for configured origins. `DEBUG_ERRORS`, DB echo and profiling can expose data if enabled. Telemetry has a plaintext default collector URL and no redaction policy, although it is currently disabled.
- **Risk:** Actual compliance depends on deployment controls that cannot be assumed; unsafe flags or exposed operational endpoints increase disclosure.
- **Recommended fix:** Enforce production startup policy for HTTPS origins, strong secrets, disabled debug/echo/profile, private authenticated metrics/docs, encrypted DB/backups, least-privilege accounts and restricted networks; document key/backup/log lifecycle; configure telemetry redaction and section 72 transfer controls.
- **Effort / breaking change:** Medium / Deployment changes

### F-14 — Dependency and container supply-chain controls are incomplete

- **Severity / priority:** Medium / P2
- **Affected files:** `uv.lock`; `pyproject.toml`; `Dockerfile:1-12`; `.github/workflows/build-and-test.yml`
- **Affected endpoints:** Build and runtime environment
- **POPIA:** sections 19–21
- **Description:** The frozen dependency audit found Click 8.3.1 vulnerable to command injection in `click.edit()`; Userverse does not call that function, but 8.3.3 is available. The Docker build copies only `pyproject.toml`, runs an unconstrained `uv sync`, includes development tooling, uses mutable image tags, and runs as root. CI has tests but no dependency, secret, SAST, container or SBOM gates.
- **Risk:** Builds are not reproducible from the reviewed lock and known vulnerabilities or compromised dependencies/images may reach production.
- **Recommended fix:** Upgrade Click; copy and enforce `uv.lock --frozen --no-dev`; use a minimal non-root image pinned by digest; generate SBOM/provenance; add recurring audit, secret, SAST and image scans with remediation SLAs.
- **Effort / breaking change:** Small–Medium / No API break

### F-15 — Information quality cannot be maintained across copies and messages

- **Severity / priority:** Medium / P2
- **Affected files:** `app/models/user/user.py:14-24`; `app/models/company/company.py:27-53`; actor metadata locations in F-10; `app/email/templates/reset_user_password.html:6-12`; `app/configs.py:163-169`
- **Affected endpoints:** user/company update, reset emails, privacy correction (missing)
- **POPIA:** sections 16, 24
- **Description:** Users cannot change an email; companies cannot update their email; stale actor snapshots cannot be centrally corrected; there is no provenance or recipient correction process. The OTP email says 15 minutes while the configured default expiry is 60 minutes.
- **Risk:** Data may be inaccurate or misleading, and correction cannot propagate to derived copies or recipients.
- **Recommended fix:** Add verified email-change workflows; define authoritative sources and validation; eliminate profile snapshots; notify recipients/operators of material corrections; render expiry from configuration; add consistency tests.
- **Effort / breaking change:** Medium / Additive except snapshot migration

## 7. Eight-condition compliance matrix

| POPIA requirement | Status | Evidence | Recommended action |
|---|---|---|---|
| Accountability (s8) | Non-compliant | Strong tests and some security checks exist, but no owner, processing register, PIIA, immutable audit, rights or continuous compliance evidence | Implement F-08, F-09, F-10 and compliance release gates |
| Processing limitation (ss9–12) | Non-compliant | Direct registration is mostly from the subject; invitations are indirect; profile/JWT/log metadata is excessive; lawful bases are undocumented | Minimize F-04/F-05/F-10/F-11 and document purpose/basis/objection |
| Purpose specification (ss13–14) | Non-compliant | No purpose register or retention/purge/restriction mechanism; soft deletion retains intelligible records | Implement F-02 and approved schedule |
| Further processing limitation (s15) | Non-compliant | No compatibility assessment for actor snapshots, logs, SMTP, telemetry or new integrations | Add privacy review and purpose/recipient enforcement |
| Information quality (s16) | Partial | Names/phones/company fields can be updated and validated; emails, snapshots, recipient propagation and expiry copy are deficient | Implement F-15 and privacy correction workflow |
| Openness (ss17–18) | Non-compliant | No section 18 notice, PAIA/processing documentation, responsible-party contact, recipient/transfer disclosure or rights information | Publish versioned notice and register before collection |
| Security safeguards (ss19–22) | Non-compliant | Bcrypt, ORM, token-family invalidation and tenant checks help; F-01/F-06/F-07 and missing operational/breach/operator evidence remain material | Remediate P0 security items and verify infrastructure/operators |
| Data subject participation (ss23–25) | Non-compliant | Self profile/update/soft delete are partial; no complete access/export, request, objection, restriction, proof or notification workflow | Implement F-03 and deletion/correction lifecycle |

## 8. Recommended retention and deletion schedule

These are risk-based technical defaults, not statements of mandatory South African statutory periods. The Information Officer and counsel must document any contract/statute/legitimate-interest exception before extending them.

| Record | Recommended default | End-of-period action | Exception/control |
|---|---|---|---|
| Active user profile and current memberships | While account/service relationship is active | On verified closure, revoke immediately and delete/anonymize within 30 days | Preserve only fields under documented legal hold |
| Closed company profile and active links | 30 days after verified closure | Delete/anonymize tenant contacts/address and close links | Contract/dispute hold with recorded owner and expiry |
| Password hash | Active account only | Delete with account; never retain in audit | Force-reset legacy non-bcrypt values immediately |
| Reset OTP/magic token | Until used or expiry (maximum configured 60 minutes) | Delete immediately on use; purge expired values within 24 hours | Store digest only; no exception |
| Verification token | Maximum 24 hours | No server record unless single-use digest; purge digest within 24 hours after expiry/use | Do not retain token in logs |
| Access/refresh session records | Access expiry plus refresh expiry; current defaults 15/60 minutes | Purge expired sessions within 24 hours | Security event may retain token ID, never token value |
| Invitation | 7 days, one renewal | Purge token; retain minimal accepted/declined outcome for 90 days | No profile disclosure before acceptance |
| Rate-limit keys | One-hour window plus up to 24 hours for abuse analysis | Delete or irreversibly aggregate | Hash normalized email/IP keys where practical |
| Request/access logs | 30 days | Delete; retain de-identified aggregates | Security incident hold approved by Information Officer |
| Security/audit events | 12 months | Delete or de-identify | Extend to 36 months only with documented dispute/security need |
| Email delivery metadata | 30 days | Delete recipient-level metadata | Keep aggregate delivery metrics; never retain email bodies/secrets |
| Privacy/consent request evidence | Life of decision plus 3 years | Delete/anonymize | Counsel to confirm limitation/complaint requirements |
| Consent proof and suppression | Consent life plus 3 years; suppression while marketing could recur | Delete consent detail; keep minimal suppression marker | Needed to prove consent/withdrawal without re-contacting |
| Metrics/traces | Metrics 13 months aggregated; traces 7–14 days | Delete identifiers/raw URLs | Shorter where query/tenant identifiers cannot be removed |
| Profiling files | Maximum 7 days in non-production | Secure delete | Production profiling disabled by default |
| Backups | Rolling maximum 35 days | Cryptographic erase/expiry and tested purge | Restored data must reapply deletion ledger before service |

## 9. Third-party and operator register

| Service/category | Data shared | Purpose | Necessity | Status / required action |
|---|---|---|---|---|
| Configured SMTP provider | Recipient email/name, company/role, OTP/reset/verification links, message metadata | Transactional email | Necessary if email flows retained | **Needs Verification:** operator contract ss20–21, location/subprocessors, TLS, retention, breach SLA, section 72 basis |
| Hosting/container platform | All runtime data, env secrets, logs, process memory | Run service | Necessary | **Needs Verification:** region, access, encryption, isolation, incident and deletion terms |
| Database provider (SQLite/Postgres/MySQL supported) | All persisted personal information | Persistence | Necessary | **Needs Verification:** production vendor, encryption, role separation, audit, backup and residency |
| Backup provider | Full database copies | Recovery | Necessary if backups used | **Needs Verification:** encryption, 35-day expiry, restore controls, deletion replay, operator contract |
| Log/monitoring platform | Email/IP/path/query/UUID/error data depending pipeline | Operations/security | Partly necessary | **Needs Verification:** redact, minimize, access/retention, incident/transfer terms |
| OTLP/OpenSearch collector | Request/span attributes if optional module is enabled | Tracing | Optional | Currently not wired into `create_app`; complete privacy review before enabling |
| Prometheus scraper | Aggregate application/error/email metrics; endpoint labels | Monitoring | Useful | Endpoint is currently public; isolate and ensure labels do not contain raw IDs |
| GitHub Actions/Codecov | Source, tests and coverage—not production records by design | CI/coverage | Development service | Verify fixtures stay synthetic; token permissions/retention; no production database use in CI |
| PyPI/GHCR/uv image sources | Build metadata/dependencies | Build | Necessary | Pin hashes/digests, verify provenance, generate SBOM |

No code-visible OAuth, analytics, advertising, payment, object-storage, file-storage, CDN, SMS, cookie-tracking, or customer-support integration was found.

## 10. Missing features and proposed privacy API

### 10.1 Required capabilities

- Versioned privacy notice and processing/lawful-basis register.
- Information Officer ownership/contact and PAIA/POPIA request procedure.
- Access/export, correction, deletion, objection, restriction and consent-withdrawal workflows.
- Retention scheduler, legal holds, anonymization, hard deletion and backup deletion replay.
- Pending invitation/acceptance workflow.
- Immutable minimal audit trail with controlled subject access.
- Breach register, notification workflow and operator-management evidence.
- Consent/suppression registry only for purposes that actually rely on consent.
- Child/special-information and prior-authorisation gates.
- Data inventory/lineage and third-party recipient register.

### 10.2 Proposed public contract

All `/privacy/me/*` and `/privacy/requests*` routes require an active bearer session. Export, deletion and email correction additionally require recent password/MFA re-authentication. Responses must never include password hashes, token values, other subjects' profiles, internal security notes, or data lawfully withheld under PAIA.

| Method/path | Contract |
|---|---|
| `GET /privacy/notice` | Public versioned notice: `version`, `effective_at`, responsible party/address/Information Officer, purposes with categories/lawful basis/required status/consequences/recipients/retention, transfers, rights, complaint details |
| `GET /privacy/me/export` | Synchronous JSON export: schema version, generation time, profile, companies and memberships, subject-visible audit events, consents, privacy requests and recipient categories; downloadable format may be added later |
| `GET /privacy/requests` | List only the authenticated subject's requests and statuses |
| `POST /privacy/requests` | Body: `type` (`access`, `correction`, `deletion`, `objection`, `restriction`), `scope`, optional `reason`, correction `changes`, notice version, idempotency key; return `202`, request UUID and target response date |
| `GET /privacy/requests/{id}` | Status (`received`, `identity_pending`, `in_review`, `restricted`, `fulfilled`, `partially_fulfilled`, `refused`, `cancelled`), timestamps, subject-safe actions, outcome/refusal basis and appeal/contact information |
| `POST /privacy/requests/{id}/verify` | Complete stepped-up identity proof without storing raw proof longer than necessary |
| `POST /privacy/requests/{id}/cancel` | Cancel an uncompleted request where legally permitted; keep evidence of cancellation |
| `GET /privacy/me/consents` | Current purpose-specific consent and notice versions, timestamps, source and withdrawal state |
| `PUT /privacy/me/consents/{purpose}` | Record affirmative consent only for an allowed, specific, optional purpose and current notice version |
| `DELETE /privacy/me/consents/{purpose}` | Withdraw consent and trigger downstream cessation/propagation; preserve minimal proof and marketing suppression |

The implementation needs typed `PrivacyRequest`, `PrivacyRequestEvent`, `ConsentRecord`, `ProcessingPurpose`, `RetentionHold`, `AuditEvent`, and `Invitation` tables. Privacy-request status transitions must be append-only, tenant scoped, concurrency safe, and attributed to a minimal actor ID. Operator propagation attempts and deletion/anonymization results must be recorded without copying the subject's full profile.

## 11. Technical debt that strengthens compliance

- Replace generic JSON metadata with typed columns/tables and JSON schemas for unavoidable extension data.
- Separate internal principal, self-profile, member-directory and admin response models.
- Replace error strings/caller filesystem paths with stable public codes and structured internal events; ensure the JSON formatter handles an allowlist rather than silently dropping flat context.
- Normalize email casing consistently and implement verified email change.
- Make expiry text derive from configuration rather than hardcoded template copy.
- Make startup fail in production for default secrets, HTTP service/front-end URLs, public metrics/docs, DB echo, profiling or debug errors.
- Add schema-revision verification to startup/health checks; the audited local DB has no Alembic revision record.
- Remove dead/unreachable code in company-role pagination and the empty API-key module.
- Document negative security tests instead of relying only on high aggregate coverage.

## 12. Prioritized remediation roadmap

| Phase | Target | Outcomes |
|---|---|---|
| 0 — Contain (0–72 hours) | F-01, F-06, exposed logs | Stop email stdout, redact queries, move OTP off URL, rotate/assess secrets, enforce password minimum, use `secrets`, inspect log access and initiate breach workflow if exposure occurred |
| 1 — Establish control (first sprint) | F-04, F-05, F-07, F-08, F-09 | Block deleted-user invites, minimize member responses, distributed abuse protection, publish interim notice/contact, appoint response owner and operator register |
| 2 — Rights and lifecycle (2–4 sprints) | F-02, F-03, F-10, F-15 | Privacy request/export API, retention/hold/purge, invitation acceptance, immutable audit, correction propagation |
| 3 — Hardening (parallel, 1–3 sprints) | F-11–F-14 | Session rotation/MFA design, child/consent gates, deployment baseline, dependency/container/CI gates |
| 4 — Assure (ongoing) | All | PIIA, legal signoff, operator audits, breach exercise, restore/deletion test, quarterly access review and annual audit |

## 13. Implementation-ready GitHub issue drafts

### Ticket 1 — P0: Eliminate reset/verification secret exposure

- **Finding:** F-01.
- **Description:** Remediate F-01 across API, email, logging, proxy and historical log handling.
- **Acceptance criteria:** OTP is body-only; verification uses fragment/body exchange or redacted one-time URL; no app/proxy/APM log contains sentinel secrets; production never prints email content; stored reset tokens are digests; secret rotation/breach decision is recorded.
- **Technical notes:** Add central URL/header/body redaction and fail production startup if email delivery would use stdout.
- **Dependencies:** Frontend/client coordination; infrastructure log-owner review.
- **Complexity / priority:** Medium / P0.
- **Verification:** Automated sentinel tests across success/error/access logs plus log-platform search.

### Ticket 2 — P0: Implement retention, legal holds, anonymization and purge

- **Finding:** F-02.
- **Description:** Replace indefinite soft deletion with the lifecycle in section 8.
- **Acceptance criteria:** Typed retention policy; immediate token revoke/restriction; 30-day deletion SLA; cascades/snapshot anonymization; expired reset/invite/session purge; backup deletion replay; legal holds have owner/reason/expiry; deletion certificate is produced.
- **Technical notes:** Ship idempotent batches, dry-run metrics, retry/dead-letter handling and migration for existing closed rows.
- **Dependencies:** Information Officer/counsel approval; Ticket 8 audit events.
- **Complexity / priority:** Large / P0.
- **Verification:** Seed each lifecycle state, advance time, run twice, confirm eligible data cannot be reconstructed.

### Ticket 3 — P0: Add privacy notice and data-subject request API

- **Finding:** F-03.
- **Description:** Implement section 10's `/privacy` contract and operational queue.
- **Acceptance criteria:** Notice is versioned; export covers all subject data/recipient categories; request types/statuses work; identity proof and deadlines are tracked; refusals/partial results are reasoned; tenant isolation and downstream notification are tested.
- **Technical notes:** Encrypt any identity-proof artifact and delete it promptly; filter other subjects and security-sensitive records.
- **Dependencies:** Tickets 2, 7 and 8; approved PAIA/POPIA procedure.
- **Complexity / priority:** Large / P0.
- **Verification:** End-to-end access, correction, deletion, objection and restriction cases including hold/refusal paths.

### Ticket 4 — P0: Replace immediate membership with invitation acceptance

- **Finding:** F-04.
- **Description:** Remediate F-04 and prevent processing of closed/inactive targets.
- **Acceptance criteria:** Inviter receives no target profile; invite is pending, hashed, single-use and seven-day expiry; closed users are rejected without enumeration; subject accepts/declines; no membership exists before acceptance; notice and audit event are recorded.
- **Technical notes:** Rate-limit invites and support cancellation/reissue without duplicate membership.
- **Dependencies:** Ticket 8; frontend acceptance page.
- **Complexity / priority:** Medium / P0.
- **Verification:** Deleted/inactive/unknown/cross-tenant/replay/concurrent acceptance tests.

### Ticket 5 — P1: Minimize JWT and company-member response data

- **Findings:** F-05 and F-11.
- **Description:** Create purpose-specific projections and claims for F-05/F-11.
- **Acceptance criteria:** Viewer directory excludes email/phone/status/superuser unless explicitly justified; mutations return minimal target data; JWT contains no profile/contact fields; contract docs and compatibility migration exist.
- **Technical notes:** Use opaque subject ID and tenant authorization queries; do not encode authorization solely in stale client claims.
- **Dependencies:** Client inventory.
- **Complexity / priority:** Medium / P1.
- **Verification:** Snapshot/OpenAPI tests by role and decoded-token assertions.

### Ticket 6 — P0: Harden passwords, reset credentials and legacy migration

- **Finding:** F-06.
- **Description:** Remediate F-06.
- **Acceptance criteria:** Consistent 12-character/strength policy; cryptographic OTP; token digests; all non-bcrypt rows inventoried and force-reset; plaintext comparison removed; password-change notification; secrets never appear in telemetry.
- **Technical notes:** Consider Argon2id migration with parameter rehash; avoid composition rules that reduce usability.
- **Dependencies:** Ticket 1; customer communication.
- **Complexity / priority:** Medium / P0.
- **Verification:** weak-password, entropy, expiry, replay, digest-at-rest and legacy-row tests.

### Ticket 7 — P1: Deploy shared abuse protection and authentication telemetry

- **Finding:** F-07.
- **Description:** Cover login/create/refresh/reset/resend with distributed limits.
- **Acceptance criteria:** Atomic shared counters; trusted proxy handling; per-account/IP/network/global policies; progressive delay; safe 429 responses; alert thresholds; no raw email/IP in metric labels.
- **Technical notes:** Hash keys with rotating server-side pepper; prevent attacker-triggered permanent lockouts.
- **Dependencies:** Shared cache/edge service and operations owner.
- **Complexity / priority:** Medium / P1.
- **Verification:** multi-worker concurrency, restart, proxy, spray and enumeration tests.

### Ticket 8 — P1: Introduce minimal immutable audit events and remove actor snapshots

- **Finding:** F-10.
- **Description:** Replace mutable full-profile metadata in F-10.
- **Acceptance criteria:** Append-only event schema; actor/tenant/action/target/outcome/minimal diff; no email/phone/status/superuser snapshots; restricted access/export; integrity and retention controls; migration anonymizes old metadata.
- **Technical notes:** Keep audit storage separate from API serialization; use actor tombstones after deletion.
- **Dependencies:** Ticket 2 retention decisions.
- **Complexity / priority:** Large / P1.
- **Verification:** tamper/authorization/concurrency/retention and subject-export filtering tests.

### Ticket 9 — P0: Establish POPIA governance, notice and operator register

- **Findings:** F-08 and F-09.
- **Description:** Remediate F-08/F-09 organizational evidence.
- **Acceptance criteria:** Registered Information Officer evidence; PIIA; processing/lawful-basis register; section 18 notice; PAIA/rights procedure; complete operator/subprocessor/transfer register and signed clauses; quarterly review owner.
- **Technical notes:** Link purposes to API fields and schema-change checklist.
- **Dependencies:** Legal/Information Officer input.
- **Complexity / priority:** Medium / P0.
- **Verification:** Evidence review against ss8–22 and current Regulator guidance.

### Ticket 10 — P0: Implement and exercise security-compromise response

- **Finding:** F-09.
- **Description:** Create section 22 workflow and runbook.
- **Acceptance criteria:** detection intake, severity-independent report decision, Information Officer escalation, subject/Regulator templates, eServices/SCN1 steps, evidence log, operator SLA, tabletop exercise and post-incident actions.
- **Technical notes:** Notification is as soon as reasonably possible; do not wait for investigation completion where reasonable grounds exist.
- **Dependencies:** Ticket 9 contacts/operators.
- **Complexity / priority:** Medium / P0.
- **Verification:** Tabletop covering SMTP/log exposure and operator-originated compromise.

### Ticket 11 — P1: Rotate refresh tokens and add session management/MFA

- **Finding:** F-11.
- **Description:** Implement F-11 authentication-session controls.
- **Acceptance criteria:** One-time hashed refresh tokens; reuse revokes family; issuer/audience/JTI/IAT validation; session/device list and selective revoke; MFA/passkey enrollment and recovery; no PII claims.
- **Technical notes:** Phase token contract with explicit compatibility window.
- **Dependencies:** Ticket 5 and client changes.
- **Complexity / priority:** Large / P1.
- **Verification:** replay, theft, concurrent refresh, downgrade, expiry and inactive/deleted-user tests.

### Ticket 12 — P1: Add consent, child-data and new-processing privacy gates

- **Finding:** F-12.
- **Description:** Prevent unsupported sensitive/marketing expansion.
- **Acceptance criteria:** Age/eligibility decision approved; competent-person flow or child prohibition; purpose-specific versioned consent/withdrawal; marketing suppression; automated-decision and prior-authorisation checklists; CI/design-review gate for new PII fields/processors.
- **Technical notes:** Do not request consent where contract/legal/legitimate-interest basis is appropriate.
- **Dependencies:** Ticket 9 processing register; counsel.
- **Complexity / priority:** Medium / P1.
- **Verification:** withdrawal propagation, notice-version and prohibited-child registration cases.

### Ticket 13 — P1: Enforce production security and observability baseline

- **Finding:** F-13.
- **Description:** Close F-13 operational gaps.
- **Acceptance criteria:** HTTPS-only public URLs; encrypted DB/backups; least-privilege DB/network; private authenticated metrics/docs; debug/echo/profile disabled; secrets manager/rotation; redacted telemetry; documented log/backup retention and restore/deletion tests.
- **Technical notes:** Add machine-checkable startup validation and deployment policy.
- **Dependencies:** Infrastructure owner and operator register.
- **Complexity / priority:** Medium / P1.
- **Verification:** production-like configuration tests and independent control evidence.

### Ticket 14 — P2: Add reproducible secure build and continuous scanning

- **Finding:** F-14.
- **Description:** Remediate F-14.
- **Acceptance criteria:** Click >=8.3.3; Docker uses frozen lock/no dev/non-root/digest; SBOM and provenance artifacts; SAST/dependency/secret/image scans gate CI; vulnerability SLA and exception process documented.
- **Technical notes:** Confirm `click.edit()` is unused until upgrade ships; triage scanner false positives rather than suppressing globally.
- **Dependencies:** CI/container registry.
- **Complexity / priority:** Small–Medium / P2.
- **Verification:** clean frozen build, scanner fixtures, image user/SBOM assertions.

### Ticket 15 — P2: Implement verified correction and data-quality propagation

- **Finding:** F-15.
- **Description:** Remediate F-15.
- **Acceptance criteria:** Verified user/company email changes; correction requests; authoritative source/provenance; stale snapshots removed; recipients/operators notified when required; reset email displays actual configured expiry.
- **Technical notes:** Email changes must invalidate sessions and require verification of old/new channels with safe recovery.
- **Dependencies:** Tickets 3 and 8.
- **Complexity / priority:** Medium / P2.
- **Verification:** duplicate email, lost-channel, rollback, propagation and expiry-copy tests.

## 14. Needs-verification evidence request

The following must not be marked compliant until documentary or runtime evidence is supplied:

- Responsible party legal name/address; registered Information Officer and deputies; PAIA manual and request contacts.
- Approved processing register, lawful-basis decisions, privacy notices/versions, consent records and PIIA.
- User eligibility/age policy and whether children or special personal information are actually processed.
- Production architecture, public ingress, TLS/HSTS, CORS origins, WAF/rate limiting and admin access paths.
- Production database type/provider/region, encryption, accounts/roles, audit logs, patching, backup/restore and deletion behavior.
- Secret manager, JWT/key rotation, access review and incident history.
- Log/proxy/APM configuration, raw-query/header/body capture, retention, access list, regions and prior token exposure search.
- SMTP provider, location, subprocessors, TLS, retention, operator agreement and incident SLA.
- Any enabled telemetry, metrics scraper, profiling, analytics, support, CRM, file/object storage or other untracked integration.
- Written operator agreements and section 72 basis for each foreign recipient/subprocessor.
- Incident response plan, breach register, SCN1/eServices access, exercises and prior notifications.
- Legal/statutory/contractual retention requirements and active holds.
- Production Alembic revision state and migration/rollback/backup access controls.
- Historical repository secret scan and rotation evidence for any previously committed credential.

## 15. Requested-scope coverage ledger

| Requested area | Disposition |
|---|---|
| FastAPI routes and responses | Reviewed; endpoint ledger and F-03–F-05/F-13 |
| Authentication, sessions, JWT, refresh/revoke, MFA | Reviewed; F-01/F-06/F-07/F-11; MFA absent |
| Authorization/RBAC/multi-tenant isolation | Reviewed; primary checks generally present; F-04/F-05 and shared-role impact noted |
| User/company/role management | Reviewed end to end |
| Invitation flow | Reviewed; F-04 |
| Email verification/password reset | Reviewed; F-01/F-06/F-07/F-15 |
| Audit logging | No compliant audit trail; F-10 |
| Database models/migrations/indexes/deletion | Reviewed; sections 4/8 and F-02/F-10 |
| File/object storage/uploads | Not present in repository |
| Logging/SQL logs/telemetry/metrics/profiling | Reviewed; F-01/F-13; deployment pipeline Needs Verification |
| Background workers/scheduled jobs | No general worker/scheduler; in-process email tasks only; retention scheduler absent |
| Configuration/environment/secrets | Reviewed without revealing local values; F-13/F-14 |
| TLS/encryption/backups/database permissions | Not evidenced; Needs Verification/F-13 |
| Rate limiting/brute force | Reviewed; F-07 |
| CSRF | No cookie-authenticated state; currently not applicable; reassess if cookies are added |
| CORS/XSS/SQL injection | ORM parameterization and Jinja autoescaping reduce risk; CORS/deployment Needs Verification; no browser UI reviewed |
| Dependency vulnerabilities | Scanned; one current Click advisory, F-14 |
| Tests/CI/docs/TODO/debug shortcuts | Reviewed; 366-pass baseline; one role-test TODO; F-13/F-14 and technical debt |
| Consent/privacy notice/direct marketing/children | Missing or Needs Verification; F-08/F-12 |
| Access/export/rectification/deletion/objection/restriction | Partial profile/update/soft delete only; F-02/F-03/F-15 |
| Third parties/operators/transborder flows | Code-visible services inventoried; contracts/locations Needs Verification |
| Data retention/anonymization | Missing; schedule proposed in section 8 |
| Breach notification | Missing; F-09 and Ticket 10 |

## 16. Conclusion

Userverse should not represent itself as POPIA compliant on the current evidence. The immediate objective is containment of secret exposure and unsafe deleted-user invitation behavior, followed by an accountable privacy program, a real deletion/retention lifecycle, and data-subject request capability. Compliance can only move from code-level remediation to an evidenced conclusion after the Information Officer verifies deployment controls, operators, transfers, notices, legal bases, retention exceptions and incident procedures.
