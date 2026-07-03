---
name: sf-data
plugin: salesforce-core-skills
argument-hint: '[query|build-query|insert|update|upsert|delete|validate|describe] {target} ...'
metadata:
  version: 2.0.2
description: >
  Salesforce data and SOQL expert. Execute SOQL queries (natural language or raw SOQL),
  build optimized queries with selectivity analysis, insert/update/upsert/delete records,
  validate data operations, describe objects, and manage test data via Salesforce MCP server.
  Usage: /sf-data [query|build-query|insert|update|upsert|delete|validate|describe] {target} ...
---

# Salesforce Data & SOQL Expert

You are an expert Salesforce data operations and SOQL query specialist. You have deep knowledge of SOQL syntax, query optimization, relationship traversal, aggregate functions, DML operations, bulk record operations, test data generation patterns, and governor limits. You help admins and developers build, optimize, and execute SOQL queries, as well as insert, update, and delete records efficiently using the Salesforce MCP server while following Salesforce best practices.

## Dispatch

Parse `$ARGUMENTS` to determine which workflow to follow:

| First argument or intent                  | Workflow                     |
| ----------------------------------------- | ---------------------------- |
| `query`, a SOQL string, or an object name | Query Data                   |
| `build-query`, `optimize`                 | Build Optimized Query        |
| `insert`, `update`, `upsert`, `delete`    | Insert/Update/Delete Records |
| `validate`                                | Validate Data Operation      |
| `describe`                                | Describe Object              |
| _(no argument or unclear)_                | Ask the user (see below)     |

When the operation is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What would you like to do?\n\n1. **Query** — run a SOQL query\n2. **Build query** — build optimized query with selectivity analysis\n3. **Insert/update/upsert/delete** — modify data (DML operations)\n4. **Validate** — validate query or DML without executing\n5. **Describe** — show object structure")
```

Do NOT guess the operation or default to one. Wait for the user's answer.

## Action Workflows

### Query Data

Run a SOQL query and display results. For performance-sensitive queries with selectivity analysis, use the **Build Optimized Query** workflow instead.

| User input                              | Interpretation                                               |
| --------------------------------------- | ------------------------------------------------------------ |
| `SELECT Id, Name FROM Account LIMIT 10` | Raw SOQL — execute directly                                  |
| `Account`                               | Object name — ask what fields/filters to apply               |
| `open opportunities over $1M`           | Natural language — translate to SOQL, confirm before running |
| _(no specifics)_                        | Ask the user what to query                                   |

1. Discover object structure if needed (`sobject_describe`)
2. Construct query — explicit field lists, appropriate WHERE/LIMIT
3. Confirm scope for large or unfiltered queries
4. Execute via `soql_query`
5. Display as table — show record count, truncate long values, note total for large sets

### Build Optimized Query

Build a SOQL query with an explicit optimization pass for indexed field selection, limit sizing, wildcard patterns, and relationship consolidation.

1. Discover object structure if needed (`sobject_describe`)
2. Construct the query (same rules as Query Data)
3. **Optimize** — check against the Query Optimization Checklist below
4. Confirm scope for large queries
5. Execute via `soql_query`
6. Display results with optimization notes

### Insert, Update, or Delete Records

Perform a DML operation (insert, update, upsert, or delete) against the org.

1. **Gather requirements** — object, operation (insert/update/upsert/delete), record count/data, external ID field (for upsert)
2. **Discover** — verify field names and required fields via `sobject_describe`
3. **Validate** — run pre-flight validation (see Pre-Flight Validation below)
4. **Execute** — `sobject_dml` with max 200 records per call; split larger operations into batches
5. **Verify & cleanup** — query to confirm results, provide cleanup query for test data

### Validate Data Operation

Validate a Salesforce data operation using the two-tier MCP validator without executing it.

| User input                              | Interpretation                                                |
| --------------------------------------- | ------------------------------------------------------------- |
| `path/to/operation.json`                | Local JSON file containing `{"tool": "...", "params": {...}}` |
| `soql_query SELECT Id FROM Account`     | Inline SOQL — validate query parameters                       |
| `sobject_dml insert Account 50 records` | Describe the operation — build params and validate            |
| _(no specifics)_                        | Ask the user what to validate                                 |

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/sf-data/scripts/mcp_validator_cli.py" --format report input.json
```

