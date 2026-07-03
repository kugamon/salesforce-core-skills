# sf-permissions

Salesforce permission analysis and auditing skill for AI coding tools. Analyze Permission Set hierarchies, find "who has access to X?", audit user permissions, and identify security risks via the Salesforce MCP server.

## Features

- **Hierarchy Viewer**: Visualize all PS/PSG in an org as structured trees
- **Permission Detector**: Find which PS/PSG grant a specific permission
- **User Analyzer**: Show all permissions assigned to a specific user
- **Security Audit**: Identify overly broad permissions and security risks
- **Permission Set Creation**: Generate and deploy Permission Sets

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Usage

#### Installation

Invoke the unified skill:

```
/sf-permissions
/sf-permissions audit
/sf-permissions analyze Account delete access
```

#### In other tools

Invoke the skill:

```
Skill: sf-permissions
Request: "Who has delete access to the Account object?"
```

### Common Operations

| Operation      | Example Request                                     |
| -------------- | --------------------------------------------------- |
| Hierarchy      | "Show the permission set hierarchy in my org"       |
| Who Has X?     | "Who has edit access to Account.AnnualRevenue?"     |
| User Analysis  | "What permissions does john@company.com have?"      |
| Security Audit | "Find all permission sets with ModifyAllData"       |
| PS Creation    | "Create a read-only permission set for contractors" |

## Related Skills

| Skill       | When to Use                                          |
| ----------- | ---------------------------------------------------- |
| sf-metadata | Create permission sets and manage metadata           |
| sf-diagram  | Visualize permission hierarchies as Mermaid diagrams |
| sf-data     | Query user assignments in bulk                       |

## Salesforce MCP tools — for developers

> This section is for Salesforce developers building integrations. Admins can skip it.

| Operation         | MCP Tool                                  |
| ----------------- | ----------------------------------------- |
| Query PS/PSG      | `soql_query(sObject="PermissionSet")`     |
| Query Permissions | `soql_query(sObject="ObjectPermissions")` |
| Tooling Queries   | `tooling_api_query(sObject, fields)`      |
| Create PS         | `metadata_create(type="PermissionSet")`   |

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

All permission operations go through MCP tools regardless of mode. The
mode determines how large responses (e.g. PermissionSet/PSG datasets)
are handled.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)
