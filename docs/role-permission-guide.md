# Global and Company RBAC Guide

Userverse uses a hybrid role-based access control model. Roles come from one
global catalog, while their permissions can come from two scopes:

- **Global permissions** are application-wide baseline permissions attached to
  a global role.
- **Company permissions** belong to one company and add capabilities to a role
  only in that company.
- **Platform role assignments** attach global roles directly to users and grant
  only the roles' global permissions.

A platform role never creates company membership and never authorizes access to
company data by itself.

## Mental model

For a role `r`, company `c`, and user `u`:

```text
global role view(r)       = global permissions on r
company role view(c, r)   = global permissions on r
                            + company c permissions attached to r
platform permissions(u)   = global permissions from roles assigned directly to u
```

Company permissions are additive. A company cannot remove, replace, or deny a
global permission inherited from a role. Tenant overrides and deny rules are not
part of this implementation.

For example:

```text
Manager global baseline: app.dashboard.view
Company A addition:      invoice.approve
Company B addition:      report.publish

Manager in company A -> app.dashboard.view + invoice.approve
Manager in company B -> app.dashboard.view + report.publish
Platform Manager      -> app.dashboard.view only
```

## Records and identity

| Record | Scope | Purpose |
| --- | --- | --- |
| `role` | Global | Reusable role catalog, such as `Manager` |
| `global_permission` | Global | Application capability, such as `app.dashboard.view` |
| `role_global_permission` | Global | Adds a mandatory baseline permission to a role |
| `company_role` | Company | Makes a global role available in one company |
| `company_permission` | Company | Tenant-owned capability, such as `invoice.approve` |
| `company_role_permission` | Company | Adds a tenant permission to an enabled company role |
| `association_user_company` | Company | Gives a member one role in a company |
| `user_role` | Platform | Assigns a global role directly to a user |

Permission names are trimmed and stored verbatim. Global names are unique
globally; company names are unique inside their company. A global permission and
a company permission may have the same name, but they are different permissions.
Use the permission UUID together with `scope` and `company_id` as its identity.

Permission responses use this shape:

```json
{
  "id": "3a6f7287-9aa5-4f89-a61e-0ad7ae1f8210",
  "name": "invoice.approve",
  "description": "Approve an invoice",
  "scope": "company",
  "company_id": "caefbf3a-0663-4997-919f-cd3b2f067d28"
}
```

For a global permission, `scope` is `global` and `company_id` is `null`.

## Authentication and management rights

All endpoints require a bearer access token.

| Operation | Required actor |
| --- | --- |
| Create, update, or delete global roles | Superuser |
| Create, update, or delete global permissions | Superuser |
| Attach or remove global permissions from roles | Superuser |
| Assign or remove direct platform roles | Superuser |
| Manage a company's permissions | Company Owner, Administrator, or superuser |
| Attach or remove company permissions from roles | Company Owner, Administrator, or superuser |
| Enable or disable an existing role for a company | Company Owner or Administrator |
| Read the current user's platform permissions | Authenticated user |

The `is_superuser` flag remains the bootstrap administration mechanism. It does
not create an implicit role or permission assignment.

The examples below assume:

```bash
BASE_URL=http://127.0.0.1:8500/userverse
SUPERUSER_TOKEN=replace-with-superuser-access-token
COMPANY_ADMIN_TOKEN=replace-with-owner-or-administrator-access-token
USER_TOKEN=replace-with-user-access-token
COMPANY_ID=replace-with-company-uuid
USER_ID=replace-with-user-uuid
```

## Global role and permission workflow

### 1. Create a global role

```bash
curl -X POST "$BASE_URL/roles" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Manager",
    "description": "Application manager"
  }'
```

Save `data.id` from the response as `ROLE_ID`.

### 2. Create a global application permission

```bash
curl -X POST "$BASE_URL/permissions" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "app.dashboard.view",
    "description": "View the application dashboard"
  }'
```

Save `data.id` as `GLOBAL_PERMISSION_ID`.

### 3. Attach the global permission to the role

```bash
curl -X POST \
  "$BASE_URL/roles/$ROLE_ID/permissions/$GLOBAL_PERMISSION_ID" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"
```

Every use of this role now inherits the permission. Companies cannot remove it
from their local view of the role.

### 4. Inspect global permissions on a role

```bash
curl "$BASE_URL/roles/$ROLE_ID/permissions" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"
```

`GET /roles` also returns each role with structured global permission objects in
its `permissions` list. It does not include any company's additions.

### 5. Update, detach, or delete

```bash
# Rename or change the description
curl -X PATCH "$BASE_URL/permissions/$GLOBAL_PERMISSION_ID" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"View the main application dashboard"}'

# Remove the permission from this role only
curl -X DELETE \
  "$BASE_URL/roles/$ROLE_ID/permissions/$GLOBAL_PERMISSION_ID" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"

# Hard-delete the permission and all of its role links
curl -X DELETE "$BASE_URL/permissions/$GLOBAL_PERMISSION_ID" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"
```