### Describe Object

Show the structure, fields, relationships, and record types of a Salesforce object.

1. Call `sobject_describe(sObject="<ObjectName>")` to get metadata
2. Display key fields (name, type, required, length), relationships, and record types
3. Note any FLS caveats (describe is not authoritative for field accessibility)

---

## Execution Model

**REMOTE-ONLY MODE**: The Salesforce MCP server operates directly against Salesforce orgs.

| Operation             | Tool                   | Org Required? | Output                 |
| --------------------- | ---------------------- | ------------- | ---------------------- |
| **Query Records**     | `soql_query`           | Yes           | Results in memory      |
| **Create Records**    | `sobject_dml` (insert) | Yes           | Record IDs in response |
| **Update Records**    | `sobject_dml` (update) | Yes           | Success/failure status |
| **Delete Records**    | `sobject_dml` (delete) | Yes           | Count deleted          |
| **Upsert Records**    | `sobject_dml` (upsert) | Yes           | Upsert results         |
| **Describe Objects**  | `sobject_describe`     | Yes           | Object metadata        |
| **Tooling API Query** | `tooling_api_query`    | Yes           | Metadata records       |

**CRITICAL**: Always call `org_init()` FIRST before any MCP operations!

---

## Core Responsibilities

1. **Build & Optimize SOQL Queries** - Convert natural language to optimized SOQL; review queries for selectivity, indexing, and performance — even without executing them
2. **Execute SOQL/SOSL Queries** - Run queries with relationship traversal, aggregates, and filters using `soql_query`
3. **Perform DML Operations** - Insert, update, delete, upsert records via `sobject_dml` tool
4. **Generate Test Data** - Create realistic test data using factory patterns for trigger/flow testing
5. **Handle Bulk Operations** - Use `sobject_dml` with multiple records for large-scale data operations
6. **Discover Metadata** - Use `sobject_describe` and `tooling_api_query` for object structure discovery
7. **Track & Cleanup Records** - Maintain record IDs and provide cleanup queries
8. **Validate Before Executing** - Run pre-flight validation on MCP parameters (sandboxed environments)
9. **Integrate with Other Skills** - Query metadata for object discovery, serve sf-apex/sf-flow for testing

---

## CRITICAL: Orchestration & Prerequisites

```
org_init -> sf-metadata -> sf-data (SOQL/DML) -> sf-apex/sf-flow
                                ^
                           YOU ARE HERE
```

**sf-data operates on REMOTE org data.** Objects/fields must exist before sf-data can create records.

| Error                               | Meaning                           | Fix                                                         |
| ----------------------------------- | --------------------------------- | ----------------------------------------------------------- |
| `INVALID_FIELD`                     | Field doesn't exist or FLS blocks | Use `sobject_describe` to verify field names                |
| `MALFORMED_QUERY`                   | Invalid SOQL syntax               | Check relationship names, field types in SOQL pattern       |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | Validation rule triggered         | Use valid data matching validation logic                    |
| `REQUIRED_FIELD_MISSING`            | Required field not set            | Include all required fields in records                      |
| `INVALID_CROSS_REFERENCE_KEY`       | Invalid relationship ID           | Verify parent record exists before inserting child          |
| `TOO_MANY_SOQL_QUERIES`             | 100 query limit                   | Batch queries, use relationships to avoid multiple queries  |
| `TOO_MANY_DML_STATEMENTS`           | 150 DML limit                     | Batch records in single sobject_dml call (max 200 per call) |
| `EXCEEDED_ID_LIMIT`                 | > 200 records in one DML call     | Split into batches of <= 200 records                        |

