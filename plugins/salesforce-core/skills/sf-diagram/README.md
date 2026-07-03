# sf-diagram

Salesforce architecture diagram generation skill for AI coding tools. Create Mermaid diagrams for OAuth flows, data models (ERDs), integration sequences, system landscapes, and role hierarchies.

## Features

- **OAuth Flows**: Authorization Code, JWT Bearer, PKCE, Client Credentials, Device Flow
- **Data Models (ERD)**: Object relationships with color coding by type
- **Integration Sequences**: API callouts, event-driven flows
- **System Landscapes**: High-level architecture diagrams
- **Role Hierarchies**: User hierarchies, profile/permission structures
- **Dual Output**: Mermaid + ASCII fallback for every diagram

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Usage

#### Installation

Invoke the unified skill:

```
/sf-diagram
/sf-diagram erd Account Contact Opportunity
```

#### In other tools

Invoke the skill:

```
Skill: sf-diagram
Request: "Create a JWT Bearer OAuth flow diagram"
```

### Common Operations

| Operation   | Example Request                                       |
| ----------- | ----------------------------------------------------- |
| OAuth Flow  | "Create a JWT Bearer OAuth flow diagram"              |
| ERD         | "Create an ERD for Account, Contact, and Opportunity" |
| Integration | "Diagram our Salesforce to SAP integration"           |
| Landscape   | "Create a system architecture diagram"                |
| Hierarchy   | "Visualize our role hierarchy"                        |
| Agentforce  | "Create flow diagram for FAQ Agent"                   |

## Related Skills

| Skill          | When to Use                                        |
| -------------- | -------------------------------------------------- |
| sf-metadata    | Get real object/field definitions for ERD diagrams |
| sf-permissions | Get permission data for hierarchy visualizations   |

## Salesforce MCP tools — for developers

> This section is for Salesforce developers building integrations. Admins can skip it.

| Operation       | MCP Tool                                    |
| --------------- | ------------------------------------------- |
| Describe Object | `sobject_describe(sObject)`                 |
| Record Counts   | `soql_query(fields=["COUNT(Id)"])`          |
| Custom Objects  | `tooling_api_query(sObject="CustomObject")` |

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

Diagram generation works in all modes. MCP tools are only needed for
org-connected ERD diagrams.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server (optional - only needed for org-connected ERDs)

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)
