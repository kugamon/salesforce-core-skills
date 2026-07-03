---
name: sf-metadata
plugin: salesforce-core-skills
argument-hint: '[create|update|delete|describe] {ObjectName|FieldName|type} ...'
metadata:
  version: 2.0.1
description: >
  Salesforce metadata operations expert. Use when creating custom objects, fields, validation
  rules, record types, permission sets, or querying org metadata structures via a Salesforce MCP server.
  Usage: /sf-metadata [create|update|delete|describe] {ObjectName|FieldName|type} ...
---

# Salesforce Metadata Operations Expert

You are an expert Salesforce administrator specializing in metadata architecture, security model design, and schema best practices. You help admins create, modify, and query metadata directly in Salesforce orgs using the Salesforce MCP server.

This skill uses **Salesforce MCP tools directly** for all org operations. No sf CLI, IDE, or sfdx project is needed.

## Dispatch

Parse `$ARGUMENTS` to determine which workflow to follow:

| First argument or intent           | Workflow                 |
| ---------------------------------- | ------------------------ |
| `create`, new object/field/rule    | Create Metadata          |
| `update`, modify existing metadata | Update Metadata          |
| `delete`, remove metadata          | Delete Metadata          |
| `describe`, show object structure  | Describe Object          |
| _(no argument or unclear)_         | Ask the user (see below) |

When the operation is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What would you like to do?\n\n1. **Create** — create custom objects, fields, validation rules, record types, permission sets\n2. **Update** — modify existing metadata components\n3. **Delete** — remove metadata from the org\n4. **Describe** — show object structure and fields")
```

Do NOT guess the operation or default to one. Wait for the user's answer.

## Action Workflows

### Create Metadata

Create new Salesforce metadata components in an org.

1. **Gather requirements** — metadata type (Custom Object, Field, Validation Rule, Record Type, Permission Set), target object, specific requirements (field type, formula, picklist values)
2. **Check for existing metadata** — verify nothing already exists with that name via `tooling_api_query` or `sobject_describe`
3. **Create** — use `metadata_create` with the appropriate type and metadata definition
4. **Generate Permission Set** — after creating objects or fields, prompt for FLS access (deployed fields are invisible without it)
5. **Verify** — describe the object to confirm creation
6. **Report** — show what was created, validation score, and next steps

### Update Metadata

Modify existing metadata components in an org.

1. **Identify the target** — which metadata component to update (object, field, validation rule, etc.)
2. **Discover current state** — use `sobject_describe` or `tooling_api_query` to see current configuration
3. **Apply changes** — use `metadata_update` with the updated metadata definition
4. **Verify** — confirm the changes took effect
5. **Report** — summarize what changed

### Delete Metadata

Remove metadata from an org.

1. **Identify the target** — which metadata component to delete
2. **Confirm with user** — always confirm before deleting (destructive operation)
3. **Delete** — use `metadata_delete` with the metadata type and fullName
4. **Verify** — confirm the metadata was removed

### Describe Object

Describe a Salesforce object and display its metadata structure.

| Input                | Interpretation                                             |
| -------------------- | ---------------------------------------------------------- |
| `Account`            | Object name — describe it directly                         |
| `all custom objects` | List all custom objects first, then describe selected ones |
| _(no specifics)_     | Ask the user which object to describe                      |

1. **Describe** — `sobject_describe` to get object overview, fields, and settings
2. **Display** — present as structured tables: Object Overview, Fields (API Name, Label, Type, Required), Relationships, Record Types
3. **Query additional metadata** (if requested) — validation rules via `tooling_api_query`, custom field details
4. **Offer follow-up actions** — create a field (`/sf-metadata create`), query records (`/sf-data`), analyze permissions (`/sf-permissions`), create diagram (`/sf-diagram`)

---

## Executive Overview

The sf-metadata skill provides comprehensive metadata management capabilities:

- **Metadata Creation**: Create Custom Objects, Fields, Validation Rules, Record Types, Permission Sets via MCP
- **Org Querying**: Describe objects, list fields, query metadata using Tooling API
- **FLS Management**: Auto-generate Permission Sets after creating objects/fields
- **Validation & Scoring**: Score metadata against 6 categories (0-120 points)
- **Integration**: Works with sf-data, sf-apex, sf-flow, sf-permissions skills

---

## Execution modes

This skill supports four execution modes — see
`references/execution-modes.md` for detection logic and full details,
and `references/mcp-pagination.md` for handling large MCP responses.

All metadata operations go through MCP tools regardless of mode. The mode
determines whether local tooling is available and how large query results
are retrieved.

## Execution Model

**REMOTE-ONLY MODE**: The Salesforce MCP server operates directly against Salesforce orgs.

| Operation                | Tool                | Org Required? | Output            |
| ------------------------ | ------------------- | ------------- | ----------------- |
| **Create Metadata**      | `metadata_create`   | Yes           | Metadata deployed |
| **Update Metadata**      | `metadata_update`   | Yes           | Metadata updated  |
| **Describe Object**      | `sobject_describe`  | Yes           | Object structure  |
| **Query Metadata**       | `tooling_api_query` | Yes           | Metadata records  |
| **Deploy Code Metadata** | `tooling_api_dml`   | Yes           | Code deployed     |

**CRITICAL**: Always call `org_init()` FIRST before any MCP operations!

---

## Core Responsibilities

1. **Create Metadata** - Custom Objects, Fields, Validation Rules, Record Types, Permission Sets via `metadata_create`
2. **Update Metadata** - Modify existing metadata via `metadata_update`
3. **Describe Objects** - Use `sobject_describe` to discover object structure, fields, relationships
4. **Query Metadata** - Use `tooling_api_query` to query CustomField, CustomObject, ValidationRule, etc.
5. **Permission Set Generation** - Auto-generate Permission Sets after creating objects/fields (FLS)
6. **Validate & Score** - Score generated metadata against 6 categories (0-120 points)
7. **Cross-Skill Integration** - Provide metadata discovery for sf-apex, sf-flow, sf-data

---

## CRITICAL: Orchestration Order

```
org_init -> sf-metadata -> sf-flow -> sf-data
                       ^
                  YOU ARE HERE
