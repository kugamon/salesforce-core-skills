# sf-apex

Generates and reviews Salesforce Apex code with 2025 best practices and 150-point scoring. Build production-ready, secure, and maintainable Apex.

## Features

- **Code Generation**: Create Apex classes, triggers (TAF), tests, batch jobs, queueables from requirements
- **Code Review**: Analyze existing Apex for best practices violations with actionable fixes
- **150-Point Scoring**: Automated validation across 8 categories
- **Template Library**: Pre-built patterns for common class types
- **LSP Integration**: Real-time syntax validation via Apex Language Server

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Quick Start

### 1. Invoke the skill

#### Installation

Invoke the unified skill:

```
/sf-apex
/sf-apex create AccountService class with CRUD methods
/sf-apex validate MyClass
```

#### In other tools

```
Skill: sf-apex
Request: "Create an AccountService class with CRUD methods"
```

### 2. Answer requirements questions

The skill will ask about:

- Class type (Service, Selector, Trigger, Batch, etc.)
- Primary purpose
- Target object(s)
- Test requirements

### 3. Review generated code

The skill generates:

- Main class with ApexDoc comments
- Corresponding test class with 90%+ coverage patterns
- Proper naming following conventions

## Scoring System (150 Points)

| Category       | Points | Focus                                                    |
| -------------- | ------ | -------------------------------------------------------- |
| Bulkification  | 25     | No SOQL/DML in loops, collection patterns                |
| Security       | 25     | CRUD/FLS checks, no injection, SOQL injection prevention |
| Testing        | 25     | Test coverage, assertions, negative tests                |
| Architecture   | 20     | SOLID principles, separation of concerns                 |
| Error Handling | 15     | Try-catch, custom exceptions, logging                    |
| Naming         | 15     | Consistent naming, ApexDoc comments                      |
| Performance    | 15     | Async patterns, efficient queries                        |
| Code Quality   | 10     | Clean code, no hardcoding                                |

**Thresholds**: 90+ | 80-89 | 70-79 | Block: <60

## Templates

| Template             | Use Case                          |
| -------------------- | --------------------------------- |
| `trigger.trigger`    | Trigger with TAF pattern          |
| `trigger-action.cls` | Trigger Actions Framework handler |
| `service.cls`        | Business logic service class      |
| `selector.cls`       | SOQL selector pattern             |
| `batch.cls`          | Batch Apex job                    |
| `queueable.cls`      | Queueable async job               |
| `test-class.cls`     | Test class with data factory      |

## Validation

Validation runs automatically **when this skill is installed as part of the
`salesforce-core-skills` plugin** — the plugin registers a `PreToolUse` hook in
`hooks/hooks.json` that fires before every `metadata_create`,
`metadata_update`, and `tooling_api_dml`. The hook is **advisory**: it always
returns `permissionDecision: allow` and emits a context message describing
critical issues (SOQL/DML in loops, injection risks) and AI anti-patterns
(invalid Java types, hallucinated methods, unsafe Map access). The agent is
expected to stop on a 🚨 critical message; the hook does not deny the call.

> **Standalone installs do not get the hook.** If you've installed only the
> sf-apex skill (without the `salesforce-core-skills` plugin's `hooks/hooks.json`), the
> hook does not fire. Run validation manually before deploying:
>
> ```bash
> python3 scripts/validate_apex_cli.py <path-to-file.cls>
> ```

Use `/sf-apex validate` at any time for on-demand checks:

| Invocation                              | What happens                                           |
| --------------------------------------- | ------------------------------------------------------ |
| `/sf-apex validate MyClass`             | Fetches the class from your org and validates it       |
| `/sf-apex validate path/to/MyClass.cls` | Validates a local file                                 |
| `/sf-apex validate MyClass,OtherClass`  | Validates multiple classes with a summary table        |
| `/sf-apex validate All`                 | Validates all Apex classes in the org, sorted by score |

## Cross-Skill Integration

| Related Skill | When to Use                                 |
| ------------- | ------------------------------------------- |
| sf-flow       | Create Flow to call @InvocableMethod        |
| sf-lwc        | Create LWC to call @AuraEnabled controllers |
| sf-testing    | Run tests and analyze coverage              |
| sf-deploy     | Deploy Apex to org                          |

## Documentation

- [Naming Conventions](references/naming-conventions.md)
- [Best Practices](references/best-practices.md)
- [Testing Guide](references/testing-guide.md)
- [Flow Integration](references/flow-integration.md)
- [Design Patterns](references/design-patterns.md)

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

All Apex operations go through MCP tools regardless of mode. The mode
determines how large responses are handled and whether local tooling is
available.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)