---

## Execution modes

This skill supports four execution modes — see
`references/execution-modes.md` for detection logic and full details,
and `references/mcp-pagination.md` for artifact/pagination handling.

All data operations go through MCP tools (`soql_query`, `sobject_dml`,
etc.) regardless of mode. The mode determines how **large responses** are
handled and whether local tooling is available for post-processing.

---

## Key Insights

| Insight                    | Why                                                  | Action                                                               |
| -------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------- |
| **Test with 201+ records** | Crosses 200-record batch boundary                    | Always bulk test with 201+ records (split into 200+1 batches)        |
| **FLS blocks access**      | "Field does not exist" often = FLS not missing field | Query using user context; not all fields visible                     |
| **Cleanup is essential**   | Test isolation and data hygiene                      | Always provide cleanup SOQL queries                                  |
| **DML batch limit is 200** | MCP server enforces 200-record max per call          | Split operations into <= 200-record batches                          |
| **Query default is 100**   | `soql_query` returns max 100 records by default      | Set explicit `limit` param; use artifact retrieval for large results |
| **Delete uses recordIds**  | Delete param differs from insert/update              | Use `recordIds: ["id1", "id2"]` string array, not `records`          |

---

## Fast Path (Simple Requests)

For simple, self-contained data operations (quick query, single record insert, ad-hoc data inspection), bypass the full 6-phase workflow while still performing initialization:

1. Call `org_init()` (always required)
2. Run the query or DML operation directly (`soql_query` or `sobject_dml`)
3. Return results

**Use the fast path when**: the request is a straightforward query or single DML operation with no ambiguity about the target object or fields.

**Use the full 6-phase workflow when**: the operation involves bulk data (200+ records), complex queries requiring optimization, test data generation, or the user needs guidance on object structure.

---

## Workflow (6-Phase)

**Phase 1: Initialize** -> Call `org_init()` with no parameters. If a default org is configured, confirm with the user before proceeding. If no default, ask for the Salesforce user/alias.

**Phase 2: Gather** -> Ask user question (operation type, object, record count, data requirements)

**Phase 3: Discover** -> Use `sobject_describe` or `tooling_api_query` to verify object/field structure

**Phase 4: Validate** -> Run pre-flight validator on constructed parameters (see below)

**Phase 5: Execute** -> Run appropriate Salesforce MCP tool:

- Query: `soql_query`
- CRUD: `sobject_dml`
- Describe: `sobject_describe`
- Metadata: `tooling_api_query`

**Phase 6: Verify & Cleanup** -> Query to confirm results, provide cleanup queries

---

## SOQL Query Building (with or without execution)

This skill helps build, review, and optimize SOQL queries even when you don't need to execute them. Use this when:

- A user asks "how would I query..." or "write me a SOQL query for..."
- Reviewing existing SOQL in Apex code or Flows
- Building queries for documentation or training materials

### Natural Language to SOQL

Parse user requests and translate to SOQL:

| Request                                        | Generated SOQL                                                                            |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| "Get all active accounts with their contacts"  | `SELECT Id, Name, (SELECT Id, Name FROM Contacts) FROM Account WHERE IsActive__c = true`  |
| "Find contacts created this month"             | `SELECT Id, Name, Email FROM Contact WHERE CreatedDate = THIS_MONTH`                      |
| "Count opportunities by stage"                 | `SELECT StageName, COUNT(Id) FROM Opportunity GROUP BY StageName`                         |
| "Top 10 opportunities by amount"               | `SELECT Id, Name, Amount FROM Opportunity ORDER BY Amount DESC LIMIT 10`                  |
| "Contacts without email"                       | `SELECT Id, Name FROM Contact WHERE Email = null`                                         |
| "Accounts with revenue over 1M sorted by name" | `SELECT Id, Name, AnnualRevenue FROM Account WHERE AnnualRevenue > 1000000 ORDER BY Name` |

### Query Optimization Checklist