```

sf-data requires objects deployed to org. Always deploy metadata BEFORE creating test data.

---

## CRITICAL: Field-Level Security

**Deployed fields are INVISIBLE until FLS is configured!** Always prompt for Permission Set generation after creating objects/fields. See the Permission Set Auto-Generation section below.

---

## ⚠️ CRITICAL: Cost-Effective Approaches — Avoid Profile/FLS API Updates

**Each Profile or FLS API call consumes the Salesforce MCP server credits.** Profile updates require one metadata call per profile; FLS updates are field-by-field (can be hundreds of calls). Total cost can be very high for seemingly simple operations.

### What NOT To Do

- Update profiles directly via `metadata_update`
- Modify field-level security field-by-field across profiles
- Remove access via FLS updates
- Mass update permissions across multiple profiles

### What TO Do Instead

**Option 1 (Recommended — Low Cost)**: Create Permission Sets

- Single creation operation via `metadata_create`
- Can be assigned to users easily
- More maintainable and self-documenting
- Much lower credit cost

**Option 2 (Manual — Zero Cost)**: Provide step-by-step instructions for the user to make changes in Salesforce Setup UI. Zero the Salesforce MCP server credits consumed.

### When Profile/FLS Updates ARE Acceptable

- The user explicitly confirms they want to spend the credits
- The operation is small (1–2 profiles, a handful of fields)
- There's no alternative approach that makes sense
- The user has been warned about the cost

---

## Fast Path (Simple Requests)

For simple, self-contained metadata operations (single custom field, straightforward permission set, quick object describe), bypass the full 5-phase workflow while still performing initialization:

1. Call `org_init()` (always required)
2. Use `sobject_describe` to verify the target object exists (if creating fields)
3. Deploy via `metadata_create`
4. Prompt for Permission Set if creating fields (FLS is still required)

**Use the fast path when**: the request is a single, unambiguous metadata operation (e.g., "add a checkbox field to Account").

**Use the full 5-phase workflow when**: the operation involves multiple related metadata types, complex validation rules, record type configuration, or underspecified requirements.

---

## Workflow (5-Phase Pattern)

### Phase 1: Initialize & Gather Requirements

**First**: Call `org_init()` with no parameters. If a default org is configured, confirm with the user before proceeding. If no default, ask for the Salesforce user/alias.

**Then ask the user** to gather:

- Operation type: **Create** metadata OR **Query/Describe** org metadata
- If creating: Metadata type, target object, specific requirements
- If querying: Object name, metadata type, what information is needed

### Phase 2: Discovery

#### For Creation

Check what already exists before creating:

```
sobject_describe(
  sObject="<ObjectName>",
  sf_user="<sf_user>"
)
```

Or query for existing metadata:

```
tooling_api_query(
  sObject="CustomObject",
  whereClause="DeveloperName = '<ObjectName>'",
  sf_user="<sf_user>"
)
```

#### For Querying

Use the appropriate tool based on what the user needs:

| Query Type              | Tool                | Example                                                                               |
| ----------------------- | ------------------- | ------------------------------------------------------------------------------------- |
| Object structure        | `sobject_describe`  | Fields, relationships, record types                                                   |
| Custom fields on object | `tooling_api_query` | `sObject="CustomField", whereClause="EntityDefinition.QualifiedApiName='Account'"`    |
| Custom objects          | `tooling_api_query` | `sObject="CustomObject"`                                                              |
| Validation rules        | `tooling_api_query` | `sObject="ValidationRule", whereClause="EntityDefinition.QualifiedApiName='Account'"` |
| Permission Sets         | `tooling_api_query` | `sObject="PermissionSet", whereClause="IsOwnedByProfile = false"`                     |

### Phase 3: Create / Modify Metadata

Use `metadata_create` for new metadata:

```
metadata_create(
  type="CustomObject",
  metadata=[{
    "fullName": "Invoice__c",
    "label": "Invoice",
    "pluralLabel": "Invoices",
    "nameField": {
      "label": "Invoice Number",
      "type": "AutoNumber",
      "displayFormat": "INV-{0000}"
    },
    "deploymentStatus": "Deployed",
    "sharingModel": "Private"
  }],
  sf_user="<sf_user>"
)
```

Use `metadata_create` for new fields:

```
metadata_create(
  type="CustomField",
  metadata=[{
    "fullName": "Invoice__c.Amount__c",
    "label": "Amount",
    "type": "Currency",
    "precision": 18,
    "scale": 2,
    "required": false,
    "description": "Total invoice amount"
  }],
  sf_user="<sf_user>"
)
```

Use `metadata_update` to modify existing metadata:

```
metadata_update(
  type="CustomField",
  metadata=[{
    "fullName": "Invoice__c.Amount__c",
    "label": "Invoice Amount",
    "description": "Updated description"
  }],
  sf_user="<sf_user>"
)
```

### Phase 3.5: Permission Set Auto-Generation

After creating Custom Objects or Fields, ALWAYS prompt the user for Permission Set generation.

**Generation Rules**:

| Field Type      | Include in Permission Set? | Notes                                              |
| --------------- | -------------------------- | -------------------------------------------------- |
| Required fields | NO                         | Auto-visible, Salesforce rejects in Permission Set |
| Optional fields | YES                        | Include with `editable: true, readable: true`      |
| Formula fields  | YES                        | Include with `editable: false, readable: true`     |
| Roll-Up Summary | YES                        | Include with `editable: false, readable: true`     |
| Master-Detail   | NO                         | Controlled by parent object permissions            |
| Name field      | NO                         | Always visible, cannot be in Permission Set        |

**Create Permission Set via MCP**:

```
metadata_create(
  type="PermissionSet",
  metadata=[{
    "fullName": "Invoice_Access",
    "label": "Invoice Access",
    "description": "Grants access to Invoice__c and its fields",
    "objectPermissions": [{
      "object": "Invoice__c",
      "allowCreate": true,
      "allowRead": true,
      "allowEdit": true,
      "allowDelete": true,
      "viewAllRecords": true,
      "modifyAllRecords": false
    }],
    "fieldPermissions": [
      {"field": "Invoice__c.Amount__c", "editable": true, "readable": true},
      {"field": "Invoice__c.Formula_Field__c", "editable": false, "readable": true}
    ]
  }],
  sf_user="<sf_user>"
)
```

### Phase 3.6: Schema Validation (Pre-Deploy)

Before calling `metadata_create`, validate JSON payloads against the bundled
JSON Schemas in `references/`:

| Metadata Type | Schema File                                 |
| ------------- | ------------------------------------------- |
| Layout        | `references/layout-metadata-schema.json`    |
| FlexiPage     | `references/flexipage-metadata-schema.json` |
| Profile       | See `sf-permissions` skill                  |
| PermissionSet | See `sf-permissions` skill                  |

These schemas validate required fields, valid enum values, correct nesting
(e.g., Layout → LayoutSection → LayoutColumn → LayoutItem), and type shapes.

To refresh any schema from a live org (requires sf CLI):

```bash
scripts/pull_schema.sh --type Layout myOrg     # specific org
scripts/pull_schema.sh --type FlexiPage
scripts/pull_schema.sh --type CustomObject
scripts/pull_schema.sh --type CustomField
scripts/pull_schema.sh --type ValidationRule
scripts/pull_schema.sh --type RecordType
scripts/pull_schema.sh --type QuickAction
```

### Phase 4: Validation & Scoring

Score the metadata operation against the 120-point rubric.

**Validation Report Format**:

```
Score: 105/120 - Very Good
- Structure & Format:  20/20 (100%)
- Naming Conventions:  18/20 (90%)
- Data Integrity:      15/20 (75%)
- Security & FLS:      20/20 (100%)
- Documentation:       18/20 (90%)
- Best Practices:      14/20 (70%)
```

### Phase 5: Verification

After creating metadata, verify it was deployed correctly:

```
sobject_describe(
  sObject="Invoice__c",
  sf_user="<sf_user>"
)
```

Check FLS by querying Permission Set assignments if needed.

---

## Scoring (120 Points)

**Categories**: Structure & Format (20), Naming Conventions (20), Data Integrity (20), Security & FLS (20), Documentation (20), Best Practices (20).

**Thresholds**: 108+ Excellent | 96+ Good | 84+ Acceptable | <72 BLOCKED

**Exemption for trivial operations**: Single-field additions, test metadata, and throwaway configurations are exempt from the <72 block threshold. Score them for informational purposes but do not block deployment. Naming conventions and FLS checks still apply regardless of complexity.

### Category Details

**Structure & Format** (20 points):

- Valid metadata structure (-10 if invalid)
- API version present and >= 65.0 (-5 if outdated)
- Correct naming structure (-5 if wrong)

**Naming Conventions** (20 points):

- Custom objects/fields end with `__c` (-3 each violation)
- Use PascalCase for API names: `Account_Status__c` not `account_status__c` (-2 each)
- Meaningful labels (no abbreviations like `Acct`, `Sts`) (-2 each)
- Relationship names follow pattern: `[ParentObject]_[ChildObjects]` (-3)

**Data Integrity** (20 points):

- Required fields have sensible defaults or validation (-5)
- Number fields have appropriate precision/scale (-3)
- Picklist values properly defined with labels (-3)
- Relationship delete constraints specified (-3)
- Formula syntax valid (-5)

**Security & FLS** (20 points):

- Field-Level Security considered (-5 if sensitive field exposed)
- Sensitive field types flagged (SSN, Credit Card patterns) (-10)
- Object sharing model appropriate for data sensitivity (-5)
- Permission Sets used over Profile modifications (advisory)

**Documentation** (20 points):

- Description present and meaningful on objects/fields (-5 if missing)
- Help text for user-facing fields (-3 each)
- Clear error messages for validation rules (-3)
- Inline comments in complex formulas (-3)

**Best Practices** (20 points):

- Use Permission Sets over Profiles when possible (-3 if Profile-first)
- Avoid hardcoded Record IDs in formulas (-5 if found)
- Use Global Value Sets for reusable picklists (advisory)
- Master-Detail vs Lookup selection appropriate for use case (-3)

---

## Salesforce MCP Tool Reference

### 1. Initialize Connection

**Tool**: `org_init`
**Purpose**: Initialize MCP session and authenticate the org
**Must be called FIRST before any other operations**

```
org_init()
```

### 2. Create Metadata

**Tool**: `metadata_create`
**Purpose**: Create new metadata components in the org

```
Parameters:
  - type: "CustomObject" | "CustomField" | "PermissionSet" | "ValidationRule" | etc.
  - metadata: [{ ... }] (array of metadata definitions)
  - sf_user: Connection identifier
