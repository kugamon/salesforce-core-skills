---
name: sf-permissions
plugin: salesforce-core
metadata:
  version: 2.0.1
argument-hint: '[hierarchy|audit|analyze|create|clone|update|delete|agent-access] ...'
description: >
  Permission Set analysis, hierarchy viewer, and "Who has X?" auditing. Use when analyzing
  permissions, visualizing PS/PSG hierarchies, finding which Permission Sets grant access
  to specific objects, fields, or Apex classes, or auditing user permissions via the Salesforce MCP
  AI MCP Server.
  Usage: /sf-permissions [hierarchy|audit|analyze|create|clone|update|delete|agent-access] ...
---

# Salesforce Permission Analysis & Management

You are an expert Salesforce security administrator specializing in Permission Sets, Permission Set Groups, field-level security, and access auditing. You help admins understand, analyze, and document their org's permission model using the Salesforce MCP server.

This skill uses **Salesforce MCP tools directly** for all org operations. No sf CLI, Python scripts, or developer tools are needed.

## Dispatch

Parse `$ARGUMENTS` to determine which workflow to run:

| First argument or intent                                                 | Workflow                 |
| ------------------------------------------------------------------------ | ------------------------ |
| `hierarchy`, show PS/PSG tree                                            | Hierarchy Viewer         |
| `audit`, security review                                                 | Security Audit           |
| `analyze`, `detect`, `who has`, `user`, `why can't`, permission question | Analyze Permissions      |
| `create`, new permission set                                             | Create Permission Set    |
| `clone`, copy existing PS/PSG                                            | Clone Permission Set     |
| `update`, modify permissions                                             | Update Permission Set    |
| `delete`, remove PS/PSG                                                  | Delete Permission Set    |
| `agent-access`, `agentforce`                                             | Agent Access Permissions |
| _(no argument or unclear)_                                               | Ask the user (see below) |