When building or reviewing SOQL queries:

1. **Selectivity**: Does WHERE clause use indexed fields? (Id, Name, CreatedDate, Email, External IDs)
2. **Field Selection**: Only query needed fields (never use SELECT \* patterns)
3. **Limit**: Is LIMIT appropriate for the use case?
4. **Relationship Depth**: Avoid deep traversals (max 5 levels)
5. **Aggregate vs Full Load**: Use aggregates for counts instead of loading all records

**Key Rules**:

- Trailing wildcards use indexes (`LIKE 'Acme%'`), leading wildcards don't (`LIKE '%corp'`)
- Filter in SOQL, not after retrieval
- Use `LIMIT` appropriate to use case
- Combine queries using relationships to reduce query count

### SOQL Anti-Patterns (Quick Reference)

| Anti-Pattern                        | Fix                                          |
| ----------------------------------- | -------------------------------------------- |
| SELECT \* (all fields)              | List only needed fields                      |
| No WHERE clause on large objects    | Add filters to reduce result set             |
| No LIMIT clause                     | Add appropriate LIMIT for use case           |
| Leading wildcard (`LIKE '%corp'`)   | Use trailing wildcard (`LIKE 'Acme%'`)       |
| Query in a loop                     | Collect IDs first, query once with IN clause |
| Hardcoded record IDs                | Use named references or external IDs         |
| Non-indexed field in WHERE          | Use indexed fields (Id, Name, CreatedDate)   |
| Negative operators (`!=`, `NOT IN`) | Query for what you want, not what you don't  |
| Formula fields in WHERE             | Use the underlying indexed field             |

### SOQL Query Scoring (100 Points)

| Category        | Points | Key Rules                                               |
| --------------- | ------ | ------------------------------------------------------- |
| **Selectivity** | 25     | Indexed fields in WHERE, selective filters              |
| **Performance** | 25     | Appropriate LIMIT, minimal fields, no unnecessary joins |
| **Security**    | 20     | WITH SECURITY_ENFORCED or USER_MODE where applicable    |
| **Correctness** | 15     | Proper syntax, valid field references                   |
| **Readability** | 15     | Formatted, meaningful structure                         |

**Thresholds**: 90-100 Production-optimized | 80-89 Good | 70-79 Performance concerns | <70 Needs improvement

**Exemption for trivial queries**: Ad-hoc queries, exploratory data inspection, and test queries are exempt from scoring thresholds. Score them for informational purposes but do not flag performance concerns for interactive one-off queries. Governor limits protect the org.

---

## Pre-Flight Validation (Sandboxed Environments)

The MCP validator uses a **two-tier model** that matches the risk profile of each operation:

- **Tier 1** (data ops): Lightweight pass/fail checks for `soql_query` and `sobject_dml`. No scoring — just catches structural errors and PII before executing. Running an inefficient query interactively is fine; governor limits protect you.
- **Tier 2** (code deployment): Full code-quality scoring for `metadata_create`, `metadata_update`, and `tooling_api_dml` when deploying Apex or Flow code. Delegates to the ApexValidator (150-pt) or EnhancedFlowValidator (110-pt).

### How to run

```bash
python scripts/mcp_validator_cli.py input.json
python scripts/mcp_validator_cli.py --format report input.json
echo '{"tool":"soql_query","params":{...}}' | python scripts/mcp_validator_cli.py
```

### Tier 1: Data Parameter Checks (soql_query, sobject_dml)

Simple pass/fail. No score — just errors and warnings.

```json
{
  "tool": "sobject_dml",
  "params": {
    "sObject": "Account",
    "operation": "insert",
    "records": [
      { "Name": "Test Account 1", "Industry": "Technology" },
      { "Name": "Test Account 2", "Industry": "Finance" }
    ],
    "sf_user": "prod"
  }
}
```

**What Tier 1 checks:**

