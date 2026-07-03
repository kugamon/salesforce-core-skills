# sf-metadata

Salesforce metadata operations skill for AI coding tools. Create custom objects, fields, validation rules, record types, and permission sets directly in your org via the Salesforce MCP server.

## Features

- **Metadata Creation**: Create Custom Objects, Fields, Validation Rules, Record Types via MCP
- **Org Querying**: Describe objects, list fields, query metadata using Tooling API
- **FLS Management**: Auto-generate Permission Sets after creating objects/fields
- **Validation & Scoring**: Score metadata against 6 categories (0-120 points)

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Usage

#### Installation

Invoke the unified skill:

```
/sf-metadata
/sf-metadata create custom object Invoice__c
/sf-metadata describe Account
```

#### In other tools

Invoke the skill:

```
Skill: sf-metadata
Request: "Create a custom object called Invoice__c with Amount, Status, and Due Date fields"
```

### Common Operations

| Operation             | Example Request                                                    |
| --------------------- | ------------------------------------------------------------------ |
| Create Object         | "Create a custom object called Inspection\_\_c"                    |
| Create Field          | "Add a Currency field called Amount**c to Invoice**c"              |
| Create Validation     | "Add a validation rule requiring Close Date when Status is Closed" |
| Describe Object       | "Describe the Account object and show all fields"                  |
| Create Permission Set | "Generate a Permission Set for the Invoice\_\_c object"            |

## Related Skills

| Skill          | When to Use                                        |
| -------------- | -------------------------------------------------- |
| sf-data        | Query, create records, build/optimize SOQL queries |
| sf-permissions | Analyze and audit permission sets                  |
| sf-apex        | Create Apex classes and triggers                   |
| sf-flow        | Create and validate Flows                          |

## Salesforce MCP tools — for developers

> This section is for Salesforce developers building integrations. Admins can skip it.

| Operation       | MCP Tool                             |
| --------------- | ------------------------------------ |
| Create Metadata | `metadata_create(type, metadata)`    |
| Update Metadata | `metadata_update(type, metadata)`    |
| Describe Object | `sobject_describe(sObject)`          |
| Query Metadata  | `tooling_api_query(sObject, fields)` |

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

All metadata operations go through MCP tools regardless of mode. The mode
determines how large responses are handled and whether local tooling is
available.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)