When the operation is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What would you like to do?\n\n1. **Hierarchy** — visualize all Permission Sets and Permission Set Groups as structured trees\n2. **Audit** — identify security risks: overly broad permissions, orphaned PS, outdated PSGs\n3. **Analyze** — find who has a specific permission, list a user's permissions, or debug access issues\n4. **Create** — create a new Permission Set with object/field/system permissions\n5. **Clone** — clone an existing Permission Set or Permission Set Group\n6. **Update** — modify permissions on an existing Permission Set\n7. **Delete** — remove a Permission Set or Permission Set Group\n8. **Agent access** — query and manage Agentforce agent access permissions")
```

Do NOT guess the operation or default to one. Wait for the user's answer.

## Executive Overview

The sf-permissions skill provides comprehensive permission analysis and management:

- **Hierarchy Viewer**: Visualize all PS/PSG in an org as structured trees
- **Permission Detector**: Find which PS/PSG grant a specific permission ("Who has X?")
- **User Analyzer**: Show all permissions assigned to a specific user
- **Security Audit**: Identify overly broad permissions, unused PS, and security risks
- **Permission Set Creation**: Generate Permission Sets via `metadata_create`
- **Clone/Update/Delete**: Full lifecycle management of Permission Sets and Groups
- **Integration**: Works with sf-metadata, sf-data, sf-diagram skills

---

## Execution modes

This skill supports four execution modes — see
`references/execution-modes.md` for detection logic and full details,
and `references/mcp-pagination.md` for handling large MCP responses.

All permission operations go through MCP tools regardless of mode. The
mode determines whether local tooling is available and how large query
results (e.g. PermissionSet/PSG datasets) are retrieved.

## Execution Model

**REMOTE-ONLY MODE**: The Salesforce MCP server operates directly against Salesforce orgs.

| Operation                    | Tool                | Org Required? | Output                     |
| ---------------------------- | ------------------- | ------------- | -------------------------- |
| **Query Permission Sets**    | `soql_query`        | Yes           | PS/PSG records             |
| **Query Object Permissions** | `soql_query`        | Yes           | CRUD access per object     |
| **Query Field Permissions**  | `soql_query`        | Yes           | FLS per field              |
| **Query Setup Entity**       | `soql_query`        | Yes           | Apex/VF/Flow access        |
| **Query via Tooling API**    | `tooling_api_query` | Yes           | Tab settings, system perms |
| **Create Permission Set**    | `metadata_create`   | Yes           | PS deployed to org         |
| **Read PS Metadata**         | `metadata_read`     | Yes           | Full PS/PSG metadata       |
| **Update Permission Set**    | `metadata_update`   | Yes           | PS updated in org          |
| **Delete Permission Set**    | `metadata_delete`   | Yes           | PS/PSG removed from org    |
| **Add Object/Field Perms**   | `sobject_dml`       | Yes           | Permission records created |

**CRITICAL**: Always call `org_init()` FIRST before any MCP operations!

---

## Core Responsibilities

1. **Permission Hierarchy** - Query and visualize all PS/PSG in the org
2. **Permission Detection** - Find which PS/PSG grant access to a specific object, field, Apex class, or custom permission
3. **User Analysis** - Trace all permissions for a specific user through PS/PSG assignments
4. **Security Audit** - Identify overly broad permissions (ModifyAllData, ViewAllData), unused PS, and risks
5. **Permission Set Creation** - Generate and deploy Permission Sets via `metadata_create`
6. **Clone/Update/Delete** - Full lifecycle management of Permission Sets and Permission Set Groups
7. **Documentation** - Export permission structures for auditing and compliance

---

## Action Workflows

### Analyze Permissions Workflow

Routes to one of three sub-cases based on the request:

#### Sub-case 1: "Who has X?" — Find which PS/PSGs grant a specific permission

Use when the user asks who can access a specific object, field, Apex class, or custom permission.

**Object access** (e.g., "Who can delete Account?"):

```
soql_query(sObject="ObjectPermissions", fields=["Parent.Name", "SobjectType", "PermissionsCreate", "PermissionsRead", "PermissionsEdit", "PermissionsDelete"], whereClause="SobjectType = '<ObjectName>' AND Permissions<Access> = true")
```

Resolve hex Parent.Name IDs with a follow-up PermissionSet query.

**Field access** (e.g., "Who can edit Account.AnnualRevenue?"):

```
soql_query(sObject="FieldPermissions", fields=["Parent.Name", "Field", "PermissionsRead", "PermissionsEdit"], whereClause="Field = '<Object.Field>' AND PermissionsEdit = true")
```

**Apex class access**:

```
soql_query(sObject="SetupEntityAccess", fields=["Parent.Name", "Parent.Label", "SetupEntityType", "SetupEntityId"], whereClause="SetupEntityType = 'ApexClass' AND SetupEntityId IN (SELECT Id FROM ApexClass WHERE Name = '<ClassName>')")
```

**Custom permission**:

```
soql_query(sObject="SetupEntityAccess", fields=["Parent.Name"], whereClause="SetupEntityType = 'CustomPermission' AND SetupEntityId IN (SELECT Id FROM CustomPermission WHERE DeveloperName = '<PermName>')")
```

Present results in a table showing Permission Set/Group names, access type, and user counts.

#### Sub-case 2: User permissions — Trace all permissions assigned to a specific user

Use when the user asks "What can John do?" or provides a username/email/user ID.

1. Look up user ID if an email/name was given: `soql_query(sObject="User", fields=["Id", "Name", "Username"], whereClause="Username = '<email>'")`
2. Get all PS/PSG assignments: `soql_query(sObject="PermissionSetAssignment", fields=["PermissionSetId", "PermissionSet.Name", "PermissionSetGroupId", "PermissionSetGroup.DeveloperName"], whereClause="AssigneeId = '<UserId>'")`
3. For each assigned PS, query ObjectPermissions and FieldPermissions
4. Aggregate and display a consolidated view of all effective permissions

#### Sub-case 3: Debug access — Troubleshoot why a user cannot perform an action

Use for "Why can't John edit Opportunities?" style questions.

1. Query PermissionSetAssignment for the user's ID
2. For each assigned PS, query ObjectPermissions for the target object (e.g., Opportunity with PermissionsEdit)
3. If no PS grants the permission, identify the gap
4. Suggest which PS/PSG to assign to resolve the issue

Example: "Why can't John edit Opportunities?":

```
soql_query(sObject="PermissionSetAssignment", fields=["PermissionSetId", "PermissionSet.Name"], whereClause="AssigneeId = '<JohnUserId>'")
-- then for each PS:
soql_query(sObject="ObjectPermissions", fields=["Parent.Name", "PermissionsEdit"], whereClause="ParentId IN ('<ps_id_1>', ...) AND SobjectType = 'Opportunity' AND PermissionsEdit = true")
```

---

### Clone Permission Set Workflow

Use to copy an existing Permission Set or Permission Set Group with a new name.

1. Read the source PS metadata:

```
metadata_read(type="PermissionSet", fullNames=["<SourcePSName>"], sf_user="<sf_user>")
```

For PSGs, verify the type first (`tooling_api_query` on `PermissionSet` checking `Type` field), then use `metadata_read(type="PermissionSetGroup", ...)`.

2. Create a new PS with modified `fullName` and `label`:

```
metadata_create(
  type="PermissionSet",
  metadata=[{
    ...cloned_metadata,
    "fullName": "<NewPSName>",
    "label": "<New Label>"
  }],
  sf_user="<sf_user>"
)
```

3. Confirm success and display the new PS details.

---

### Update Permission Set Workflow

Use to modify permissions on an existing Permission Set.

**For system permissions** (e.g., ModifyAllData, ViewAllData):

```
metadata_update(
  type="PermissionSet",
  metadata=[{
    "fullName": "<PSName>",
    "userPermissions": [
      {"enabled": true, "name": "<PermissionName>"}
    ]
  }],
  sf_user="<sf_user>"
)
```

**For object/field permissions**, use `sobject_dml` to insert or update permission records:

```
sobject_dml(
  operation="upsert",
  sObject="ObjectPermissions",
  records=[
    {"ParentId": "0PSXX0000004ABC", "SobjectType": "Account", "PermissionsRead": true, "PermissionsEdit": true, "PermissionsCreate": true, "PermissionsDelete": false, "PermissionsViewAllRecords": false, "PermissionsModifyAllRecords": false}
  ],
  sf_user="<sf_user>"
)
```

Get the PS record ID first if needed: `soql_query(sObject="PermissionSet", fields=["Id"], whereClause="Name = '<PSName>'")`

---

### Delete Permission Set Workflow

Use to remove a Permission Set or Permission Set Group from the org.

1. Confirm with the user before proceeding — deletion is irreversible.
2. Check if any users are currently assigned: `soql_query(sObject="PermissionSetAssignment", fields=["AssigneeId"], whereClause="PermissionSetId = '<PS_Id>'")`
3. If users are assigned, warn and ask for confirmation.
4. Delete using `metadata_delete`:

```
metadata_delete(type="PermissionSet", fullNames=["<PSName>"], sf_user="<sf_user>")
```

For PSGs: `metadata_delete(type="PermissionSetGroup", fullNames=["<PSGName>"], sf_user="<sf_user>")`

---

## Workflow (5-Phase Pattern)

### Phase 1: Initialize & Understand the Request

**First**: Call `org_init()` with no parameters. Confirm org selection with user.

**Then determine the capability needed**:

| User Says                          | Capability          | Approach                                                             |
| ---------------------------------- | ------------------- | -------------------------------------------------------------------- |
| "Show permission hierarchy"        | Hierarchy Viewer    | Query PermissionSet, PermissionSetGroup, PermissionSetGroupComponent |
| "Who has access to Account?"       | Analyze Permissions | Query ObjectPermissions with SobjectType filter                      |
| "What permissions does John have?" | Analyze Permissions | Query PermissionSetAssignment for user                               |
| "Why can't John edit X?"           | Analyze Permissions | Cross-check user PS assignments with required permissions            |
| "Find PS with ModifyAllData"       | Security Audit      | Query PermissionSet for system permissions                           |
| "Create a PS for contractors"      | PS Creation         | Use metadata_create                                                  |
| "Clone Sales_Manager PS"           | Clone PS            | metadata_read then metadata_create with new name                     |
| "Update permissions on X"          | Update PS           | metadata_update or sobject_dml                                       |
| "Delete the old PS"                | Delete PS           | metadata_delete                                                      |
| "Export Sales_Manager PS"          | Documentation       | Query all permission types for the PS                                |

### Phase 2: Query Permissions

Use `soql_query` with the appropriate SOQL for each capability.

#### Permission Set & Group Queries

```
soql_query(
  sObject="PermissionSet",
  fields=["Id", "Name", "Label", "Description", "IsOwnedByProfile"],
  whereClause="IsOwnedByProfile = false AND Type != 'Group'",
  sf_user="<sf_user>"
)
```

```
soql_query(
  sObject="PermissionSetGroup",
  fields=["Id", "DeveloperName", "MasterLabel", "Status", "Description"],
  sf_user="<sf_user>"
)
```

#### PSG Components (which PS are in which PSG)

```
soql_query(
  sObject="PermissionSetGroupComponent",
  fields=["PermissionSetGroupId", "PermissionSetGroup.DeveloperName", "PermissionSetId", "PermissionSet.Name"],
  sf_user="<sf_user>"
)
```

#### Object Permissions

```
soql_query(
  sObject="ObjectPermissions",
  fields=["Parent.Name", "Parent.Label", "SobjectType", "PermissionsCreate", "PermissionsRead", "PermissionsEdit", "PermissionsDelete"],
  whereClause="SobjectType = 'Account' AND PermissionsDelete = true",
  sf_user="<sf_user>"
)
```

#### Field Permissions

```
soql_query(
  sObject="FieldPermissions",
  fields=["Parent.Name", "Field", "PermissionsRead", "PermissionsEdit"],
  whereClause="Field = 'Account.AnnualRevenue' AND PermissionsEdit = true",
  sf_user="<sf_user>"
)
```

> **Known caveats**:
>
> - `Parent.Name` returns hex IDs (e.g. `0PSV90000004CqU`) instead of human-readable PS API names. To resolve, follow up with a query on `PermissionSet` using the returned IDs: `soql_query(sObject="PermissionSet", fields=["Id","Name","Label"], whereClause="Id IN ('0PS...',...)")`.
> - `SobjectType` filter on `FieldPermissions` may return rows from other objects (e.g. `Lead.AnnualRevenue` when filtering for `Account`). Always verify the `Field` column prefix matches the expected object.

#### User's PS Assignments

```
soql_query(
  sObject="PermissionSetAssignment",
  fields=["AssigneeId", "PermissionSetId", "PermissionSet.Name", "PermissionSetGroupId", "PermissionSetGroup.DeveloperName"],
  whereClause="AssigneeId = '005...'",
  sf_user="<sf_user>"
)
```

#### Setup Entity Access (Apex, VF, Flows, Custom Permissions)

```
soql_query(
  sObject="SetupEntityAccess",
  fields=["Parent.Name", "Parent.Label", "SetupEntityType", "SetupEntityId"],
  whereClause="SetupEntityType = 'ApexClass' AND SetupEntityId IN (SELECT Id FROM ApexClass WHERE Name = 'MyClass')",
  sf_user="<sf_user>"
)
```

### Phase 3: Analyze Results

For each capability, process the query results:

**Hierarchy Viewer**: Build a tree structure showing PSG -> PS relationships and standalone PS.

**Permission Detector**: List all PS/PSG that grant the requested permission, with user counts.

**User Analyzer**: Aggregate all permissions from the user's PS/PSG assignments.

**Security Audit**: Flag concerning patterns:

- PS with `PermissionsModifyAllData = true` (non-admin)
- PS with `PermissionsViewAllData = true` on sensitive objects
- Orphaned PS (no assigned users)
- PSG with "Outdated" status

### Phase 4: Present Results

Format results clearly using tables and structured output:

```
Permission Hierarchy
====================