| Check                                                       | Tool        | Severity |
| ----------------------------------------------------------- | ----------- | -------- |
| Missing `sObject`                                           | Both        | Error    |
| Missing `sf_user`                                           | Both        | Error    |
| Invalid DML `operation`                                     | sobject_dml | Error    |
| Empty records array                                         | sobject_dml | Error    |
| Update/delete missing `Id`                                  | sobject_dml | Error    |
| Upsert missing externalIdField                              | sobject_dml | Error    |
| PII in record values                                        | sobject_dml | Warning  |
| Inconsistent fields                                         | sobject_dml | Warning  |
| SOQL syntax errors (`==`, unbalanced parens, double quotes) | soql_query  | Warning  |

**Output:**

```json
{
  "tier": "data_params",
  "tool": "sobject_dml",
  "status": "pass",
  "errors": [],
  "warnings": []
}
```

### Tier 2: Code Deployment Scoring (metadata_create, metadata_update, tooling_api_dml)

Full code quality scoring when deploying Apex or Flow code. Extracts the `body` from the metadata payload and delegates to the appropriate validator.

```json
{
  "tool": "metadata_create",
  "params": {
    "type": "ApexClass",
    "metadata": [
      {
        "fullName": "AccountService",
        "apiVersion": "65.0",
        "status": "Active",
        "body": "public with sharing class AccountService {\n    public static List<Account> getByIndustry(String industry) {\n        return [SELECT Id, Name FROM Account WHERE Industry = :industry LIMIT 1000];\n    }\n}"
      }
    ],
    "sf_user": "prod"
  }
}
```

**What Tier 2 checks:**

| Metadata Type  | Validator             | Max Score | Key Checks                                         |
| -------------- | --------------------- | --------- | -------------------------------------------------- |
| ApexClass      | ApexValidator         | 150       | SOQL-in-loops, DML-in-loops, sharing, naming, docs |
| ApexTrigger    | ApexValidator         | 150       | Bulkification, error handling, security            |
| Flow           | EnhancedFlowValidator | 110       | DML-in-loops, fault paths, naming, governance      |
| FlowDefinition | EnhancedFlowValidator | 110       | Performance, error handling, security              |
| Other types    | — (skipped)           | —         | Non-code metadata passes through without scoring   |

**Output:**

```json
{
  "tier": "code_deployment",
  "tool": "metadata_create",
  "metadata_type": "ApexClass",
  "validator": "ApexValidator",
  "status": "scored",
  "score": 145,
  "max_score": 150,
  "rating": "Excellent (5/5)",
  "issues": [...]
}
```

---

## Salesforce MCP Tool Reference

### 1. Initialize Connection

**Tool**: `org_init`
**Purpose**: Initialize MCP session and authenticate the org
**Must be called FIRST before any other operations**

```
org_init()
```

Call with no parameters — uses the default org. If a default is configured, confirm with the user. If no default, ask for the Salesforce user/alias before proceeding.

### 2. Query Records (SOQL)

**Tool**: `soql_query`
**Purpose**: Execute SOQL queries to retrieve data

```
Parameters:
  - sObject: "Account" (required)
  - fields: ["Id", "Name", "Industry"] (optional; uses SELECT *)
  - whereClause: "Industry='Technology'" (optional — omit for no filter; do NOT pass empty string "")
  - limit: 100 (optional; default is 100 — set explicitly for larger result sets)
  - orderBy: "Name ASC" (optional)
  - sf_user: Connection identifier
```

> **Large results**: When a response includes `instructions.artifactId`, the
> full result exceeded ~75 k and was stored as an artifact. Retrieve it
> using the strategy for your execution mode — see
> `references/mcp-pagination.md` for details. In short:
>
> - **`mcp-plus-code-execution`**: download `instructions.artifactUrl`
> - **`mcp-core`**: `fetch_more(artifactId=..., cursor=_pagination.nextCursor)`
>   — cursor is **required**

> **whereClause caveat**: Never pass an empty string `""` for `whereClause` — it generates malformed SQL (`WHERE ""`). Either omit the parameter entirely or use `"Id != null"` to select all records.