Deleting a permission never deletes or modifies the role itself.

## Company role and permission workflow

Company permissions can be attached only to roles enabled for the same company.
Composite database foreign keys enforce this tenant boundary.

### 1. Enable an existing global role for the company

```bash
curl -X POST "$BASE_URL/company/$COMPANY_ID/roles/$ROLE_ID" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"
```

The returned role initially contains its global baseline permissions.

### 2. Create a company permission

```bash
curl -X POST "$BASE_URL/company/$COMPANY_ID/permissions" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "invoice.approve",
    "description": "Approve invoices in this company"
  }'
```

Save `data.id` as `COMPANY_PERMISSION_ID`.

### 3. Attach the company permission to the enabled role

```bash
curl -X POST \
  "$BASE_URL/company/$COMPANY_ID/roles/$ROLE_ID/permissions/$COMPANY_PERMISSION_ID" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"
```

The returned `permissions` list is the effective company view: the role's global
baseline plus this company's additions.

### 4. Inspect company permissions and effective role permissions

```bash
# Permissions defined by the company
curl "$BASE_URL/company/$COMPANY_ID/permissions?limit=10&page=1" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"

# Global baseline plus this company's additions
curl "$BASE_URL/company/$COMPANY_ID/roles/$ROLE_ID/permissions" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"

# All enabled roles, each with effective permissions
curl "$BASE_URL/company/$COMPANY_ID/roles?limit=10&page=1" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"
```

### 5. Assign the role to a company member

Company membership remains single-role. The `role` field is the global role
name and that role must already be enabled for the company.

```bash
curl -X POST "$BASE_URL/company/$COMPANY_ID/users" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manager@example.com",
    "role": "Manager"
  }'
```

Company-user and current-user company responses include the role's structured,
effective permission list.

### 6. Remove or delete company permissions

```bash
# Remove the link from one company role
curl -X DELETE \
  "$BASE_URL/company/$COMPANY_ID/roles/$ROLE_ID/permissions/$COMPANY_PERMISSION_ID" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"

# Hard-delete the permission and all role links in this company
curl -X DELETE \
  "$BASE_URL/company/$COMPANY_ID/permissions/$COMPANY_PERMISSION_ID" \
  -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN"
```

Unassigning a role from a company also removes that company's permission links
for the role. It does not remove the role from the global catalog or affect
another company.

## Direct platform roles

Direct platform assignments are useful for application-level access that is not
tied to a company. A user may hold multiple direct roles.

```bash
# Assign a direct role
curl -X POST "$BASE_URL/users/$USER_ID/roles/$ROLE_ID" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"

# List direct roles and their global permissions
curl "$BASE_URL/users/$USER_ID/roles" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"

# Remove only the direct assignment
curl -X DELETE "$BASE_URL/users/$USER_ID/roles/$ROLE_ID" \
  -H "Authorization: Bearer $SUPERUSER_TOKEN"
```

The authenticated user can inspect the deduplicated union of global permissions
from their direct platform roles:

```bash
curl "$BASE_URL/user/permissions" \
  -H "Authorization: Bearer $USER_TOKEN"
```

Company permissions never appear in this response. A direct `Manager` role does
not make the user a member of any company and cannot be used to read or mutate
tenant resources.

## Listing and filtering permissions

Global and company permission lists are paginated and support partial `name` and
`description` filters:

```text
GET /permissions?name=dashboard&description=view&limit=20&page=1
GET /company/{company_id}/permissions?name=invoice&limit=20&page=1
```

The response has this shape:

```json
{
  "message": "Permissions retrieved successfully.",
  "data": {
    "records": [],
    "pagination": {
      "total_records": 0,
      "limit": 20,
      "current_page": 1,
      "total_pages": 0
    }
  }
}
```

## Failure behavior

| Status | Meaning |
| --- | --- |
| `403` | The authenticated actor cannot manage the requested scope |
| `404` | The permission, role, company, assignment, or scoped resource does not exist |
| `409` | A permission name or assignment already exists in that scope |
| `422` | The request is invalid, such as a blank name or empty update |

Cross-company permission identifiers deliberately behave as missing resources
and return `404`.

## Lifecycle and safety rules

- Permission deletion is physical, so its name can be reused immediately.
- Removing a permission deletes its role links but leaves roles unchanged.
- Removing a platform role deletes only the `user_role` link.
- A global role cannot be deleted while used by an active company membership or
  a platform user.
- Inactive or deleted users cannot receive new platform role assignments.
- Changing a global role permission propagates immediately to every company and
  platform user using that role.
- Company additions are isolated: changes in company A do not change company B.
- Permission introspection exposes effective permissions but does not yet
  replace existing route authorization with permission-key checks.