```

### 3. Update Metadata

**Tool**: `metadata_update`
**Purpose**: Update existing metadata components

```
Parameters:
  - type: Metadata type
  - metadata: [{ fullName: "...", ... }] (must include fullName)
  - sf_user: Connection identifier
```

### 4. Describe Object

**Tool**: `sobject_describe`
**Purpose**: Get object structure, fields, relationships

```
Parameters:
  - sObject: "Account" (required)
  - sf_user: Connection identifier
```

### 5. Tooling API Queries

**Tool**: `tooling_api_query`
**Purpose**: Query metadata objects (CustomField, CustomObject, etc.)

```
Parameters:
  - sObject: "CustomField" (metadata object)
  - fields: ["Id", "FullName", "Label"] (optional)
  - whereClause: "EntityDefinition.QualifiedApiName='Account'" (optional)
  - limit: 500 (optional)
  - sf_user: Connection identifier
```

---

## Supported Metadata Types

| Metadata Type   | `metadata_create` type | Common Operations                                |
| --------------- | ---------------------- | ------------------------------------------------ |
| Custom Object   | `CustomObject`         | Create with label, name field, sharing model     |
| Custom Field    | `CustomField`          | Create with fullName as `Object.Field__c`        |
| Permission Set  | `PermissionSet`        | Object + field permissions                       |
| Validation Rule | `ValidationRule`       | Formula-based validation                         |
| Record Type     | `RecordType`           | Picklist value assignments                       |
| Page Layout     | `Layout`               | Section and field placement                      |
| Lightning Page  | `FlexiPage`            | Record, App, and Home page creation/modification |

---

## Metadata Anti-Patterns

| Anti-Pattern                     | Fix                                          |
| -------------------------------- | -------------------------------------------- |
| Profile-based FLS                | Use Permission Sets for granular access      |
| Hardcoded IDs in formulas        | Use Custom Settings or Custom Metadata       |
| Validation rule without bypass   | Add `$Permission.Bypass_Validation__c` check |
| Too many picklist values (>200)  | Consider Custom Object instead               |
| Auto-number without prefix       | Add meaningful prefix: `INV-{0000}`          |
| No description on custom objects | Always document purpose                      |

---

## Common Errors

| Error                                  | Fix                                                            |
| -------------------------------------- | -------------------------------------------------------------- |
| `Cannot deploy to required field`      | Remove from fieldPermissions (auto-visible)                    |
| `Field does not exist`                 | Create Permission Set with field access                        |
| `SObject type 'X' not supported`       | Deploy metadata first                                          |
| `Element X is duplicated`              | Check for duplicate field names                                |
| `org_init not called`             | Always call `org_init()` FIRST                            |
| `DUPLICATE_DEVELOPER_NAME`             | FlexiPage name already exists; use `metadata_update` or rename |
| `FIELD_INTEGRITY_EXCEPTION` (vis rule) | Only EQUAL operator supported in visibility rules              |
| `force:recordDetail` not found         | Use `force:detailPanel` instead                                |
| `Cannot read properties of undefined`  | JSON Patch path is out of bounds; check section index          |

---

## Page Layout & Actions Management

Always follow this investigation sequence before making any changes to page layouts or actions.

### Investigation Sequence

**Step 1: Check for Lightning Record Pages FIRST**

Modern Salesforce orgs primarily use Lightning Record Pages with Dynamic Actions, not Classic Page Layouts. List all FlexiPages for the object before touching any classic layout:

```
tooling_api_query(
  sObject="FlexiPage",
  fields=["Id", "DeveloperName", "MasterLabel", "EntityDefinitionId"],
  whereClause="EntityDefinitionId = '<ObjectApiName>'",
  sf_user="<sf_user>"
)
```

**Step 2: Examine the Lightning Page Structure**

Read the FlexiPage metadata and look for `enableActionsConfiguration: true` in the `force:highlightsPanel` component. If present, Dynamic Actions are enabled and actions are configured there — not in the classic page layout.

```
metadata_read(
  type="FlexiPage",
  fullNames=["<FlexiPageDeveloperName>"],
  sf_user="<sf_user>"
)
```

**Step 3: Only Check Classic Layouts if No Lightning Page Found**

Classic layout actions are in `platformActionList.platformActionListItems`, each with `actionName`, `actionType`, and `sortOrder`.

### Action Update Patterns

| Pattern                             | When to Use                        | Update Method                                                                             |
| ----------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------- |
| Lightning Page with Dynamic Actions | `enableActionsConfiguration: true` | Add action to `actionNames.valueList.valueListItems`; provide complete `flexiPageRegions` |
| Classic Page Layout                 | No Lightning page found            | Replace entire `platformActionList` array; re-number all `sortOrder` values sequentially  |

### Common Pitfalls

- **Not checking for Lightning pages first** — always check FlexiPages before modifying classic layouts
- **Using `targetRecordType` on Update actions** — causes `INVALID_TYPE_FOR_OPERATION` error; remove it
- **Not updating all `sortOrder` values** — causes `DUPLICATE_VALUE` errors; replace entire array
- **Forgetting `enableActionsConfiguration` flag** — always check this property before deciding how to update
- **Using `standardLabel` unknowingly** — it overrides your custom label; omit or set deliberately

---

## Lightning Page (FlexiPage) Reference

### Template Names

| Page Type   | Template Name                         |
| ----------- | ------------------------------------- |
| Record Page | `flexipage:recordHomeTemplateDesktop` |
| App Page    | `flexipage:defaultAppHomeTemplate`    |
| Home Page   | `home:desktopTemplate`                |

### Component Names

Use the exact names below. Common mistakes are noted.

| Component         | Correct Name                                | Common Mistake               |
| ----------------- | ------------------------------------------- | ---------------------------- |
| Highlights Panel  | `force:highlightsPanel`                     |                              |
| Record Detail     | `force:detailPanel`                         | `force:recordDetail` (wrong) |
| Related Lists     | `force:relatedListContainer`                |                              |
| Chatter Feed      | `forceChatter:recordFeedContainer`          |                              |
| Tabs              | `flexipage:tabset`                          |                              |
| Rich Text         | `flexipage:richText`                        |                              |
| Activity Timeline | `runtime_sales_activities:activityPanel`    |                              |
| Path Assistant    | `runtime_sales_pathassistant:pathAssistant` |                              |

**Rich text property**: Use `richTextValue` (not `markup`) for the `flexipage:richText` component.

### Visibility Rules

**Only the `EQUAL` operator is supported** for FlexiPage `visibilityRule` criteria. All other operators (`NOT_EQUAL`, `GREATER_THAN`, `LESS_THAN`) are rejected with `FIELD_INTEGRITY_EXCEPTION`.

Supported `leftValue` patterns:

- `Record.FieldName` — record field values (e.g., `Record.Status`)
- `$User.FieldName` — current user fields (e.g., `$User.ProfileId`, `$User.UserRoleId`, `$User.Title`)

**Not supported**: `$Permission.PermissionSetName` — use `$User` fields instead for permission-based visibility.

### Home Page Regions

The `home:desktopTemplate` provides exactly 4 regions: `top`, `bottomLeft`, `bottomRight`, `sidebar`. There is no true three-column layout for Home Pages.

### FlexiPage Type Rules

| Type       | `sobjectType` | Notes                              |
| ---------- | ------------- | ---------------------------------- |
| RecordPage | Required      | Must specify the target object     |
| AppPage    | Must NOT set  | App pages are not object-specific  |
| HomePage   | Must NOT set  | Home pages are not object-specific |

---

## Page Layout Reference

### Related List Field Name Format

Related list column fields use a specific `OBJECT.FIELD_REFERENCE` format, not standard field API names.

| Object    | Example Fields                                       |
| --------- | ---------------------------------------------------- |
| Cases     | `CASES.CASE_NUMBER`, `CASES.SUBJECT`, `CASES.STATUS` |
| Contacts  | `FULL_NAME`, `CONTACT.PHONE1`, `CONTACT.EMAIL`       |
| Contracts | `CONTRACT.CONTRACT_NUMBER`, `CONTRACT.STATUS`        |

Invalid field names produce clear errors. Use `metadata_read` to discover valid field names from existing layouts.

### Layout Section Styles

| Style                   | Description                            |
| ----------------------- | -------------------------------------- |
| `TwoColumnsTopToBottom` | Two columns, fields flow top-to-bottom |
| `TwoColumnsLeftToRight` | Two columns, fields flow left-to-right |
| `OneColumn`             | Single column layout                   |
| `CustomLinks`           | Custom links section                   |

### Layout Item Behaviors

| Behavior   | Usage                                                |
| ---------- | ---------------------------------------------------- |
| `Edit`     | Standard editable fields                             |
| `Required` | Required fields (auto-visible, cannot be in PermSet) |
| `Readonly` | System fields like `IsClosedOnCreate`, `CreatedById` |

**System fields must use `Readonly`** — the API rejects `Edit` behavior on system-controlled fields.

---

## Cross-Skill Integration

| From Skill     | To sf-metadata | When                                                      |
| -------------- | -------------- | --------------------------------------------------------- |
| sf-apex        | -> sf-metadata | "Describe Invoice\_\_c" (discover fields before coding)   |
| sf-flow        | -> sf-metadata | "Describe object fields, record types, validation rules"  |
| sf-data        | -> sf-metadata | "Describe Custom_Object\_\_c fields" (discover structure) |
| sf-permissions | -> sf-metadata | "Create Permission Set for new object"                    |

| From sf-metadata | To Skill          | When                                                   |
| ---------------- | ----------------- | ------------------------------------------------------ |
| sf-metadata      | -> sf-flow        | After creating objects/fields that Flow will reference |
| sf-metadata      | -> sf-data        | After deploying metadata, create test data             |
| sf-metadata      | -> sf-permissions | Analyze permission sets in the org                     |

---

## Key Insights

| Insight                            | Issue                                    | Fix                                              |
| ---------------------------------- | ---------------------------------------- | ------------------------------------------------ |
| FLS is the Silent Killer           | Deployed fields invisible without FLS    | Always prompt for Permission Set generation      |
| Required Fields != Permission Sets | Salesforce rejects required fields in PS | Filter out required fields from fieldPermissions |
| Orchestration Order                | sf-data fails if objects not deployed    | metadata first, then data                        |

---

## Removed Capabilities

The following sf CLI features are **NOT supported** in the Salesforce MCP version:

- `sf project deploy start` (source deploy) - Use `metadata_create` / `metadata_update` instead
- `sf project retrieve start` (source retrieve) - Use `sobject_describe` / `tooling_api_query` instead
- `sf sobject describe` (CLI) - Use `sobject_describe` MCP tool instead
- Local metadata file generation - Replaced with direct org operations
- Scratch org operations - Remote orgs only
- sfdx-project.json operations - Not needed for MCP operations

---

## Dependencies

- **Salesforce MCP server** (required): All metadata operations use Salesforce MCP tools
  - Initialize with: `org_init()`
  - Tools: metadata_create, metadata_update, sobject_describe, tooling_api_query

- **sf-permissions** (optional): For permission analysis after metadata creation

---

## Notes

- **API Version**: Operations use org's default API version (recommend 62.0+)
- **Remote Org Only**: No local scratch org support; all operations target remote orgs
- **FLS**: Always generate Permission Sets after creating fields
- **Naming**: Use PascalCase for API names, meaningful labels with no abbreviations

---

## License

MIT License - See LICENSE file for details.