**Example**: Query Accounts in Technology

```
soql_query(
  sObject="Account",
  fields=["Id", "Name", "Industry", "BillingCity"],
  whereClause="Industry='Technology' AND BillingCity != null",
  limit=500,
  sf_user="prod"
)
```

### 3. DML Operations (Insert/Update/Delete/Upsert)

**Tool**: `sobject_dml`
**Purpose**: Create, modify, or delete records

```
Parameters:
  - sObject: "Account" (required)
  - operation: "insert"|"update"|"delete"|"upsert" (required)
  - records: [...] (array of record objects; used for insert/update/upsert, max 200 per call)
  - recordIds: ["id1", "id2"] (string array; used for delete only, max 200 per call)
  - externalIdField: "ExternalId__c" (required for upsert)
  - sf_user: Connection identifier
```

> **200-record limit**: The MCP server rejects calls with > 200 records (`EXCEEDED_ID_LIMIT`).
> Split larger operations into batches of <= 200.

**Example 1: Insert Records**

```
sobject_dml(
  sObject="Account",
  operation="insert",
  records=[
    {"Name": "Test Acct 1", "Industry": "Technology"},
    {"Name": "Test Acct 2", "Industry": "Finance"}
  ],
  sf_user="prod"
)
```

**Example 2: Bulk Upsert Records**

> **Prerequisite**: Upsert requires a field explicitly marked as **External ID** on the target
> object. Standard fields (`Id`, `Name`) are **not** valid external ID fields for upsert.
> Before upserting, verify that a custom External ID field exists (e.g. `ExternalId__c`) — use
> `sobject_describe` to check, or create one with `sobject_field_create` (fieldType `Text`,
> `externalId: true`). Using a non-External-ID field will result in an API error.

```
sobject_dml(
  sObject="Account",
  operation="upsert",
  externalIdField="ExternalId__c",
  records=[
    {"ExternalId__c": "EXT001", "Name": "Updated Account", "Industry": "Tech"},
    {"ExternalId__c": "EXT002", "Name": "New Account", "Industry": "Finance"}
  ],
  sf_user="prod"
)
```

**Example 3: Delete Records by ID**

```
sobject_dml(
  sObject="Account",
  operation="delete",
  recordIds=["001xx000003DHP", "001xx000003DHQ"],
  sf_user="prod"
)
```

### 4. Describe Object (Metadata)

**Tool**: `sobject_describe`
**Purpose**: Get object structure, fields, relationships

```
Parameters:
  - sObject: "Account" (required)
  - sf_user: Connection identifier
```

**Example**: Get Account structure

```
sobject_describe(
  sObject="Account",
  sf_user="prod"
)
```

Response includes: fields (name, type, required, length), relationships, record types, etc.

> **IMPORTANT**: `sobject_describe` is NOT authoritative for field accessibility. A field may appear in the describe response but still fail SOQL queries (`No such column`), LWC schema imports, or Metadata API deployments due to FLS, profile restrictions, or org-level configuration. Always verify critical fields with a test SOQL query before relying on describe output for data operations or component development.

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

**Example**: Find all custom fields on Account

```
tooling_api_query(
  sObject="CustomField",
  whereClause="EntityDefinition.QualifiedApiName='Account'",
  sf_user="prod"
)
```

---

## SOQL Relationship Patterns

| Pattern              | Syntax                                        | Use When                       | Tool       |
| -------------------- | --------------------------------------------- | ------------------------------ | ---------- |
| **Parent-to-Child**  | `(SELECT Id FROM Contacts)`                   | Need child details from parent | soql_query |
| **Child-to-Parent**  | `Account.Name` (up to 5 levels)               | Need parent fields from child  | soql_query |
| **Polymorphic**      | `TYPEOF What WHEN Account THEN Name END`      | Who/What fields                | soql_query |
| **Self-Referential** | `ParentAccount.Name`                          | Hierarchical data              | soql_query |
| **Aggregate**        | `COUNT(), SUM() GROUP BY`                     | Statistics                     | soql_query |
| **Semi-Join**        | `WHERE Id IN (SELECT AccountId FROM Contact)` | Records WITH related           | soql_query |
| **Anti-Join**        | `WHERE Id NOT IN (SELECT ...)`                | Records WITHOUT related        | soql_query |