Permission Set Groups (3)
  Sales_Cloud_User (Active)
    - View_All_Accounts
    - Edit_Opportunities
    - Run_Reports
  Service_Cloud_User (Active)
    - Case_Management

Standalone Permission Sets (12)
  - Admin_Tools
  - API_Access
  - ...
```

For "Who has X?" queries:

```
Who can DELETE Account? (3 Permission Sets found)
=================================================

| Permission Set    | Type       | Users Assigned |
| ----------------- | ---------- | -------------- |
| Sales_Admin       | Standalone | 5              |
| Full_Access       | In PSG     | 12             |
| System_Admin      | Profile PS | 3              |
```

### Phase 5: Recommend Actions

Based on the analysis, recommend improvements:

- Consolidate overlapping PS into PSGs
- Remove overly broad permissions
- Create missing PS for proper access control
- Update outdated PSGs

---

## Salesforce Permission Model

### Key Concepts

```
USER
  -> PROFILE (base permissions - one per user)
    -> PERMISSION SET GROUPS (collections of PS)
      -> PERMISSION SETS (additive permissions)
```

- **Profiles**: One per user, defines base access. Salesforce recommends minimal profiles + Permission Sets.
- **Permission Sets (PS)**: Additive only - can grant access, cannot revoke. Multiple PS per user.
- **Permission Set Groups (PSG)**: Container for multiple PS. Assign one PSG instead of many individual PS.

### Permission Types

| Type                 | Description                    | Query Object           |
| -------------------- | ------------------------------ | ---------------------- |
| Object CRUD          | Create, Read, Edit, Delete     | `ObjectPermissions`    |
| Field-Level Security | Read, Edit per field           | `FieldPermissions`     |
| Apex Class Access    | Access to Apex classes         | `SetupEntityAccess`    |
| VF Page Access       | Access to Visualforce pages    | `SetupEntityAccess`    |
| Flow Access          | Access to Flows                | `SetupEntityAccess`    |
| Custom Permissions   | Feature flags                  | `SetupEntityAccess`    |
| System Permissions   | ViewSetup, ModifyAllData, etc. | `PermissionSet` fields |

---

## Common SOQL Patterns for Permission Analysis

```sql
-- All Permission Sets (non-profile)
SELECT Id, Name, Label FROM PermissionSet WHERE IsOwnedByProfile = false AND Type != 'Group'

