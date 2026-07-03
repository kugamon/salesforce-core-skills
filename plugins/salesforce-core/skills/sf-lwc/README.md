# sf-lwc

Lightning Web Components development skill with PICKLES architecture methodology, 165-point SLDS 2 scoring, and dark mode support. Build modern, accessible Salesforce UIs.

## Features

- **Component Scaffolding**: Generate complete LWC bundles (JS, HTML, CSS, meta.xml)
- **PICKLES Architecture**: Structured methodology for robust, maintainable components
- **165-Point Scoring**: SLDS 2 validation across 8 categories including dark mode readiness
- **Wire Service Patterns**: @wire decorators for Apex & GraphQL data fetching
- **Jest Testing**: Comprehensive unit test generation with async patterns
- **Spring '26 Features**: TypeScript, lwc:on directive, GraphQL mutations, Agentforce discoverability
- **SLDS Linting**: 165-point SLDS 2 compliance and accessibility rubric

## Installation

For full installation instructions (various AI tools), see the [root README](../../../README.md).

## Quick Start

### 1. Invoke the skill

#### Installation

Invoke the unified skill:

```
/sf-lwc
/sf-lwc create datatable for Accounts
/sf-lwc validate myComponent
```

#### In other tools

```
Skill: sf-lwc
Request: "Create a data table component for Account records"
```

### 2. Answer requirements questions

The skill will ask about:

- Component purpose and target (App Page, Record Page, Flow Screen)
- Data source (LDS, Apex, GraphQL)
- Accessibility requirements
- Dark mode / SLDS 2 compliance needs

### 3. Review generated component

The skill generates:

- JavaScript controller with decorators and wire adapters
- HTML template with SLDS 2 styling
- CSS with styling hooks (dark mode ready)
- meta.xml with targets and property configuration
- Jest test file with async patterns

## PICKLES Framework

```
P → Prototype    │ Validate ideas with wireframes & mock data
I → Integrate    │ Choose data source (LDS, Apex, GraphQL, API)
C → Composition  │ Structure component hierarchy & communication
K → Kinetics     │ Handle user interactions & event flow
L → Libraries    │ Leverage platform APIs & base components
E → Execution    │ Optimize performance & lifecycle hooks
S → Security     │ Enforce permissions, FLS, and data protection
```

## Scoring System (165 Points)

| Category            | Points | Focus                             |
| ------------------- | ------ | --------------------------------- |
| Component Structure | 25     | File organization, naming         |
| Data Layer          | 25     | Wire service, error handling      |
| UI/UX               | 25     | SLDS 2, responsiveness, dark mode |
| Accessibility       | 20     | WCAG, ARIA, keyboard navigation   |
| Testing             | 20     | Jest coverage, async patterns     |
| Performance         | 20     | Lazy loading, debouncing          |
| Events              | 15     | Component communication           |
| Security            | 15     | FLS, permissions                  |

**Thresholds**: 150+ (Production-ready) | 100-149 (Minor issues) | <100 (Needs work)

## Templates

