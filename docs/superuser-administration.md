# Superuser Bootstrap and Administration

Userverse treats `is_superuser` as a platform recovery and bootstrap authority.
It is deliberately separate from global roles, platform-role assignments, and
company membership.

This release implements only the one-time offline bootstrap command. Superuser
promotion APIs, step-up authentication, demotion, and access-review endpoints
are documented below as follow-up work and are not currently available.

## Security model

The bootstrap command:

- must be run from a trusted host, application container, or Kubernetes job
  that already has database access;
- promotes an existing user and never creates an account;
- never accepts a password, access token, or refresh token;
- requires the user to be active, verified, and not soft-deleted;
- serializes attempts through the singleton `superuser_bootstrap_control` row;
- refuses to run if any superuser already exists;
- is idempotent only for the original, still-superuser account;
- records `superuser_bootstrapped` in `privileged_access_event` in the same
  transaction as the promotion; and
- increments the target's refresh-token version, invalidating all existing
  access and refresh tokens.

Do not add automatic startup promotion, a `SUPERUSER_EMAIL` environment
variable, a public "first user" endpoint, or a data migration containing an
administrator email. Those mechanisms can silently grant platform-root access
in the wrong environment.

## Bootstrap procedure

### 1. Register and verify the account

Create the administrator through the normal registration flow. Confirm the
account status is `Active` before continuing. The CLI will not activate or
verify it.

### 2. Apply migrations

```bash
alembic upgrade head
```

The command intentionally fails if the bootstrap-control row is absent.

### 3. Run interactively

```bash
userverse-admin bootstrap-superuser \
  --email admin@example.com \
  --reason "Initial production bootstrap"
```

The prompt displays the resolved email and UUID. Confirm only after comparing
both values with the intended account.

When running from the repository without installing the entry point:

```bash
uv run userverse-admin bootstrap-superuser \
  --email admin@example.com \
  --reason "Initial production bootstrap"
```

### 4. Run non-interactively

Automation must supply the exact UUID obtained from a separate, trusted account
lookup:

```bash
userverse-admin bootstrap-superuser \
  --email admin@example.com \
  --reason "Initial production bootstrap" \
  --confirm-user-id 11111111-2222-3333-4444-555555555555
```

An email/UUID mismatch aborts without changing either account. Do not derive the
confirmation UUID from untrusted job input in the same command.

### 5. Sign in again

All sessions belonging to the promoted user are invalidated. The user must sign
in again before accessing global role, permission, or platform administration
APIs.

### 6. Verify the audit record

Confirm that one `privileged_access_event` exists with:

```text
action: superuser_bootstrapped
source: operator_cli
target_user_id: <expected UUID>
previous_superuser: false
resulting_superuser: true
```

The reason is stored, but credentials and tokens are never recorded.

## Idempotency and failure behavior

- Repeating the command for the original user succeeds without creating a
  second event or invalidating sessions again.
- Repeating it for a different user fails.
- If the original user is no longer a superuser, the command fails instead of
  silently restoring access.
- If any superuser predates the control record, bootstrap fails and requires an
  operator investigation.
- The command does not provide a disaster-recovery bypass. Database recovery
  procedures should remain restricted to trusted infrastructure operators.

## Next milestone: superuser administration APIs

The next implementation should add:

```text
POST  /user/reauthenticate
GET   /admin/superusers
PATCH /admin/users/{user_id}/superuser
```

The `PATCH` request should be idempotent:

```json
{
  "enabled": true,
  "reason": "Secondary break-glass administrator"
}
```

Required controls:

1. Load the actor from the database and require an active superuser. Platform
   roles and permissions must not authorize this operation.
2. Require recent password reauthentication through a short-lived,
   single-purpose step-up token. Require MFA once supported.
3. Require the target to be active, verified, and not deleted.
4. Lock the singleton control row for every promotion or demotion.
5. Prevent demotion, suspension, deactivation, or deletion of the final active
   superuser, including through `DELETE /user/me`.
6. Increment the target's refresh-token version after every privilege change.
7. Write the before/after audit event atomically with the user update.
8. Notify the target and security contacts after commit, preferably through a
   transactional outbox.
9. Keep `is_superuser` out of ordinary profile updates and tenant member
   management APIs.

Until that milestone is implemented, the bootstrap CLI cannot and must not be
used to promote a second user. Production environments that require two
break-glass administrators should complete the administration API milestone
before relying on this bootstrap flow for general operations.

## Required follow-up tests

- Promotion and demotion require a current superuser and recent reauthentication.
- Company permissions and direct platform roles cannot grant superuser access.
- Promotion and demotion invalidate all target sessions immediately.
- Concurrent changes cannot remove the final active superuser.
- Self-deletion and suspension respect the final-superuser invariant.
- Every privilege change creates exactly one atomic audit event.
- Failed audit writes roll back privilege changes.
- Audit and application logs contain no passwords or tokens.