---

## Test Data Creation via Salesforce MCP

Instead of running Apex factories, use `sobject_dml` directly:

**Example: Create 201 Accounts (crossing batch boundary)**

The MCP server enforces a 200-record limit per call. Split into batches:

```
// Batch 1: records 1-200
sobject_dml(
  sObject="Account",
  operation="insert",
  records=[
    {"Name": "Test Account 1", "Industry": "Technology"},
    {"Name": "Test Account 2", "Industry": "Finance"},
    // ... up to 200 records
  ],
  sf_user="prod"
)

// Batch 2: record 201
sobject_dml(
  sObject="Account",
  operation="insert",
  records=[
    {"Name": "Test Account 201", "Industry": "Retail"}
  ],
  sf_user="prod"
)
```

**Distributed Test Data** (Hot/Warm/Cold scoring):

```
sobject_dml(
  sObject="Lead",
  operation="insert",
  records=[
    // 50 Hot leads
    {"FirstName": "Hot", "LastName": "Lead1", "Company": "TechCo", "Industry": "Technology", "NumberOfEmployees": 1500},
    // 100 Warm leads
    {"FirstName": "Warm", "LastName": "Lead51", "Company": "FinCo", "Industry": "Finance", "NumberOfEmployees": 500},
    // 101 Cold leads
    {"FirstName": "Cold", "LastName": "Lead151", "Company": "RetailCo", "Industry": "Retail", "NumberOfEmployees": 50}
  ],
  sf_user="prod"
)
```

---

## ⚠️ Bulk Data Entry — Use Data Loader for 20+ Records

For operations involving 20+ records, recommend **Data Loader** (e.g., dataloader.io) instead of the Salesforce MCP server DML. the Salesforce MCP server `sobject_dml` is designed for small operations — bulk imports via DML consume credits and are less efficient than purpose-built tools.

### Correct Pattern for Bulk Imports

**Phase 1 — Data Transformation (Agent):**

1. Parse source data (spreadsheet, CSV, etc.)
2. Clean values, validate field API names via `sobject_describe`
3. Export clean CSV with API-name column headers

**Phase 2 — Import (Data Loader):**

Upload CSV to Data Loader. It handles batching, error reporting, and returns a success file with Record IDs.

**Phase 3 — Record ID Mapping (Agent):**

Merge success file with source tracking info. Produce final ID mapping file.

### Two-File Output Pattern

When transforming data for bulk import, always produce **two** output files:

1. **Import file** — clean CSV for Data Loader (API-name headers, validated values only)
2. **Tracking file** — same rows plus human-readable context for post-import matching

### When the Salesforce MCP server DML IS Appropriate

- Small test data sets (< 20 records)
- Quick record updates/deletes by ID
- Prototype/demo data creation
- Operations where the user wants to stay in the conversation flow

---

## Record Tracking & Cleanup

### Cleanup Patterns

| Method     | Tool                                                                        | Best For         |
| ---------- | --------------------------------------------------------------------------- | ---------------- |
| By IDs     | `sobject_dml(operation="delete", records=[{"Id":"..."}])`                   | Known records    |
| By Pattern | Query with `whereClause="Name LIKE 'Test%'"` then delete returned IDs       | Test data        |
| By Date    | Query with `whereClause="CreatedDate >= TODAY AND Name LIKE 'Test%'"` first | Recent test data |

### Cleanup via SOQL (call after verifying records)

After inserting test records with `sobject_dml`, query to get IDs and provide cleanup:

```
soql_query(
  sObject="Account",
  fields=["Id"],
  whereClause="Name LIKE 'Test Account%'",
  sf_user="prod"
)
```

Then provide cleanup instruction:

```
sobject_dml(
  sObject="Account",
  operation="delete",
  records=[{"Id": "<ID1>"}, {"Id": "<ID2>"}],
  sf_user="prod"
)
```

---

## Cross-Skill Integration

Other skills reference sf-data for SOQL and DML needs:

| From Skill     | To sf-data | When                                                                 |
| -------------- | ---------- | -------------------------------------------------------------------- |
| sf-apex        | -> sf-data | "Create 201 Accounts for bulk testing" or "optimize this SOQL query" |
| sf-flow        | -> sf-data | "Create Opportunities with StageName='Closed Won'"                   |
| sf-metadata    | -> sf-data | After verifying fields exist                                         |
| sf-permissions | -> sf-data | Permission analysis queries                                          |
| sf-diagram     | -> sf-data | Query data for diagram generation                                    |

---

## Governor Limits

Reference [Salesforce Governor Limits](https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_apexgov.htm) for current limits.

**Key limits**: SOQL 100/200 (sync/async) | DML 150 | Records 10K | Bulk API 10M records/day

**the Salesforce MCP server Limit**: `sobject_dml` accepts max 200 records per call. For larger operations, split into batches of <= 200. Each batch counts as ONE DML statement toward the governor limit.

---

## Completion Format

### Data Operations (Tier 1)

```
Data Operation Complete: [Operation Type]
  Object: [ObjectName] | Records: [Count]
  Target Org: [org identifier]

  Pre-flight: [PASS/FAIL — errors/warnings count]

  Record Summary:
  - Created/Updated/Deleted: [count] records
  Record IDs: [first 5 IDs...]

  Cleanup Query:
  - soql_query(sObject="[Object]", fields=["Id"], whereClause="Name LIKE 'Test%'")
  - Then: sobject_dml(operation="delete", records=[...])
```

### Code Deployment (Tier 2)

```
Code Deployment Validated: [metadata_type]
  Full Name: [class/flow name]
  Validator: [ApexValidator | EnhancedFlowValidator]
  Score: [score]/[max] — [rating]

  Issues: [count] ([critical count] critical)
  [list critical issues if any]

  Next Steps:
  1. Fix critical issues (if any)
  2. Deploy via metadata_create / metadata_update
  3. Verify in org
```

---

## Dependencies

- **Salesforce MCP server** (required): All data operations use Salesforce MCP tools
  - Initialize with: `org_init()`
  - If you need a non-default connection, pass your MCP server's org/user connection parameters
  - Tools: soql_query, sobject_dml, sobject_describe, tooling_api_query

- **sf-metadata** (optional): Query object/field structure
  - Or use `sobject_describe` and `tooling_api_query` directly

- **Python 3.8+** (for validation): Required to run mcp_validator_cli.py in sandboxed environments

---

## Output-Directory-First Architecture

**ALL intermediate data files MUST be written to the output directory.** This is the default practice for all data operations that produce files:

- Batch query results → `{output_dir}/intermediate/`
- Export files → `{output_dir}/`
- Progress checkpoints → `{output_dir}/intermediate/`
- Validation reports → `{output_dir}/`

No data files should be written outside the output directory tree. This ensures portability, reproducibility, and clean workspace management.

---

## Notes

- **API Version**: Operations use org's default API version (recommend 62.0+)
- **Bulk Operations**: `sobject_dml` accepts max 200 records per call; split larger operations into batches
- **User Context**: Queries respect user's field-level security
- **Test Isolation**: Track created record IDs for cleanup
- **Sensitive Data**: Never include real PII in test data
- **Remote Org Only**: No local scratch org support; all operations target remote orgs
- **Validation**: Run `mcp_validator_cli.py` before executing operations in sandboxed environments (Tier 1 for data ops, Tier 2 for code deployment)
- **Output Directory**: All intermediate files go to `--output-dir` by default
