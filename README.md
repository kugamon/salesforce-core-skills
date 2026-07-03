# salesforce-core-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Claude Desktop / Cowork **plugin marketplace** that ships a single plugin (`salesforce-core`) with **eight general-purpose Salesforce admin & developer skills** — Apex, Flow, SOQL/Data, LWC, Metadata, Permissions, Architecture Diagrams, and Org Audit.

This repo **does not install an MCP server**. It assumes you already have a Salesforce MCP server connected to your org. The skills are **tool-agnostic** — they reference MCP capabilities generically rather than one vendor's tool names, so they work with any Salesforce MCP server.

## Why this plugin

Out of the box, Claude can call your Salesforce MCP server's tools — but it doesn't know:

- **How to write production-grade Apex** (bulkification, governor limits, SOLID, trigger frameworks) or score it consistently
- **How to build Flows that pass review** (naming, fault paths, entry conditions, subflow patterns)
- **How to optimize SOQL** (selectivity, indexes) or run safe bulk DML with cleanup/rollback plans
- **How to audit an org end-to-end** and produce Word / Excel / HTML reports
- **Which execution mode to use** — local SFDX metadata, Salesforce CLI, MCP + code execution, or MCP-only

This plugin encodes those rules as Cowork skills with structured scoring rubrics (150-point Apex, 110-point Flow, 165-point LWC SLDS 2), reference guides, metadata schemas, and validation scripts. After you install it, Claude routes Salesforce tasks to the right skill automatically.

## Prerequisites

You need a Salesforce MCP server connected to Claude Desktop, wired to your target org. Options include:

1. **[salesforce-mcp-auto-auth-chrome](https://github.com/kugamon/salesforce-mcp-auto-auth-chrome)** — local MCP server with 14 Salesforce tools that auto-refreshes its session from your Chrome login (no tokens to paste).
2. **Any other Salesforce MCP server** — the skills reason about capabilities (SOQL query, DML, metadata create, Tooling API), not specific tool names.

## The 8 skills

| Skill | What it does | Scoring |
| --- | --- | --- |
| [sf-apex](plugins/salesforce-core/skills/sf-apex/README.md) | Create, update and review Apex classes and triggers | 150-point |
| [sf-flow](plugins/salesforce-core/skills/sf-flow/README.md) | Create, update and review Flows | 110-point |
| [sf-data](plugins/salesforce-core/skills/sf-data/README.md) | SOQL build/optimize/execute, DML, test data factories | — |
| [sf-lwc](plugins/salesforce-core/skills/sf-lwc/README.md) | Lightning Web Components development | 165-point SLDS 2 |
| [sf-metadata](plugins/salesforce-core/skills/sf-metadata/README.md) | Metadata creation, org queries, permission set generation | — |
| [sf-permissions](plugins/salesforce-core/skills/sf-permissions/README.md) | Permission Set analysis, "Who has X?" auditing | — |
| [sf-diagram](plugins/salesforce-core/skills/sf-diagram/README.md) | Architecture diagrams (ERDs, OAuth flows, integrations) in Mermaid | — |
| [sf-audit](plugins/salesforce-core/skills/sf-audit/README.md) | Comprehensive org audit with Word, Excel and HTML reports | — |

## Org connection convention

The skills refer to `org_init` as shorthand for **your MCP server's session/connection initialization step**. Tool names vary by server:

- If your Salesforce MCP server exposes a connection or init tool, call it first and confirm the target org.
- If it does not, verify connectivity with a lightweight query (e.g. `SELECT Id FROM Organization LIMIT 1`) before running operations.

Likewise, generic tool names used in the skills (`soql_query`, `sobject_dml`, `metadata_create`, `tooling_api_query`, …) map to the equivalent tools on your server — most Salesforce MCP servers expose the same capabilities under similar names.

## Execution modes

Each skill detects one of four execution modes per session and adapts:

| Mode | When | What it enables |
| --- | --- | --- |
| `sfdx-repo` | Working dir is an SFDX project with metadata on disk | Read metadata locally, no API calls for body retrieval |
| `cli` | Salesforce CLI (`sf`) installed and authenticated | Bulk retrieve, CLI queries, code execution |
| `mcp-plus-code-execution` | MCP server + local Python/shell | MCP for org access, scripts for analysis and reports |
| `mcp-only` | MCP server only | Everything via MCP tools, paginated |

See any skill's `references/execution-modes.md` for details.

## Repo layout

```
salesforce-core-skills/                  # repo root = a marketplace
├── .claude-plugin/
│   └── marketplace.json                 # marketplace manifest (lists 1 plugin)
├── README.md                            # you are here
├── LICENSE                              # MIT
└── plugins/
    └── salesforce-core/                 # the plugin itself
        ├── .claude-plugin/
        │   └── plugin.json              # plugin manifest
        ├── hooks/                       # PreToolUse validation hooks
        ├── shared/                      # shared validator scripts
        └── skills/
            ├── sf-apex/                 # each skill: SKILL.md + README +
            ├── sf-audit/                #   references/ + assets/ + scripts/
            ├── sf-data/
            ├── sf-diagram/
            ├── sf-flow/
            ├── sf-lwc/
            ├── sf-metadata/
            └── sf-permissions/
```

The marketplace pattern means future contributors can add more plugins under `plugins/<name>/` and register them in `marketplace.json` — the install URL stays the same.

## Install

### Option 1 — Cowork "Add marketplace" (recommended)

1. Open Claude Desktop → **Customize** → **Marketplace**.
2. Click **+ Add marketplace** (sometimes labeled **Sync from URL**).
3. URL: `kugamon/salesforce-core-skills` — or the full URL `https://github.com/kugamon/salesforce-core-skills`.
4. Click **Sync**. You'll see one plugin: `salesforce-core`.
5. Click **Install**.
6. Restart Claude (Cmd+Q + reopen on macOS) so the skills load into the system prompt.

### Option 2 — Local folder

1. Clone the repo or download the source.
2. In Claude Desktop → **Customize** → **Personal plugins** → **+** → **Local folder**.
3. Pick `plugins/salesforce-core/` (the directory that contains `.claude-plugin/plugin.json`).
4. Toggle on. Restart Claude.

### Option 3 — Manually pin to settings.json

```json
{
  "extraKnownMarketplaces": [
    { "url": "https://github.com/kugamon/salesforce-core-skills" }
  ],
  "enabledPlugins": ["salesforce-core"]
}
```

## Verify

After installing and restarting, test a skill:

> "Review all Apex triggers in my org for bulkification issues and governor limit risks. For each issue found, suggest a fix and score the code."

Claude should detect the execution mode, connect to your Salesforce MCP server, and run the sf-apex review workflow with 150-point scoring.

## Sample prompts

- "Perform a thorough audit of the Apex classes and Flows in my Salesforce org. Generate Word, HTML and Excel versions of the report."
- "I need a new custom object called Inspection__c with fields for Status, Inspector, and Date. Then create an Apex trigger that auto-assigns inspectors based on region, a Screen Flow for field technicians to submit inspection results, and seed 50 test records so I can demo it."
- "Analyze all my profiles and permission sets and recommend security fixes and cleanup."
- "Create an ERD diagram for my Sales Cloud data model including Account, Contact, Opportunity, and Lead."
- "Build a SOQL query that shows me all opportunities closing this quarter with amount over $100K."

## Model choice

For reports, analysis and simple metadata tasks a fast model (e.g. Sonnet) is a good, cost-effective choice. For deeper design or debugging work, a more capable model may be needed.

## Troubleshooting

**"This repository isn't a marketplace — no manifest found at .claude-plugin/marketplace.json".** Make sure you're on `main` — the manifest lives at the repo root.

**Plugin loads but skills don't trigger.** Restart Claude Desktop fully (Cmd+Q on macOS). Skills are loaded at session start.

**Tools missing entirely.** Confirm your Salesforce MCP server is connected and authenticated to the right org. Check `claude_desktop_config.json`, or ask Claude: *"what's the org name?"* — a working server answers via a SOQL query on `Organization`.

**Skill references a tool your server doesn't have.** The skills use generic tool names (`soql_query`, `sobject_dml`, `metadata_create`, …). Map them to your server's equivalents — see [Org connection convention](#org-connection-convention).

## Contributing

PRs welcome. Especially useful contributions:

- Additional skills (e.g. sf-reports, sf-experience-cloud) — drop a folder under `plugins/salesforce-core/skills/`
- New plugins under `plugins/<name>/`, registered in `marketplace.json`
- Improved scoring rubrics and reference guides as Salesforce releases evolve

Keep skill files terse — a focused skill that triggers correctly beats a sprawling one Claude scrolls past.

## License

MIT — see [LICENSE](./LICENSE).

Portions derived from the MIT-licensed [sf-skills](https://github.com/Jaganpro/sf-skills) project by Jag Valaiyapathy; original copyright notices are preserved in the LICENSE file. Per-skill credits are in each skill's `CREDITS.md`.

This project is **not affiliated with Salesforce, Inc. or with Anthropic.** Tool names, APIs, and platform behavior may change as Salesforce evolves; verify against official Salesforce documentation.
