# salesforce-core-skills

General-purpose Salesforce admin and developer skills for AI coding tools (Claude Code, Claude Cowork, and other agents that support skill plugins). The skills work with **any Salesforce MCP server** — they reference MCP capabilities generically rather than a specific vendor's tool names.

The plugin coordinates the individual Salesforce skills (Apex, Flow, Data/SOQL, LWC, Metadata, Permissions, Diagrams, Audit) into a unified admin suite. Tasks are routed to the appropriate skill based on context — e.g., Apex code reviews go to `sf-apex`, data operations go to `sf-data`, metadata queries go to `sf-metadata`. Each skill also works independently.

## Skills

| Skill                                             | Description                                                                      |
| ------------------------------------------------- | -------------------------------------------------------------------------------- |
| [sf-apex](skills/sf-apex/README.md)               | Create, update and review Apex classes and triggers (150-point scoring)          |
| [sf-flow](skills/sf-flow/README.md)               | Create, update and review Flows (110-point scoring)                              |
| [sf-data](skills/sf-data/README.md)               | SOQL query building/optimization/execution, DML operations, test data factories  |
| [sf-lwc](skills/sf-lwc/README.md)                 | Lightning Web Components development (165-point SLDS 2 scoring)                  |
| [sf-metadata](skills/sf-metadata/README.md)       | Metadata creation, org queries, permission set generation                        |
| [sf-permissions](skills/sf-permissions/README.md) | Permission Set analysis, "Who has X?" auditing                                   |
| [sf-diagram](skills/sf-diagram/README.md)         | Architecture diagrams (ERDs, OAuth, integrations) in Mermaid                     |
| [sf-audit](skills/sf-audit/README.md)             | Comprehensive org audit with Word, Excel, and HTML reports                       |

## Org connection convention

The skills refer to `org_init` as shorthand for **your MCP server's session/connection initialization step**. Tool names vary by server:

- If your Salesforce MCP server exposes a connection or init tool, call it first and confirm the target org.
- If it does not, verify connectivity with a lightweight query (e.g., `SELECT Id FROM Organization LIMIT 1`) before running operations.

Similarly, generic tool names used in the skills (`soql_query`, `sobject_dml`, `metadata_create`, `tooling_api_query`, etc.) map to the equivalent tools on your server — most Salesforce MCP servers expose the same capabilities under similar names.

## Sample Prompts

- "Perform a thorough audit of the Apex classes and Flows in my Salesforce org. Generate Word, HTML and Excel versions of the report."
- "I need a new custom object called Inspection__c with fields for Status, Inspector, and Date. Then create an Apex trigger that auto-assigns inspectors based on region, a Screen Flow for field technicians to submit inspection results, and seed 50 test records so I can demo it."
- "Review all Apex triggers in my org for bulkification issues and governor limit risks. For each issue found, suggest a fix and score the code."
- "Analyze all my profiles and permission sets and recommend security fixes and cleanup."
- "Create an ERD diagram for my Sales Cloud data model including Account, Contact, Opportunity, and Lead."
- "Build a SOQL query that shows me all opportunities closing this quarter with amount over $100K."

## Execution modes

Each skill supports four execution modes (detected once per session): `sfdx-repo` (metadata on disk), `cli` (Salesforce CLI), `mcp-plus-code-execution`, and `mcp-only`. See any skill's `references/execution-modes.md` for details.

## Model choice

For reports, analysis and simple metadata tasks a fast model (e.g. Sonnet) is a good, cost-effective choice. For deeper design or debugging work, a more capable model may be needed.

## Requirements

- Claude Cowork or Claude Code with skill plugins enabled
- A Salesforce MCP server connected to your target org

## Installation

Install as a Claude Code / Cowork plugin, or copy individual skill folders from `skills/` into your skills directory.

## License

MIT License — see [LICENSE](LICENSE) for details. Portions derived from the MIT-licensed [sf-skills](https://github.com/Jaganpro/sf-skills) project by Jag Valaiyapathy; original copyright notices are preserved in the LICENSE file. Per-skill credits are in each skill's `CREDITS.md`.
