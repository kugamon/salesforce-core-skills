# sf-flow

Creates and validates Salesforce Flows with 110-point scoring and Winter '26 best practices. Build production-ready, performant, and secure flows.

## Features

- **Flow Generation**: Create record-triggered, screen, autolaunched, and scheduled flows
- **110-Point Scoring**: Automated validation across 6 categories
- **Template Library**: Pre-built patterns for common flow types
- **Bulk Safety**: Automatic checks for 251+ record handling
- **Element Library**: Complete Wait, Loop, Get Records, Transform patterns
- **Transform vs Loop Guide**: Decision pattern for choosing Transform (data mapping) vs Loop (per-record decisions)
- **Flow Quick Reference**: Comprehensive cheat sheet with flow type selection trees and element reference

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Quick Start

### 1. Invoke the skill

#### Installation

Invoke the unified skill:

```
/sf-flow
/sf-flow create before-save flow for Account
/sf-flow validate Auto_Lead_Assignment
```

#### In other tools

```
Skill: sf-flow
Request: "Create a before-save flow to auto-populate Account fields"
```

### 2. Answer requirements questions

The skill will ask about:

- Flow type (Record-Triggered, Screen, Autolaunched, etc.)
- Trigger object and timing (Before/After Save)
- Entry conditions
- Actions needed

### 3. Review generated flow

The skill generates:

- Complete Flow XML metadata
- Proper element naming with alphabetical ordering
- Entry conditions and fault connectors

## Scoring System (110 Points)

| Category       | Points | Focus                                         |
| -------------- | ------ | --------------------------------------------- |
| Bulkification  | 25     | No DML/queries in loops, collection variables |
| Entry Criteria | 20     | Selective, indexed fields                     |
| Naming         | 20     | Consistent element names, descriptions        |
| Fault Handling | 20     | Fault paths on all DML/queries                |
| Performance    | 15     | Minimal elements, efficient paths             |
| Documentation  | 10     | Element descriptions, flow description        |

**Minimum Score**: 88 (80%) for deployment

## Key Insights

| Rule                  | Details                                                                |
| --------------------- | ---------------------------------------------------------------------- |
| Before vs After Save  | Before: same-record updates (no DML). After: related records, callouts |
| Test with 251 records | Batch boundary at 200. Test bulk behavior                              |
| $Record context       | Single record, not a collection. Platform handles batching             |
| Transform vs Loop     | Transform: data mapping (30-50% faster). Loop: per-record decisions    |
| Deploy as Draft       | Always deploy flows as Draft first, then activate                      |

## Templates

| Template                    | Use Case               |
| --------------------------- | ---------------------- |
| `before-save-template.xml`  | Field auto-population  |
| `after-save-template.xml`   | Related record updates |
| `screen-flow-template.xml`  | User interaction flows |
| `autolaunched-template.xml` | Background automation  |
| `scheduled-template.xml`    | Time-based automation  |
| `wait-template.xml`         | Wait element patterns  |

## Cross-Skill Integration

| Related Skill | When to Use                               |
| ------------- | ----------------------------------------- |
| sf-apex       | Create @InvocableMethod for complex logic |
| sf-lwc        | Create screen components for custom UI    |
| sf-metadata   | Deploy custom objects BEFORE flows        |
| sf-deploy     | Deploy flows to org                       |

## Orchestration Order

```
sf-metadata → sf-flow → sf-deploy → sf-data
```

Always deploy custom objects/fields BEFORE flows that reference them.

## Documentation

- [Transform vs Loop Guide](references/transform-vs-loop-guide.md) - When to use each element
- [Flow Quick Reference](references/flow-quick-reference.md) - Comprehensive cheat sheet
- [Flow Best Practices](references/flow-best-practices.md) - Performance and design patterns
- [LWC Integration](references/lwc-integration-guide.md) - Screen components
- [Testing Guide](references/testing-guide.md) - Validation strategies

## Validation

Validation is **manual and required** before every Flow deployment. The skill
ships a `PreToolUse` hook script (`scripts/pre-mcp-validate.py`), but **it is
not wired up in every runtime environment** — there is no `hooks/hooks.json`
shipped with this skill and the script does not run unless your host registers
it. Until you have confirmed the hook is registered for your host, run the
validator manually before every `metadata_create`, `metadata_update`, or
`tooling_api_dml` call on a Flow:

```bash
python3 scripts/validate_flow_cli.py <path-to-flow.flow-meta.xml>
```

The validator blocks deployment for CRITICAL/HIGH issues (DML in loops, missing
fault paths on any fallible element, invalid resource properties). See the
four-question self-check in `SKILL.md` for the contract.

Use `/sf-flow validate` at any time for on-demand checks:

| Invocation                                                           | What happens                                    |
| -------------------------------------------------------------------- | ----------------------------------------------- |
| `/sf-flow validate Auto_Lead_Assignment`                             | Fetches the flow from your org and validates it |
| `/sf-flow validate force-app/.../Auto_Lead_Assignment.flow-meta.xml` | Validates a local file                          |
| `/sf-flow validate Auto_Lead_Assignment,Screen_Case_Intake`          | Validates multiple flows with a summary table   |
| `/sf-flow validate All`                                              | Validates all flows in the org, sorted by score |

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

All Flow operations go through MCP tools regardless of mode. The mode
determines how large responses are handled and whether local tooling is
available.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org
  - API Version 65.0+ (Winter '26)

## For Contributors

### Validation Hooks

This skill ships Python validation scripts in `scripts/`. A `PreToolUse` hook
adapter (`scripts/pre-mcp-validate.py`) is shipped for hosts that want to wire
it up, but **no `hooks/hooks.json` is shipped with the skill** and registration
is the host's responsibility. Treat the validator as manual until you have
confirmed your host runs the hook.

#### Hook 1: `pre-mcp-validate.py` — pre-deployment (script only, not auto-registered)

Designed for use as a plugin-level PreToolUse hook against `metadata_create`,
`metadata_update`, and `tooling_api_dml`. The script inspects the metadata type
and only validates Flow payloads; non-Flow types pass through silently. It is
**not registered** by the skill itself — register it in your host's
`hooks.json` if you want validator output surfaced before each Flow deployment.

The hook is **advisory**: every outcome returns `permissionDecision: allow`
and emits an `additionalContext` message. Nothing is blocked at the protocol
level — the agent is expected to read the message and choose to stop before
calling the deployment tool. If you need hard blocking, fork the hook to
return `deny`/`ask` when CRITICAL/HIGH issues are present.

| Result                                                   | Action                                                     |
| -------------------------------------------------------- | ---------------------------------------------------------- |
| Critical/High issues (DML in loops, missing fault paths) | Allows the call; emits a 🚨 critical-issue context message |
| Score < 80% (< 88/110)                                   | Allows the call; emits a ⚠️ advisory context message       |
| Pass                                                     | Allows the call; emits a ✅ score-summary context message  |
| Non-Flow type (ApexClass, CustomObject, etc.)            | Passes through silently (no context emitted)               |

#### Hook 2: `post-tool-validate.py` — post-write (advisory, not wired by default)

Available for PostToolUse `Write|Edit` integration. The skill does not ship a `hooks.json`, so this is host-side opt-in. When registered, runs `EnhancedFlowValidator` on any `.flow-meta.xml` file and outputs a scored report to the transcript.

**`validate_flow.py`: 110-point static analysis**

| Category                       | Points | What it checks                                                      |
| ------------------------------ | ------ | ------------------------------------------------------------------- |
| Design & Naming                | 25     | Element naming conventions, alphabetical ordering, flow description |
| Logic & Structure              | 20     | Entry criteria, flow variables, decision logic                      |
| Architecture & Orchestration   | 20     | Flow type appropriateness, subflow usage, API versioning            |
| Performance & Bulk Safety      | 20     | DML/queries in loops, 251-record bulk handling, collection patterns |
| Error Handling & Observability | 15     | Fault connectors on all DML/queries, unhandled paths                |
| Security & Governance          | 10     | Sharing mode, hardcoded IDs, API version ≥ 59.0                     |

### Scripts

| Script                   | Purpose                                                                    |
| ------------------------ | -------------------------------------------------------------------------- |
| `validate_flow_cli.py`   | Standalone CLI used by `/sf-flow validate` — takes a file path argument    |
| `pre-mcp-validate.py`    | PreToolUse hook adapter — translates hook stdin to FlowMCPValidator format |
| `post-write-validate.py` | Legacy hook (Write only). Not wired in hooks.json                          |
| `mcp_validator_cli.py`   | Manual pre-flight check for MCP Flow deployment calls                      |

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)