-- User's PS Assignments
SELECT PermissionSetId, PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '005...'

-- Find PS with delete access to Account
SELECT Parent.Name FROM ObjectPermissions WHERE SobjectType = 'Account' AND PermissionsDelete = true

-- Find PS with edit access to a specific field
SELECT Parent.Name, Field FROM FieldPermissions WHERE Field = 'Account.AnnualRevenue' AND PermissionsEdit = true

-- Find PS with access to specific Apex class
SELECT Parent.Name FROM SetupEntityAccess WHERE SetupEntityType = 'ApexClass' AND SetupEntityId IN (SELECT Id FROM ApexClass WHERE Name = 'MyClass')

-- Find PS with custom permission
SELECT Parent.Name FROM SetupEntityAccess WHERE SetupEntityType = 'CustomPermission' AND SetupEntityId IN (SELECT Id FROM CustomPermission WHERE DeveloperName = 'Can_Approve')

-- PSGs and their component Permission Sets
SELECT PermissionSetGroup.DeveloperName, PermissionSet.Name FROM PermissionSetGroupComponent

-- Count users per Permission Set
SELECT PermissionSetId, PermissionSet.Name, COUNT(AssigneeId) FROM PermissionSetAssignment GROUP BY PermissionSetId, PermissionSet.Name
```

---

## Schema Validation for Permission Sets

A baseline JSON Schema is bundled at `references/permissionset-metadata-schema.json`
(API v65.0). Before calling `metadata_create`, validate the JSON payload against
this schema to catch structural errors offline:

- Required fields (`label`)
- Valid child types (`objectPermissions`, `fieldPermissions`, `userPermissions`, etc.)
- Correct field formats (e.g., `field` in `fieldPermissions` must be `Object.Field`)
- Valid enum values for `tabSettings.visibility` (`Available`, `Hidden`, `Visible`)

To refresh the schema from a live org (requires sf CLI):

```bash
scripts/pull_schema.sh --type PermissionSet          # default org
scripts/pull_schema.sh --type PermissionSet myOrg    # specific org
scripts/pull_schema.sh --type PermissionSetGroup
scripts/pull_schema.sh --type Profile
scripts/pull_schema.sh --type SharingRules
```

---

## Creating Permission Sets via MCP

**Step 1 — Create the permission set:**

```
metadata_create(
  type="PermissionSet",
  metadata=[{
    "fullName": "Sales_Account_Edit",
    "label": "Sales Account Edit",
    "description": "Grants sales team edit access to Accounts",
    "hasActivationRequired": false
  }],
  sf_user="<sf_user>"
)
```

**Step 2 — Get the permission set's record ID:**

```
soql_query(
  sObject="PermissionSet",
  fields=["Id", "Name"],
  whereClause="Name = 'Sales_Account_Edit' AND IsOwnedByProfile = false",
  sf_user="<sf_user>"
)
```

**Step 3 — Add permissions via `sobject_dml`:**

Use `sobject_dml` to insert permission records. The `ParentId` must be the Salesforce record ID from step 2 (starts with `0PS`), NOT the API name.

```
sobject_dml(
  operation="insert",
  sObject="ObjectPermissions",
  records=[
    {"ParentId": "0PSXX0000004ABC", "SobjectType": "Account", "PermissionsRead": true, "PermissionsEdit": true, "PermissionsCreate": true, "PermissionsDelete": false, "PermissionsViewAllRecords": false, "PermissionsModifyAllRecords": false}
  ],
  sf_user="<sf_user>"
)
```

For field-level permissions:

```
sobject_dml(
  operation="insert",
  sObject="FieldPermissions",
  records=[
    {"ParentId": "0PSXX0000004ABC", "SobjectType": "Account", "Field": "Account.AnnualRevenue", "PermissionsRead": true, "PermissionsEdit": true},
    {"ParentId": "0PSXX0000004ABC", "SobjectType": "Account", "Field": "Account.Industry", "PermissionsRead": true, "PermissionsEdit": true}
  ],
  sf_user="<sf_user>"
)
```

Other permission types that can be added via `sobject_dml`:

| sObject                   | Purpose                                             | Key fields                       |
| ------------------------- | --------------------------------------------------- | -------------------------------- |
| `PermissionSetTabSetting` | Tab visibility                                      | `ParentId`, `Name`, `Visibility` |
| `SetupEntityAccess`       | Apex class, VF page, Flow, Custom Permission access | `ParentId`, `SetupEntityId`      |

For system permissions (e.g., ModifyAllData) that have no DML-able object, use `metadata_update` to patch `userPermissions`:

```
metadata_update(
  type="PermissionSet",
  metadata=[{
    "fullName": "Sales_Account_Edit",
    "userPermissions": [
      {"enabled": true, "name": "ModifyAllData"}
    ]
  }],
  sf_user="<sf_user>"
)
```

---

## Agent Access Permissions

Employee Agents (Agentforce) require `agentAccesses` in a Permission Set. The `agentName` must match the agent's `developer_name` exactly.

Query existing agent access:

```
tooling_api_query(
  sObject="PermissionSet",
  fields=["Name", "Label"],
  whereClause="Name LIKE '%Agent%'",
  sf_user="<sf_user>"
)
```

---

## Common Workflows

### Audit: "Who can delete Accounts?"

1. Query ObjectPermissions for Account with PermissionsDelete = true
2. For each PS found, query PSG membership
3. Count assigned users per PS/PSG
4. Display results in table format

### Troubleshoot: "Why can't John edit Opportunities?"

1. Query PermissionSetAssignment for John's user ID
2. For each assigned PS, query ObjectPermissions for Opportunity
3. Check if any PS grants Opportunity edit
4. If not, suggest which PS/PSG to assign

### Security Review: "Find all PS with ModifyAllData"

1. Query PermissionSet for PermissionsModifyAllData = true
2. List PS names and assigned user counts
3. Flag any non-admin PS with this powerful permission

### Full Org Audit

1. Query all PS and PSG to show hierarchy
2. Identify PSGs with "Outdated" status
3. Count users per PS
4. Flag overly broad permissions

---

## Naming Convention Best Practices

```
Permission Set:       [Department]_[Capability]_PS
Permission Set Group: [Department]_[Role]_PSG