| Template                 | Use Case                        |
| ------------------------ | ------------------------------- |
| `basic-component/`       | Simple component starter        |
| `form-component/`        | Form with validation            |
| `datatable-component/`   | Data table with sorting         |
| `modal-component/`       | Modal dialog pattern            |
| `flow-screen-component/` | Flow screen integration         |
| `graphql-component/`     | GraphQL data binding            |
| `typescript-component/`  | TypeScript support (Spring '26) |
| `message-channel/`       | Lightning Message Service       |

## Validation

The skill includes validation scripts that check LWC components against a 165-point SLDS 2 rubric. Checks are **advisory** — they provide feedback but never block operations. Validation covers:

- **SLDS 2 compliance**: Valid class names, styling hooks, no deprecated SLDS 1 patterns
- **Accessibility**: ARIA labels/roles, alt-text, keyboard navigation
- **Dark mode readiness**: No hardcoded colors, CSS variables only
- **Template anti-patterns**: Catches common AI-generated mistakes like inline expressions, missing loop keys, and invalid ternary operators

Results appear as a scored report with a star rating and prioritised issue list. See the [For Contributors](#for-contributors) section for details on wiring up automated validation hooks.

## Cross-Skill Integration

| Related Skill | When to Use                       |
| ------------- | --------------------------------- |
| sf-apex       | Create @AuraEnabled controllers   |
| sf-flow       | Embed components in Flow screens  |
| sf-metadata   | Create Lightning Message Channels |
| sf-deploy     | Deploy component to org           |

## Spring '26 Features (API 66.0)

- **lwc:on directive**: Dynamic event binding from JavaScript
- **GraphQL Mutations**: `executeMutation` for create/update/delete
- **Complex Expressions**: JS expressions in templates (Beta)
- **TypeScript Support**: `@salesforce/lightning-types` package
- **Agentforce Discoverability**: `lightning__agentforce` capability

## Documentation

- [Component Patterns](references/component-patterns.md) — Wire, GraphQL, Modal, Navigation, TypeScript
- [LMS Guide](references/lms-guide.md) — Lightning Message Service deep dive
- [Jest Testing](references/jest-testing.md) — Advanced testing patterns
- [Accessibility Guide](references/accessibility-guide.md) — WCAG, ARIA, focus management
- [Performance Guide](references/performance-guide.md) — Dark mode, lazy loading, optimization
- [LWC Best Practices](assets/lwc-best-practices.md)
- [Flow Integration](assets/flow-integration-guide.md)
- [State Management](assets/state-management.md)
- [Template Anti-Patterns](assets/template-anti-patterns.md)

## Execution Modes

| Mode                      | When                                              | Speed   |
| ------------------------- | ------------------------------------------------- | ------- |
| `sfdx-repo`               | Working directory is an SFDX project              | Fastest |
| `cli`                     | Salesforce CLI installed and authed               | Fast    |
| `mcp-plus-code-execution` | MCP + filesystem + code execution (Cowork, Codex) | Medium  |
| `mcp-core`                | MCP only, no filesystem (chat interfaces)         | Slowest |

All LWC operations go through MCP tools regardless of mode. The mode
determines how large responses are handled and whether local tooling
(Jest, Node.js) is available.

## Requirements

- An AI coding tool with skill/plugin support
- Salesforce MCP server
- Target Salesforce org
- API Version 65.0+ (Winter '26), 66.0+ recommended (Spring '26)
- Node.js 18+ (for running Jest tests locally)

## For Contributors

### Validation Hooks

This skill ships Python validation scripts in `scripts/` for SLDS 2 compliance checking.

#### `post-tool-validate.py` — post-write (advisory, not wired by default)

Available for PostToolUse `Write|Edit` integration but **not currently registered** in `hooks/hooks.json`. When enabled, runs a two-phase SLDS 2 validation pipeline and outputs a scored report to the transcript.

**Phase 1 — `validate_slds.py`: SLDS 2 static analysis**

| Category            | Points | What it checks                                    |
| ------------------- | ------ | ------------------------------------------------- |
| SLDS Class Usage    | 25     | Valid `slds-*` class names, proper utility usage  |
| Accessibility       | 25     | ARIA labels/roles, alt-text, keyboard navigation  |
| Dark Mode Readiness | 25     | No hardcoded hex/RGB colors, CSS variables only   |
| SLDS Migration      | 20     | No deprecated SLDS 1 patterns or tokens           |
| Styling Hooks       | 20     | Proper `--slds-g-*` variable usage with fallbacks |
| Component Structure | 15     | Use of `lightning-*` base components              |
| Performance         | 10     | Efficient selectors, no `!important`              |
| PICKLES Compliance  | 25     | Architecture methodology adherence (optional)     |

**Phase 2 — `template_validator.py`: LWC template anti-pattern detection**

Catches mistakes AI models commonly make when generating LWC templates:

- **Inline expressions**: `{item.field + ' suffix'}` (not valid in LWC templates)
- **Ternary operators**: `{condition ? 'a' : 'b'}` (use getter or `lwc:if` instead)
- **Missing `key` on loops**: `for:each` without `key` attribute
- **Direct DOM access**: `document.querySelector` instead of `this.template.querySelector`
- **`@track` on primitives**: unnecessary in modern LWC

### Scripts

| Script                   | Purpose                                                     |
| ------------------------ | ----------------------------------------------------------- |
| `slds_linter_wrapper.py` | Wraps `@salesforce-ux/slds-linter` npm package if installed |
| `lwc-lsp-validate.py`    | LWC Language Server protocol validation                     |

## License

MIT License — see [LICENSE](LICENSE) for details.

For credits see [CREDITS](CREDITS.md)
