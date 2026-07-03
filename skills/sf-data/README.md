# sf-data

Salesforce data and SOQL expert skill for AI coding tools. Build, optimize, and execute SOQL queries, manage data operations, generate test data, and validate operations via the Salesforce MCP server.

> **Note**: This skill covers all SOQL and data operation capabilities. Use `/sf-data` for any data-related work — querying, DML, validation, and object discovery.

## Features

- **Natural Language to SOQL**: Convert plain English requests to optimized queries
- **SOQL Query Building & Review**: Build, optimize, and validate queries — with or without executing them
- **Query Optimization**: Analyze selectivity, indexing, and performance
- **Relationship Queries**: Parent-child, child-parent, polymorphic, semi-joins, anti-joins
- **Aggregate Functions**: COUNT, SUM, AVG, MIN, MAX with GROUP BY
- **CRUD Operations**: Create, read, update, delete records via Salesforce MCP server
- **Test Data Factories**: Bulk-ready Apex factories for standard objects
- **Bulk Operations**: Insert/update/delete/upsert multiple records efficiently
- **Record Tracking & Cleanup**: Savepoint/rollback, cleanup scripts
- **Pre-Flight Validation**: Lightweight pass/fail checks for data operations (PII detection, missing params, syntax errors)

## Installation

For full installation instructions (various AI tools), see the [root README](../../../../README.md).

## Usage

#### Installation

Invoke the unified skill:

```
/sf-data
/sf-data query SELECT Id FROM Account LIMIT 10
/sf-data insert Account records
```

#### In other tools

Invoke the skill:

```
Skill: sf-data
Request: "Create 251 test Account records with varying Industries for trigger testing in my dev sandbox"
```

### Common Operations

| Operation        | Example Request                                          |
| ---------------- | -------------------------------------------------------- |
| Build Query      | "Write a SOQL query to get accounts with their contacts" |
| Optimize Query   | "Optimize this SOQL query for performance"               |
| Natural Language | "Who are our top 10 customers by revenue?"               |
| Execute Query    | "Query all Accounts with related Contacts"               |
| Create           | "Create 10 test Opportunities at various stages"         |
| Bulk Insert      | "Insert 500 accounts from accounts.csv"                  |
| Update           | "Update Account 001xxx with new Industry"                |
| Delete           | "Delete all test records with Name LIKE 'Test%'"         |
| Cleanup          | "Generate cleanup script for all records created today"  |

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

All data operations go through MCP tools regardless of mode. The mode
determines how large query results are retrieved — see the skill for details.

## Related Skills

| Skill          | When to Use                                              |
| -------------- | -------------------------------------------------------- |
| sf-apex        | Create and validate Apex code, triggers, test classes    |
| sf-flow        | Create and validate Salesforce Flows                     |
| sf-metadata    | Describe objects, fields, permission sets, profiles etc. |
| sf-permissions | Permission analysis queries                              |
| sf-diagram     | Visualize query results as diagrams                      |

## Validation

This skill includes validation scripts that check SOQL queries and data operations for common issues like unbounded queries, hardcoded IDs, non-indexed filter fields, and missing LIMIT clauses. See the [For Contributors](#for-contributors) section for details on the available scripts and hook integration.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org

## Salesforce MCP tools — for developers

> This section is for Salesforce developers building integrations. Admins can skip it.

| Operation | MCP Tool                                   |
| --------- | ------------------------------------------ |
| Query     | `soql_query(sObject, fields, whereClause)` |
| Create    | `sobject_dml(operation="insert", ...)`     |
| Update    | `sobject_dml(operation="update", ...)`     |
| Delete    | `sobject_dml(operation="delete", ...)`     |
| Upsert    | `sobject_dml(operation="upsert", ...)`     |
| Describe  | `sobject_describe(sObject)`                |
| Tooling   | `tooling_api_query(sObject, fields)`       |

## For Contributors

### Validation Scripts

This skill ships Python validation scripts in `scripts/` for SOQL and data operation validation. These are available for manual use and can be integrated with plugin hooks.

| Script                       | Purpose                                                        |
| ---------------------------- | -------------------------------------------------------------- |
| `soql_validator.py`          | SOQL syntax validation, selectivity checks, optimization hints |
| `validate_data_operation.py` | 130-point data operation scoring across 7 categories           |
| `mcp_validator.py`           | MCP parameter validation (Tier 1 data, Tier 2 code)            |
| `mcp_validator_cli.py`       | CLI wrapper for manual pre-flight checks                       |
| `post-write-validate.py`     | Post-write hook for local file validation                      |

### SOQL Validator Checks

For `.soql` and `.apex` files containing SOQL, `soql_validator.py` checks:

| Check                    | What it catches                                                |
| ------------------------ | -------------------------------------------------------------- |
| Syntax errors            | Malformed SOQL                                                 |
| Missing WHERE            | Unbounded queries on large objects                             |
| Missing LIMIT            | Queries without limits that could hit governor limits          |
| Hardcoded IDs            | `WHERE Id = '001...'` — brittle, breaks on org refresh         |
| Non-indexed fields       | WHERE on non-indexed fields causing full table scans           |
| Optimization suggestions | SELECT \* patterns, missing ORDER BY, relationship query hints |

### Manual MCP pre-flight

Validate a data operation payload before calling the MCP tool:

```bash
echo '{"tool":"soql_query","params":{"sObject":"Account","fields":["Id","Name"],"whereClause":"Industry = '\''Technology'\''"}}' \
  | python scripts/mcp_validator_cli.py --format report
```

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)