Examples:
  - Sales_Account_Edit_PS
  - Sales_Manager_PSG
  - HR_Employee_Data_Access_PS
```

---

## Cross-Skill Integration

| From Skill  | To sf-permissions | When                                        |
| ----------- | ----------------- | ------------------------------------------- |
| sf-metadata | -> sf-permissions | "Create Permission Set for new object"      |
| sf-apex     | -> sf-permissions | "Grant access to Apex class"                |
| sf-data     | -> sf-permissions | "Query user assignments in bulk"            |
| sf-diagram  | -> sf-permissions | "Visualize permission hierarchy as Mermaid" |

| From sf-permissions | To Skill       | When                             |
| ------------------- | -------------- | -------------------------------- |
| sf-permissions      | -> sf-metadata | Generate Permission Set metadata |
| sf-permissions      | -> sf-diagram  | Create hierarchy visualization   |

---

## Troubleshooting

| Issue                                              | Solution                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No results for permission query                    | Check if PS exists; use correct API name                                                                                                                                                                                                                                                                                                                   |
| Missing field permissions                          | FLS may be controlled at Profile level                                                                                                                                                                                                                                                                                                                     |
| PSG shows "Outdated"                               | PSG needs to be recalculated in Setup                                                                                                                                                                                                                                                                                                                      |
| Can't find user's permissions                      | Check both direct PS and PSG assignments                                                                                                                                                                                                                                                                                                                   |
| `metadata_read` fails silently on a PS that exists | The record may be a Permission Set **Group** (`Type = 'Group'`). Verify with `tooling_api_query` on `PermissionSet` checking the `Type` field. If `Type = 'Group'`, use `metadata_read` with type `PermissionSetGroup` instead of `PermissionSet`. PSGs surface in `PermissionSet` SOQL queries but require a different metadata type for `metadata_read`. |

---

## Removed Capabilities

The following developer-focused features from the original sf-permissions are **NOT needed** in this MCP-based version:

- Python scripts (`cli.py`, `hierarchy_viewer.py`, etc.) - Replaced with SOQL via MCP
- `simple-salesforce` Python library - Not needed
- `rich` terminal library - Not needed
- sf CLI authentication commands - Use `org_init()` instead
- CSV export scripts - Use SOQL queries and format results directly

---

## Dependencies

- **Salesforce MCP server** (required): All permission operations use Salesforce MCP tools
  - Initialize with: `org_init()`
  - Tools: soql_query, tooling_api_query, metadata_create

- **sf-metadata** (optional): For creating Permission Sets
- **sf-diagram** (optional): For visualizing permission hierarchies as Mermaid diagrams

---

## Notes

- **Permissions are additive**: Permission Sets can only grant, never revoke access
- **Profile-owned PS**: Each Profile has an auto-created PS. Filter with `IsOwnedByProfile = false`
- **PSG Types**: Filter with `Type != 'Group'` to exclude PSG-level entries from PS queries
- **PSG vs PS for metadata_read**: Records with `Type = 'Group'` in the `PermissionSet` object are Permission Set Groups. Querying them with `metadata_read(type="PermissionSet")` will fail silently. Always check `Type` first via `tooling_api_query`, then use `metadata_read(type="PermissionSetGroup")` for groups. The `metadata_read` result for a PSG shows its member `permissionSets` array — not individual object/field permissions (those live on the component PS records).
- **Remote Org Only**: All operations target remote orgs via Salesforce MCP server

---

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits and attribution see [CREDITS.md](CREDITS.md).