## For Contributors

### Validation Hooks

This skill ships Python validation scripts in `scripts/`. The pre-deployment hook is registered at the **plugin level** in `salesforce-core-skills/hooks/hooks.json` (not in this skill's directory) and is **type-scoped** — it inspects the metadata type in each MCP call and only validates Apex payloads. Standalone skill installs without the plugin's `hooks/hooks.json` will not get automatic validation; run the scripts manually.

#### Hook 1: `pre-mcp-validate.py` — pre-deployment (advisory, plugin-only)

Registered in the plugin's `hooks/hooks.json` as a `PreToolUse` hook. Fires before every `metadata_create`, `metadata_update`, and `tooling_api_dml` call **when installed as part of `salesforce-core-skills`**. The script inspects the metadata type and only validates Apex payloads; non-Apex types pass through silently. Every outcome returns `permissionDecision: allow`; the hook surfaces findings via `additionalContext` and relies on the agent to stop on a critical message. Fork the script to return `deny` if hard blocking is required.

| Result                                              | Action                                                     |
| --------------------------------------------------- | ---------------------------------------------------------- |
| Critical/High issues (SOQL/DML in loops, injection) | Allows the call; emits a 🚨 critical-issue context message |
| Score < 67%                                         | Allows the call; emits a ⚠️ advisory context message       |
| Pass                                                | Allows the call; emits a ✅ score-summary context message  |
| Non-Apex type (Flow, CustomObject, etc.)            | Passes through silently (no context emitted)               |

#### Hook 2: `post-tool-validate.py` — post-write (advisory, not wired by default)

Available for PostToolUse `Write|Edit` integration but **not currently registered** in `hooks/hooks.json`. When enabled, runs a two-phase validation pipeline and outputs a scored report to the transcript.

**Phase 1 — `validate_apex.py`: 150-point static analysis**

| Category       | Points | What it checks                              |
| -------------- | ------ | ------------------------------------------- |
| Bulkification  | 25     | SOQL/DML inside loops                       |
| Security       | 25     | Sharing keywords, SOQL injection risk       |
| Testing        | 25     | Test methods, assertions, coverage patterns |
| Architecture   | 20     | SOLID principles, separation of concerns    |
| Clean Code     | 20     | PascalCase classes, camelCase methods       |
| Error Handling | 15     | Empty catch blocks, exception patterns      |
| Performance    | 10     | Async patterns, governor limit awareness    |
| Documentation  | 10     | ApexDoc on public methods                   |

**Phase 1.5 — `llm_pattern_validator.py`: LLM anti-pattern detection**

Catches mistakes that AI models commonly make when generating Apex:

- **Java types**: `ArrayList`, `HashMap`, `StringBuilder`, etc. (don't exist in Apex)
- **Hallucinated methods**: `stream()`, `collect()`, `addMilliseconds()`, `getOrDefault()`, `entrySet()`, `String.matches()`, etc.
- **Unsafe Map access**: `map.get(key).method()` without null check or `containsKey()`
- **SOQL field gaps**: queries with very few fields where subsequent code accesses many more

### Scripts

| Script                   | Purpose                                                                    |
| ------------------------ | -------------------------------------------------------------------------- |
| `validate_apex_cli.py`   | Standalone script used by `/sf-apex validate` — takes a file path argument |
| `pre-mcp-validate.py`    | PreToolUse hook adapter — translates hook stdin to mcp_validator format    |
| `post-write-validate.py` | Legacy hook (Write only, no LLM check). Not wired in hooks.json            |
| `mcp_validator_cli.py`   | Manual pre-flight check for MCP metadata deployment calls                  |

**Manual MCP pre-flight** — validate an Apex deployment payload before calling the MCP tool:

```bash
echo '{"tool":"metadata_create","params":{"type":"ApexClass","metadata":[{"fullName":"MyClass","body":"public class MyClass {}"}]}}' \
  | python scripts/mcp_validator_cli.py --format report
```

### Integration Testing (Actual Org)

This section is primarily for open-source contributors to this repository.
If you are using the skill as an end user, you do not need to run these tests.

To validate end-to-end behavior in a real Salesforce org (LLM prompt → MCP calls → deployed metadata → org verification), use:

- [`tests/test_apex_mcp_integration.md`](tests/test_apex_mcp_integration.md)

The protocol includes:

- a reusable prompt for running the test in an LLM session
- positive deployment scenarios
- negative scenarios (critical/advisory findings)
- verification queries and optional cleanup steps
