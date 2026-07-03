# sf-audit

Run a comprehensive Salesforce org audit that inventories and evaluates all major metadata categories: Apex classes, Apex triggers, Flows, Process Builders, Workflow Rules, LWC components, custom objects and fields, validation rules, Profiles, and Permission Sets. Generates Word, Excel, and HTML reports.

## Features

- **Complete org inventory**: Counts and catalogs every component across all metadata categories
- **Code quality scoring**: 150-point Apex, 110-point Flow, 165-point LWC, and 120-point Metadata rubrics (from domain skills)
- **Trigger review**: Inventories Apex triggers and flags anti-patterns (logic in trigger body, missing bulkification)
- **Permission audit**: Inventories Profiles, Permission Sets, and PSGs; detects overly broad permissions, orphaned PS, and outdated PSGs
- **Data model audit**: Scores custom objects against the metadata rubric and flags cross-object issues
- **Validation rule review**: Inventories rules and flags missing descriptions, hardcoded IDs, and missing bypass mechanisms
- **Legacy automation inventory**: Catalogs active Workflow Rules and Process Builders with migration priorities
- **Automation overlap detection**: Identifies objects with multiple automation types active (triggers, flows, PBs, workflow rules)
- **Report generation**: Word (.docx), Excel (.xlsx), and HTML reports with per-component scores and findings
- **Actionable summary**: Overall health score, components needing attention, findings by severity, migration priorities
- **Incremental audits**: Re-score only components that changed since the last audit, carrying forward unchanged scores
- **Four execution modes**: Works with local SFDX repos (fastest), Salesforce CLI, MCP with code execution, or MCP-only

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Quick Start

### Installation

Invoke the unified skill:

```
/sf-audit
/sf-audit full
```

### In OpenAI Codex or other tools

```
Skill: sf-audit
Request: "Audit my Salesforce org"
```

### Incremental Audit

To update a previous audit (only re-scores changed components):

```
Audit my Salesforce org. Previous audit is at ~/audits/2026-01/audit_output/
```

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

The skill auto-detects the best available mode. In `sfdx-repo` mode, metadata
is read directly from disk. In `cli` mode, bulk retrieval uses the Salesforce
CLI. In `mcp-plus-code-execution` mode, large responses are downloaded via
artifact URLs for local processing. In `mcp-core` mode, large responses are
paged through in-context with `fetch_more`.

## Cross-Skill Integration

| Related Skill  | When to Use                                         |
| -------------- | --------------------------------------------------- |
| sf-apex        | Fix or review Apex classes/triggers in the audit    |
| sf-flow        | Fix or review Flows found in the audit              |
| sf-lwc         | Fix or review LWC components found in the audit     |
| sf-permissions | Fix permission or Profile issues found in the audit |
| sf-metadata    | Fix data model issues found in the audit            |
| sf-data        | Query or update data after fixing issues            |
| sf-diagram     | Visualize architecture or permission hierarchies    |

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org

## License

MIT License — see [LICENSE](LICENSE) for details.

