---
name: sf-lwc
plugin: salesforce-core-skills
argument-hint: '[create|update|validate] {ComponentName} ...'
metadata:
  version: 2.0.2
description: >
  Lightning Web Components development with PICKLES architecture methodology, component
  scaffolding, wire service patterns, event handling, Apex integration, GraphQL support,
  and Jest test generation. Powered by Salesforce MCP server for seamless metadata deployment.
  Usage: /sf-lwc [create|update|validate] {ComponentName} ...
---

# Salesforce Lightning Web Components

Expert frontend engineer specializing in Lightning Web Components for Salesforce. Generate production-ready LWC components using the **PICKLES Framework** for architecture, with proper data binding, Apex/GraphQL integration, event handling, SLDS 2 styling, and comprehensive Jest tests. Deploy components directly via **Salesforce MCP server** for seamless org integration.

## Dispatch

Parse `$ARGUMENTS` to determine which workflow to run:

| First argument or intent            | Workflow                               |
| ----------------------------------- | -------------------------------------- |
| `create`, new component request     | [Create LWC](#create-lwc-workflow)     |
| `update`, modify existing component | [Update LWC](#update-lwc-workflow)     |
| `validate`, review, score           | [Validate LWC](#validate-lwc-workflow) |
| _(no argument or unclear)_          | Ask the user (see below)               |

When the operation is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What would you like to do?\n\n1. **Create** — scaffold a new Lightning Web Component\n2. **Update** — fetch, modify, validate, and redeploy\n3. **Validate** — score an existing LWC")
```

Do NOT guess the operation or default to one. Wait for the user's answer.

## Execution modes

This skill supports four execution modes — see
`references/execution-modes.md` for detection logic and full details,
and `references/mcp-pagination.md` for handling large MCP responses.

All LWC operations go through MCP tools regardless of mode. The mode
determines whether local tooling (filesystem, Jest, code execution) is
available for post-processing and how large query results are retrieved.

---

## Source encoding rules (read this before any deploy/update)

Salesforce uses two different APIs for LWC source code, and they expect different encodings. Mixing them up produces errors like `XML parse error: Content is not allowed in prolog.: Source` or `Compilation` failures.

| API path                                                                           | Field                               | Encoding                         |
| ---------------------------------------------------------------------------------- | ----------------------------------- | -------------------------------- |
| Metadata API — `metadata_create` / `metadata_update` on `LightningComponentBundle` | `lwcResources.lwcResource[].source` | **Base64-encoded**               |
| Tooling API — `tooling_api_dml` on `LightningComponentResource`                    | `Source`                            | **Plain text** (NOT Base64)      |
| Tooling API — `tooling_api_query` on `LightningComponentResource`                  | `Source` (returned)                 | **Plain text** (already decoded) |

When falling back from `metadata_update` to per-file Tooling API edits (see [Tooling API fallback](#tooling-api-fallback--per-file-edits)), do not re-encode. The `Source` you read with `tooling_api_query` is the same plain text you write back with `tooling_api_dml`.

---

## Create LWC Workflow

Create a new Lightning Web Component following PICKLES architecture and Spring '26 best practices.

### 1. Gather requirements

Use AskUserQuestion to collect:

- **Component purpose**: one sentence description
- **Target placement**: App Page, Record Page, Home Page, or Flow Screen
- **Data source**: Lightning Data Service (LDS), Apex @wire, GraphQL, or none
- **Target object(s)** (if data-driven): which Salesforce objects
- **Special requirements**: dark mode, accessibility, LMS events, TypeScript, Agentforce discoverability, etc.

### 2. Check for existing component

Before generating, confirm nothing already exists with that name.

```
tooling_api_query(
  sObject="LightningComponentBundle",
  whereClause="DeveloperName = '<ComponentName>'",
  fields=["DeveloperName", "ApiVersion"]
)
```

If it already exists, suggest `update <ComponentName>` instead.

### 3. Generate the bundle

Apply the PICKLES framework from the sf-lwc skill. Generate all four files:

#### `<componentName>.html`

- SLDS 2 markup with `lightning-*` base components
- No hardcoded colors — use CSS styling hooks (`--slds-g-*` variables)
- Accessibility: ARIA labels/roles, keyboard navigation, `lwc:if` instead of ternary

#### `<componentName>.js`

- `@wire` decorators for data fetching (LDS or Apex)
- `@api` for parent→child props, `CustomEvent` for child→parent
- Error state handling for wire adapters
- No `@track` on primitives (unnecessary in modern LWC)

#### `<componentName>.css`

- CSS styling hooks only — no hardcoded hex or RGB values
- Dark mode ready via `--slds-g-*` variable fallbacks

#### `<componentName>.js-meta.xml`

- Correct `targets` for the intended placement
- `targetConfigs` with typed properties where applicable
- `isExposed: true` for App Builder drag-and-drop

### 4. Validate before deploying

Write each file to a temp directory and validate:

```bash
# Locate the validator
VALIDATOR=$(find ~/.claude/plugins -name "validate_slds.py" 2>/dev/null | grep sf-lwc | head -1)
# Or if CLAUDE_PLUGIN_ROOT is set:
# VALIDATOR="${CLAUDE_PLUGIN_ROOT}/skills/sf-lwc/scripts/validate_slds.py"

python3 "$VALIDATOR" "/tmp/<componentName>/<componentName>.html"
python3 "$VALIDATOR" "/tmp/<componentName>/<componentName>.css"
python3 "$VALIDATOR" "/tmp/<componentName>/<componentName>.js"
```

Fix any CRITICAL issues before proceeding. Advisory warnings can be noted in the report.

### 5. Deploy

```
metadata_create(
  type="LightningComponentBundle",
  metadata=[{
    "fullName": "<componentName>",
    "apiVersion": "66.0",
    "isExposed": true,
    "masterLabel": "<Component Label>",
    "lwcResources": {
      "lwcResource": [
        {"filePath": "lwc/<componentName>/<componentName>.js", "source": "<Base64-encoded JS>"},
        {"filePath": "lwc/<componentName>/<componentName>.html", "source": "<Base64-encoded HTML>"},
        {"filePath": "lwc/<componentName>/<componentName>.css", "source": "<Base64-encoded CSS>"}
      ]
    }
  }]
)
```

### 6. Report

Show the per-file validation scores and deployment status. If the component exposes `lightning__agentforce` capability, remind the user to add an agent action in Setup to make it discoverable.

---

## Update LWC Workflow

Fetch, modify, validate, and redeploy an existing Lightning Web Component.

### Parsing the request

The argument should be a component name followed by the requested changes: `update accountDashboard add a search filter` or `update contactCard fix dark mode colors`.

If no name is given, ask the user which component to update and what changes are needed.

### 1. Fetch the current bundle

```
metadata_read(
  type="LightningComponentBundle",
  fullNames=["c/<ComponentName>"]
)
```

If not found, suggest `create <ComponentName>` instead.

### 2. Read and understand

Review the existing files before making any changes. Understand:

- What the component currently does
- Existing SLDS classes, CSS variables, and styling patterns in use
- Wire adapters and data flow
- Event handling and component communication patterns
- What the requested change affects

### 3. Apply changes

Modify the relevant file(s) following sf-lwc skill guidelines:

- Preserve existing SLDS classes and wire patterns (update where relevant)
- Maintain accessibility attributes
- Do not introduce hardcoded colors — keep CSS hooks
- If changing `targets` in meta.xml, verify all existing placements remain valid

### 4. Validate before deploying

Write the modified file(s) to a temp directory and validate:

```bash
# Locate the validator
VALIDATOR=$(find ~/.claude/plugins -name "validate_slds.py" 2>/dev/null | grep sf-lwc | head -1)

# Validate each modified file (skip unchanged ones)
python3 "$VALIDATOR" "/tmp/<ComponentName>/<componentName>.html"
python3 "$VALIDATOR" "/tmp/<ComponentName>/<componentName>.css"
python3 "$VALIDATOR" "/tmp/<ComponentName>/<componentName>.js"
```

Fix any CRITICAL issues before proceeding.

### 5. Deploy

```
metadata_update(
  type="LightningComponentBundle",
  metadata=[{
    "fullName": "<ComponentName>",
    "apiVersion": "66.0",
    "isExposed": true,
    "masterLabel": "<Component Label>",
    "lwcResources": {
      "lwcResource": [
        {"filePath": "lwc/<ComponentName>/<ComponentName>.js", "source": "<Base64-encoded JS>"},
        {"filePath": "lwc/<ComponentName>/<ComponentName>.html", "source": "<Base64-encoded HTML>"},
        {"filePath": "lwc/<ComponentName>/<ComponentName>.css", "source": "<Base64-encoded CSS>"}
      ]
    }
  }]
)
```

> **If `metadata_update` reports a partial failure** (e.g. `had partial failures: All 1 operations failed`), do NOT retry the bundle-level call with the same payload. Switch to the [Tooling API fallback](#tooling-api-fallback--per-file-edits) and update one resource at a time with plain-text `Source`. Re-running `metadata_update` with the same content will reproduce the same failure.

### 6. Report

Summarise the changes made and show the final validation scores per file.

---

## Tooling API fallback — per-file edits

If `metadata_update` returns a partial failure or the bundle-level call is rejected (e.g. the `targetConfigs` validates differently against the org), you can update a single resource at a time via the Tooling API. **The `Source` field on this path is plain text — do NOT Base64-encode it.**

### 1. Resolve the bundle id and resource ids

```
tooling_api_query(
  sObject="LightningComponentBundle",
  fields=["Id", "DeveloperName"],
  whereClause="DeveloperName = '<ComponentName>'"
)

tooling_api_query(
  sObject="LightningComponentResource",
  fields=["Id", "FilePath", "Format", "Source"],
  whereClause="LightningComponentBundleId = '<bundleId>'"
)
```

`FilePath` is on `LightningComponentResource`, NOT on `LightningComponentBundle` — querying the latter for `FilePath` will fail with `No such column 'FilePath' on entity 'LightningComponentBundle'`.

### 2. Update one resource at a time

```
tooling_api_dml(
  operation="update",
  sObject="LightningComponentResource",
  record={
    "Id": "<resourceId>",
    "Source": "<plain-text source — NOT Base64>"
  }
)
```

Common mistakes that produce Salesforce errors on this path:

| Symptom                                                          | Cause                                               |
| ---------------------------------------------------------------- | --------------------------------------------------- |
| `XML parse error: Content is not allowed in prolog.: Source`     | You Base64-encoded the value before sending.        |
| `Compilation Failure` / `Unexpected token`                       | You Base64-encoded a JS or HTML resource.           |
| `No such column 'FilePath' on entity 'LightningComponentBundle'` | Queried `FilePath` on the bundle, not the resource. |

`*.js-meta.xml` is also a `LightningComponentResource` and is updated the same way (plain text). Use it to change bundle-level properties (apiVersion, isExposed, targets, targetConfigs) when `metadata_update` is unavailable.

### 3. Validate `*.js-meta.xml` content before writing

The `js-meta.xml` is XML that Salesforce validates strictly against the org's metadata. Common rejection causes:

| Salesforce error                        | Likely cause                                                                                                                     |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `No such relation 'X' on entity 'User'` | `userPermissions` referencing a permission name that doesn't exist in the org                                                    |
| `Invalid type: <name>` in `<targets>`   | Target not enabled / not available on this edition (e.g. `lightning__Dashboard` requires Salesforce Customer Support enablement) |
| `<targetConfigs>` parse / schema error  | `<targetConfig targets="...">` does not match an entry in the bundle's `<targets>`                                               |

Before sending the updated `js-meta.xml`:

- **Do not invent `userPermissions`**. If you need to gate visibility, use `tooling_api_query` on `PermissionSet` describes (or `soql_query` on `PermissionSetTabSetting` / known standard permissions) to confirm the name is real before referencing it. Standard SF user permissions (`ViewSetup`, `ManageUsers`, etc.) are safe; custom/named ones are not.
- **Each `<targetConfig targets="X">`** must reference a target that's also present in the bundle's `<targets>` block.
- **API version on `<apiVersion>`** must be one the org supports — query an existing component if unsure.

### 4. Listing many LWC components in large orgs

`metadata_list(type="LightningComponentBundle")` returns one record per component plus per-file properties and can exceed the per-call response cap in orgs with many LWCs (the response then gets paginated to a 3-record preview). For enumeration, prefer the lightweight Tooling API list:

```
tooling_api_query(
  sObject="LightningComponentBundle",
  fields=["Id", "DeveloperName", "NamespacePrefix", "ApiVersion", "MasterLabel", "Description"],
  whereClause="NamespacePrefix = null"
)
```

This returns just the bundle metadata (no embedded sources), is small, and uses the same plain-text path as the per-file edits above.

---

## Validate LWC Workflow

Validate one or more Lightning Web Components using the SLDS 2 static analysis pipeline and return a scored report.

### Parsing the request

| Input after `validate`                                                 | Interpretation                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------ |
| `accountDashboard`                                                     | Component name — fetch bundle from org, validate |
| `force-app/.../accountDashboard.html` (ends `.html`, `.css`, or `.js`) | Local file — validate directly                   |
| `accountDashboard,contactCard`                                         | Comma-separated list — bulk fetch, validate each |
| `All`                                                                  | All LightningComponentBundle records in the org  |
| _(no argument)_                                                        | Ask the user what to validate                    |

### Validation script

```bash
# $CLAUDE_PLUGIN_ROOT is set by Claude Code. Other hosts: see references/execution-modes.md.
# If not set, find the script:
VALIDATOR=$(find ~/.claude/plugins -name "validate_slds.py" 2>/dev/null | grep sf-lwc | head -1)
```

### Local file

```bash
python3 "$VALIDATOR" "<file_path>"
```

### Component name (fetch from org)

1. Fetch the component bundle:

```
metadata_read(
  type="LightningComponentBundle",
  fullNames=["c/<ComponentName>"]
)
```

If not found, tell the user the component was not found in the org.

2. Write the bundle files to a temp directory:

```
Write /tmp/validate_<ComponentName>/<componentName>.html
Write /tmp/validate_<ComponentName>/<componentName>.css
Write /tmp/validate_<ComponentName>/<componentName>.js
```

3. Validate each file:

```bash
python3 "$VALIDATOR" "/tmp/validate_<ComponentName>/<componentName>.html"
python3 "$VALIDATOR" "/tmp/validate_<ComponentName>/<componentName>.css"
python3 "$VALIDATOR" "/tmp/validate_<ComponentName>/<componentName>.js"
```

4. Delete the temp directory after validation.

5. Aggregate scores: sum the per-file scores and show a combined report with per-category breakdown.

### Comma-separated list

Fetch all bundles in individual `metadata_read` calls (LightningComponentBundle doesn't support bulk reads reliably):

```
metadata_read(type="LightningComponentBundle", fullNames=["c/<Name1>"])
metadata_read(type="LightningComponentBundle", fullNames=["c/<Name2>"])
```

Validate each bundle (write → validate → delete). After all are validated, show a summary table sorted by score ascending (worst first):

| Component     | HTML    | CSS     | JS      | Combined | Status             |
| ------------- | ------- | ------- | ------- | -------- | ------------------ |
| weakDashboard | 45/165  | 60/165  | 55/165  | avg 53%  | ❌ Below threshold |
| accountCard   | 140/165 | 155/165 | 148/165 | avg 90%  | ✅ Pass            |

### All

1. List all deployed components. Prefer the lightweight Tooling API query — `metadata_list` exceeds the per-call response cap in larger orgs and returns only a paginated preview:

```
tooling_api_query(
  sObject="LightningComponentBundle",
  fields=["Id", "DeveloperName", "MasterLabel", "ApiVersion"],
  whereClause="NamespacePrefix = null"
)
```

2. Fetch and validate each component bundle in batches of 10.

**Backoff strategy**: If a batch read fails, fall back to individual reads for that batch.

3. Validate each bundle (write → validate → delete).
4. Show the summary table sorted by combined score ascending.
5. Highlight any components averaging below 100/165 (61%) as requiring attention.

---

## Core Responsibilities

1. **Component Scaffolding**: Generate complete LWC bundles (JS, HTML, CSS, meta.xml)
2. **PICKLES Architecture**: Apply structured design methodology for robust components
3. **Wire Service Patterns**: Implement @wire decorators for data fetching (Apex & GraphQL)
4. **Apex/GraphQL Integration**: Connect LWC to backend with @AuraEnabled and GraphQL
5. **Event Handling**: Component communication (CustomEvent, LMS, pubsub)
6. **Lifecycle Management**: Proper use of connectedCallback, renderedCallback, etc.
7. **Jest Testing**: Generate comprehensive unit tests with advanced patterns
8. **Accessibility**: WCAG compliance with ARIA attributes, focus management
9. **Dark Mode**: SLDS 2 compliant styling with global styling hooks
10. **Performance**: Lazy loading, virtual scrolling, debouncing, efficient rendering
11. **the Salesforce MCP server Deployment**: Deploy via metadata_create with validation

---

## Salesforce MCP Integration

### Workflow

| Task                         | Original (CLI)                                        | New (the Salesforce MCP server)                                         |
| ---------------------------- | ----------------------------------------------------- | ------------------------------------------------------ |
| **Generate Component**       | `sf lightning generate component`                     | Generate files directly                                |
| **Deploy Component**         | `sf project deploy start -m LightningComponentBundle` | `metadata_create` with type "LightningComponentBundle" |
| **Query Component Metadata** | `sf data query --use-tooling-api`                     | `tooling_api_query` for LightningComponentBundle       |
| **Describe sObjects**        | `sf sobject describe Account`                         | `sobject_describe` tool                                |
| **SOQL Queries**             | `sf data query`                                       | `soql_query` tool                                      |
| **Run Jest Tests**           | `sf lightning lwc test run`                           | Jest runs locally; tests are code-generated            |

### Deployment Process

```
1. Generate LWC bundle files (JS, HTML, CSS, meta.xml)
   ↓
2. User reviews generated code (PICKLES + SLDS 2 validation)
   ↓
3. Call org_init() to authenticate with target org
   ↓
4. Call metadata_create with:
   - type: "LightningComponentBundle"
   - metadata: [{ fullName: "c/componentName", ...bundle files }]
   ↓
5. Component deployed to org
   ↓
6. Validation: tooling_api_query to verify LightningComponentBundle metadata
```

### MCP Tools Mapping

| Operation              | CLI Command                                           | MCP Tool             | Example                                                                              |
| ---------------------- | ----------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------ |
| Generate component     | `sf lightning generate component`                     | (generated directly) | Write JS/HTML/CSS/meta.xml directly                                                  |
| Deploy component       | `sf project deploy start -m LightningComponentBundle` | `metadata_create`    | `metadata_create(type="LightningComponentBundle", metadata=[...])`                   |
| Update component       | `sf project deploy` (existing)                        | `metadata_update`    | `metadata_update(type="LightningComponentBundle", metadata=[...])`                   |
| Retrieve component     | `sf project retrieve`                                 | `metadata_read`      | `metadata_read(type="LightningComponentBundle", fullNames=["c/accountDashboard"])`   |
| List components        | `sf metadata list`                                    | `metadata_list`      | `metadata_list(type="LightningComponentBundle")`                                     |
| Query metadata objects | `sf data query --use-tooling-api`                     | `tooling_api_query`  | `tooling_api_query(sObject="LightningComponentBundle", whereClause="...")`           |
| Describe sObject       | `sf sobject describe`                                 | `sobject_describe`   | `sobject_describe(sObject="Account")`                                                |
| Query data             | `sf data query`                                       | `soql_query`         | `soql_query(sObject="Account", fields=["Id","Name"], whereClause="Industry='Tech'")` |
| Delete component       | `sf project delete`                                   | `metadata_delete`    | `metadata_delete(type="LightningComponentBundle", fullNames=["c/accountDashboard"])` |

### Required Initialization

**ALWAYS start with**:

```
org_init()
```

Call with no parameters — uses the default org. If a default is configured, confirm with the user before proceeding. If no default is configured, ask for the Salesforce user/alias.

---

## Fast Path (Simple Requests)

For simple, self-contained components (static display, single-field input, basic wrapper, quick prototype), bypass the full PICKLES design methodology and 165-point scoring while still performing initialization and mandatory checks, then generate + deploy:

1. Call `org_init()` (always required)
2. Generate the LWC bundle (JS, HTML, CSS, meta.xml)
3. Run basic checks (accessibility attributes, no hardcoded colors)
4. Deploy via `metadata_create`
5. Verify deployment

**Use the fast path when**: the request is explicit, the component is self-contained with no complex data binding, and there are no ambiguous requirements.

**Use the full PICKLES workflow when**: the component involves Apex/GraphQL integration, complex state management, cross-component communication, or underspecified requirements.

---

## PICKLES Framework (Architecture Methodology)

The **PICKLES Framework** provides a structured approach to designing robust Lightning Web Components. Apply each principle during component design and implementation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     🥒 PICKLES FRAMEWORK                            │
├─────────────────────────────────────────────────────────────────────┤
│  P → Prototype    │  Validate ideas with wireframes & mock data    │
│  I → Integrate    │  Choose data source (LDS, Apex, GraphQL, API)  │
│  C → Composition  │  Structure component hierarchy & communication │
│  K → Kinetics     │  Handle user interactions & event flow         │
│  L → Libraries    │  Leverage platform APIs & base components      │
│  E → Execution    │  Optimize performance & lifecycle hooks        │
│  S → Security     │  Enforce permissions, FLS, and data protection │
└─────────────────────────────────────────────────────────────────────┘
```

### Quick Reference

| Principle           | Key Actions                                                                |
| ------------------- | -------------------------------------------------------------------------- |
| **P - Prototype**   | Wireframes, mock data, stakeholder review, separation of concerns          |
| **I - Integrate**   | LDS for single records, Apex for complex queries, GraphQL for related data |
| **C - Composition** | `@api` for parent→child, CustomEvent for child→parent, LMS for cross-DOM   |
| **K - Kinetics**    | Debounce search (300ms), disable during submit, keyboard navigation        |
| **L - Libraries**   | Use `lightning/*` modules, base components, avoid reinventing              |
| **E - Execution**   | Lazy load with `lwc:if`, cache computed values, avoid infinite loops       |
| **S - Security**    | `WITH SECURITY_ENFORCED`, input validation, FLS/CRUD checks                |

**For detailed PICKLES implementation patterns, see [references/component-patterns.md](references/component-patterns.md)**

---

## Key Component Patterns

### Wire vs Imperative Apex Calls

| Aspect           | Wire (@wire)            | Imperative Calls        |
| ---------------- | ----------------------- | ----------------------- |
| **Execution**    | Automatic / Reactive    | Manual / Programmatic   |
| **DML**          | ❌ Read-Only            | ✅ Insert/Update/Delete |
| **Data Updates** | ✅ Auto on param change | ❌ Manual refresh       |
| **Control**      | Low (framework decides) | Full (you decide)       |
| **Caching**      | ✅ Built-in             | ❌ None                 |

**Quick Decision**: Use `@wire` for read-only display with auto-refresh. Use imperative for user actions, DML, or when you need control over timing.

**For complete comparison with code examples and decision tree, see [references/component-patterns.md](references/component-patterns.md#wire-vs-imperative-apex-calls)**

### Data Source Decision Tree

| Scenario            | Recommended Approach                                   |
| ------------------- | ------------------------------------------------------ |
| Single record by ID | Lightning Data Service (`getRecord`)                   |
| Simple record CRUD  | `lightning-record-form` / `lightning-record-edit-form` |
| Complex queries     | Apex with `@AuraEnabled(cacheable=true)`               |
| Related records     | GraphQL wire adapter                                   |
| Real-time updates   | Platform Events / Streaming API                        |
| External data       | Named Credentials + Apex callout                       |

### Communication Patterns

| Pattern                   | Direction         | Use Case                |
| ------------------------- | ----------------- | ----------------------- |
| `@api` properties         | Parent → Child    | Pass data down          |
| Custom Events             | Child → Parent    | Bubble actions up       |
| Lightning Message Service | Any → Any         | Cross-DOM communication |
| Pub/Sub                   | Sibling → Sibling | Same page, no hierarchy |

### Communication Pattern Quick Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│              LWC COMMUNICATION - MADE SIMPLE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Parent → Child     │  [Parent] ─────→ [Child]   │  @api properties │
│                                                                     │
│  Child → Parent     │  [Child] ─────→ [Parent]   │  Custom Events   │
│                                                                     │
│  Sibling Components │  [A] → [Parent] → [B]      │  Events + @api   │
│                                                                     │
│  Unrelated          │  [Comp 1] ←─LMS─→ [Comp 2] │  Message Service │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Decision Tree**:

- Same parent? → Use parent as middleware (events up, `@api` down)
- Different DOM trees? → Use Lightning Message Service
- LWC ↔ Aura/VF? → Use Lightning Message Service

**For complete sibling communication code example, see [references/component-patterns.md](references/component-patterns.md#sibling-communication-via-parent)**

### Lifecycle Hook Guidance

| Hook                     | When to Use                     | Avoid                            |
| ------------------------ | ------------------------------- | -------------------------------- |
| `constructor()`          | Initialize properties           | DOM access (not ready)           |
| `connectedCallback()`    | Subscribe to events, fetch data | Heavy processing                 |
| `renderedCallback()`     | DOM-dependent logic             | Infinite loops, property changes |
| `disconnectedCallback()` | Cleanup subscriptions/listeners | Async operations                 |

**For complete code examples (Wire Service, GraphQL, Modal, Navigation, TypeScript), see:**

- [references/component-patterns.md](references/component-patterns.md) - Comprehensive patterns with full source code
- [references/lms-guide.md](references/lms-guide.md) - Lightning Message Service deep dive

---

## SLDS 2 Validation (165-Point Scoring)

The sf-lwc skill includes automated SLDS 2 validation that ensures dark mode compatibility, accessibility, and modern styling.

| Category                | Points | Key Checks                                        |
| ----------------------- | ------ | ------------------------------------------------- |
| **SLDS Class Usage**    | 25     | Valid class names, proper `slds-*` utilities      |
| **Accessibility**       | 25     | ARIA labels, roles, alt-text, keyboard navigation |
| **Dark Mode Readiness** | 25     | No hardcoded colors, CSS variables only           |
| **SLDS Migration**      | 20     | No deprecated SLDS 1 patterns/tokens              |
| **Styling Hooks**       | 20     | Proper `--slds-g-*` variable usage                |
| **Component Structure** | 15     | Uses `lightning-*` base components                |
| **Performance**         | 10     | Efficient selectors, no `!important`              |
| **PICKLES Compliance**  | 25     | Architecture methodology adherence (optional)     |

**Scoring Thresholds**:

```
✅ 150-165 pts → Production-ready, full SLDS 2 + Dark Mode
⚠️ 100-149 pts → Good component, minor styling issues to address
❌  <100 pts   → Needs significant SLDS 2 cleanup before deploy
```

**Exemption for trivial components**: Simple display components, wrappers, and prototypes are exempt from the <100 block threshold. Score them for informational purposes but do not block deployment. Basic accessibility and dark mode checks still apply regardless of complexity.

**CLI usage**: `validate_slds.py` validates a **single file** (not a directory):

```bash
python scripts/validate_slds.py path/to/component.html    # Human-readable report
python scripts/validate_slds.py path/to/component.css      # CSS validation
python scripts/validate_slds.py path/to/component.js       # JS validation
python scripts/validate_slds.py path/to/component.html --json  # JSON output
```

> **Note**: The local SLDS validator catches styling and pattern issues but cannot detect server-side compile errors (e.g. invalid component references like `lightning-formatted-phone-number` or inaccessible schema imports). Always verify deployment succeeds after local validation passes.

---

## Dark Mode Readiness

Dark mode is exclusive to SLDS 2 themes. Components must use global styling hooks to support light/dark theme switching.

### Dark Mode Checklist

- [ ] **No hardcoded hex colors** (`#FFFFFF`, `#333333`)
- [ ] **No hardcoded RGB/RGBA values**
- [ ] **All colors use CSS variables** (`var(--slds-g-color-*)`)
- [ ] **Fallback values provided** for SLDS 1 compatibility
- [ ] **No inline color styles** in HTML templates
- [ ] **Icons use SLDS utility icons** (auto-adjust for dark mode)

### Global Styling Hooks (Common)

| Category      | SLDS 2 Variable                              | Purpose                  |
| ------------- | -------------------------------------------- | ------------------------ |
| **Surface**   | `--slds-g-color-surface-1` to `-4`           | Background colors        |
| **Container** | `--slds-g-color-surface-container-1` to `-3` | Card/section backgrounds |
| **Text**      | `--slds-g-color-on-surface`                  | Primary text             |
| **Border**    | `--slds-g-color-border-1`, `-2`              | Borders                  |
| **Brand**     | `--slds-g-color-brand-1`, `-2`               | Brand accent             |
| **Spacing**   | `--slds-g-spacing-0` to `-12`                | Margins/padding          |

**Example Migration**:

```css
/* SLDS 1 (Deprecated) */
.my-card {
  background-color: #ffffff;
  color: #333333;
}

/* SLDS 2 (Dark Mode Ready) */
.my-card {
  background-color: var(--slds-g-color-surface-container-1, #ffffff);
  color: var(--slds-g-color-on-surface, #181818);
}
```

**For complete styling hooks reference and migration guide, see [references/performance-guide.md](references/performance-guide.md)**

---

## Jest Testing

Advanced testing patterns ensure robust, maintainable components. Tests are generated alongside component code.

### Essential Patterns

```javascript
// Render cycle helper
const runRenderingLifecycle = async (reasons = ['render']) => {
  while (reasons.length > 0) {
    await Promise.resolve(reasons.pop());
  }
};

// DOM cleanup
afterEach(() => {
  while (document.body.firstChild) {
    document.body.removeChild(document.body.firstChild);
  }
  jest.clearAllMocks();
});

// Proxy unboxing (LWS compatibility)
const unboxedData = JSON.parse(JSON.stringify(component.data));
expect(unboxedData).toEqual(expectedData);
```

### Test Template Structure

```javascript
import { createElement } from 'lwc';
import MyComponent from 'c/myComponent';
import getData from '@salesforce/apex/MyController.getData';

jest.mock(
  '@salesforce/apex/MyController.getData',
  () => ({
    default: jest.fn(),
  }),
  { virtual: true }
);

describe('c-my-component', () => {
  afterEach(() => {
    /* DOM cleanup */
  });

  it('displays data when loaded successfully', async () => {
    getData.mockResolvedValue(MOCK_DATA);
    const element = createElement('c-my-component', { is: MyComponent });
    document.body.appendChild(element);
    await runRenderingLifecycle();
    // Assertions...
  });
});
```

**For complete testing patterns (ResizeObserver polyfill, advanced mocks, event testing), see [references/jest-testing.md](references/jest-testing.md)**

### Local Test Execution

```bash
# All tests
npm run test

# Specific component
npm run test -- accountList

# With coverage
npm run test:coverage
```

---

## Accessibility

WCAG compliance is mandatory for all components.

### Quick Checklist

| Requirement      | Implementation                                          |
| ---------------- | ------------------------------------------------------- |
| **Labels**       | `label` on inputs, `aria-label` on icons                |
| **Keyboard**     | Enter/Space triggers, Tab navigation                    |
| **Focus**        | Visible indicator, logical order, focus traps in modals |
| **Live Regions** | `aria-live="polite"` for dynamic content                |
| **Contrast**     | 4.5:1 minimum for text                                  |

```html
<!-- Accessible dynamic content -->
<div aria-live="polite" class="slds-assistive-text">{statusMessage}</div>
```

**For comprehensive accessibility guide (focus management, ARIA patterns, screen reader testing), see [references/accessibility-guide.md](references/accessibility-guide.md)**

---

## Metadata Configuration

### meta.xml Targets

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>Account Dashboard</masterLabel>
    <description>SLDS 2 compliant account dashboard with dark mode support</description>
    <targets>
        <target>lightning__RecordPage</target>
        <target>lightning__AppPage</target>
        <target>lightning__HomePage</target>
        <target>lightning__FlowScreen</target>
        <target>lightningCommunity__Page</target>
        <target>lightning__Dashboard</target> <!-- Spring '26 Beta -->
    </targets>
    <targetConfigs>
        <targetConfig targets="lightning__RecordPage">
            <objects>
                <object>Account</object>
            </objects>
            <property name="title" type="String" default="Dashboard"/>
            <property name="maxRecords" type="Integer" default="10"/>
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

---

## Deployment via MCP

### Step 1: Initialize & Generate

**FIRST**: Call `org_init`:

```
Use: org_init()
```

If you need to override the default connection, pass your MCP server's org/user connection parameters explicitly.

Then generate the LWC bundle:

```
User: "Generate an accountDashboard LWC component for displaying account metrics"

Agent:
1. Generates accountDashboard.js (with @wire, event handling)
2. Generates accountDashboard.html (SLDS 2 structure)
3. Generates accountDashboard.css (dark mode variables)
4. Generates accountDashboard.meta.xml (targets and config)
5. Generates accountDashboard.test.js (Jest tests)
6. Validates against PICKLES framework (165-point score: ~155 pts)
7. Shows code preview to user
```

### Step 2: Deploy via metadata_create

The `metadata_create` call requires a flat metadata structure with **Base64-encoded** sources in `lwcResources`:

```
metadata_create(
  type="LightningComponentBundle",
  metadata=[{
    "fullName": "accountDashboard",
    "apiVersion": "66.0",
    "isExposed": true,
    "masterLabel": "Account Dashboard",
    "description": "SLDS 2 compliant account metrics dashboard",
    "lwcResources": {
      "lwcResource": [
        {
          "filePath": "lwc/accountDashboard/accountDashboard.js",
          "source": "<Base64-encoded JS source>"
        },
        {
          "filePath": "lwc/accountDashboard/accountDashboard.html",
          "source": "<Base64-encoded HTML source>"
        },
        {
          "filePath": "lwc/accountDashboard/accountDashboard.css",
          "source": "<Base64-encoded CSS source>"
        }
      ]
    }
  }]
)
```

> **Encoding note**: `metadata_create` and `metadata_update` require **Base64-encoded** source files in `lwcResources.lwcResource[].source`. When updating an existing component via `tooling_api_dml` on `LightningComponentResource.Source`, use **plain text** (NOT Base64). This is an intentional Salesforce API difference between the Metadata API and Tooling API. See [Source encoding rules](#source-encoding-rules-read-this-before-any-deployupdate) at the top of this skill for the full reference.

### Step 3: Verify Deployment

```
tooling_api_query(
  sObject="LightningComponentBundle",
  whereClause="DeveloperName = 'accountDashboard'"
)
```

---

## Code Generation Examples

### Example 1: Wire Service Component

**Request**: "Create an account list component that loads accounts using Apex wire service"

**Generated: accountList.js**

```javascript
import { LightningElement, wire, api } from 'lwc';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

export default class AccountList extends LightningElement {
  @api maxRecords = 10;
  accounts;
  error;
  isLoading = true;

  @wire(getAccounts, { maxRecords: '$maxRecords' })
  wiredAccounts(result) {
    if (result.data) {
      this.accounts = result.data;
      this.error = undefined;
    } else if (result.error) {
      this.error = result.error;
      this.accounts = undefined;
    }
    this.isLoading = false;
  }
}
```

**Generated: accountList.html**

```html
<template>
  <lightning-card title="Accounts" icon-name="standard:account">
    <template lwc:if="{isLoading}">
      <lightning-spinner variant="brand"></lightning-spinner>
    </template>

    <template lwc:else-if="{accounts}">
      <div class="slds-m-around_medium">
        <div class="slds-table slds-table_striped slds-table_bordered">
          <template for:each="{accounts}" for:item="account">
            <div key="{account.Id}" class="slds-truncate">{account.Name}</div>
          </template>
        </div>
      </div>
    </template>

    <template lwc:else-if="{error}">
      <div class="slds-notify slds-notify_alert slds-theme_alert-danger">{error.body.message}</div>
    </template>
  </lightning-card>
</template>
```

**Generated: accountList.css**

```css
:host {
  --slds-g-color-surface-1: var(--slds-c-card-color-background, #ffffff);
}

.slds-table {
  background-color: var(--slds-g-color-surface-1);
  color: var(--slds-g-color-on-surface);
}
```

### Example 2: Custom Event Communication

**Request**: "Create a parent-child component pair with custom event communication"

**Generated: parentComponent.js**

```javascript
import { LightningElement, track } from 'lwc';

export default class ParentComponent extends LightningElement {
  @track selectedAccountId;

  handleAccountSelection(event) {
    this.selectedAccountId = event.detail.id;
  }
}
```

**Generated: childAccountSelector.js**

```javascript
import { LightningElement } from 'lwc';

export default class ChildAccountSelector extends LightningElement {
  handleSelect(event) {
    const selectedId = event.currentTarget.dataset.id;
    this.dispatchEvent(
      new CustomEvent('accountselected', {
        detail: { id: selectedId },
      })
    );
  }
}
```

---

## Flow Screen Integration

LWC components can be embedded in Flow Screens for custom UI experiences within guided processes.

### Key Concepts

| Mechanism                      | Direction  | Purpose                       |
| ------------------------------ | ---------- | ----------------------------- |
| `@api` with `role="inputOnly"` | Flow → LWC | Pass context data             |
| `FlowAttributeChangeEvent`     | LWC → Flow | Return user selections        |
| `FlowNavigationFinishEvent`    | LWC → Flow | Programmatic Next/Back/Finish |
| `availableActions`             | Flow → LWC | Check available navigation    |

### Quick Example

```javascript
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';

@api recordId;           // Input from Flow
@api selectedRecordId;   // Output to Flow
@api availableActions = [];

handleSelect(event) {
    this.selectedRecordId = event.detail.id;
    // CRITICAL: Notify Flow of the change
    this.dispatchEvent(new FlowAttributeChangeEvent(
        'selectedRecordId',
        this.selectedRecordId
    ));
}

handleNext() {
    if (this.availableActions.includes('NEXT')) {
        this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
    }
}
```

**For complete Flow integration patterns, see:**

- [assets/flow-integration-guide.md](assets/flow-integration-guide.md)
- [assets/triangle-pattern.md](assets/triangle-pattern.md)

---

## Advanced Features

### TypeScript Support (Spring '26 - GA in API 66.0)

Lightning Web Components now support TypeScript with the `@salesforce/lightning-types` package.

```typescript
interface AccountRecord {
  Id: string;
  Name: string;
  Industry?: string;
}

export default class AccountList extends LightningElement {
  @api recordId: string | undefined;
  @track private _accounts: AccountRecord[] = [];

  @wire(getAccounts, { maxRecords: '$maxRecords' })
  wiredAccounts(result: WireResult<AccountRecord[]>): void {
    // Typed wire handling...
  }
}
```

**Requirements**: TypeScript 5.4.5+, `@salesforce/lightning-types` package

### LWC in Dashboards (Beta - Spring '26)

Components can be embedded as custom dashboard widgets.

```xml
<targets>
    <target>lightning__Dashboard</target>
</targets>
<targetConfigs>
    <targetConfig targets="lightning__Dashboard">
        <property name="metricType" type="String" label="Metric Type"/>
        <property name="refreshInterval" type="Integer" default="30"/>
    </targetConfig>
</targetConfigs>
```

**Note**: Requires enablement via Salesforce Customer Support

### Agentforce Discoverability (Spring '26 - GA in API 66.0)

Make components discoverable by Agentforce agents:

```xml
<capabilities>
    <capability>lightning__agentforce</capability>
</capabilities>
```

**Best Practices**:

- Clear `masterLabel` and `description`
- Detailed property descriptions
- Semantic naming conventions

**For TypeScript patterns and advanced configurations, see [references/component-patterns.md](references/component-patterns.md)**

---

## Cross-Skill Integration

| Skill       | Use Case                                                       |
| ----------- | -------------------------------------------------------------- |
| sf-apex     | Generate Apex controllers (`@AuraEnabled`, `@InvocableMethod`) |
| sf-flow     | Embed components in Flow Screens, pass data to/from Flow       |
| sf-data     | SOQL queries and test data for component development           |
| sf-metadata | Create LWC message channels                                    |

---

## Limitations & Workarounds

| Feature                     | CLI Support                                           | MCP Support                              | Workaround                                      |
| --------------------------- | ----------------------------------------------------- | ---------------------------------------- | ----------------------------------------------- |
| Local file scaffolding      | `sf lightning generate component`                     | ❌ Not available                         | Generate code as strings, write via Edit        |
| Automatic file sync         | `force-app/main/default/lwc/`                         | ❌ Not available                         | Generate as strings, deploy via metadata_create |
| LWC Jest runner             | `sf lightning lwc test run`                           | ❌ Not available                         | Run `npm run test` locally                      |
| Component metadata deploy   | `sf project deploy start -m LightningComponentBundle` | ✅ `metadata_create` / `metadata_update` | Full support via MCP                            |
| Component metadata retrieve | `sf project retrieve`                                 | ✅ `metadata_read`                       | Full support via MCP                            |
| List deployed components    | `sf metadata list`                                    | ✅ `metadata_list`                       | Full support via MCP                            |

---

## Dependencies

**Required**:

- Salesforce MCP server connection (via `org_init`)
- Target org with LWC support (API 45.0+)

**For Testing**:

- Node.js 18+
- Jest (`@salesforce/sfdx-lwc-jest`)

**For SLDS Validation**:

- `@salesforce-ux/slds-linter` (optional)

---

## Additional Resources

### Documentation Files

| Resource                                                                       | Purpose                                                               |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| [references/component-patterns.md](references/component-patterns.md)           | Complete code examples (Wire, GraphQL, Modal, Navigation, TypeScript) |
| [references/lms-guide.md](references/lms-guide.md)                             | Lightning Message Service deep dive                                   |
| [references/jest-testing.md](references/jest-testing.md)                       | Advanced testing patterns (James Simone)                              |
| [references/accessibility-guide.md](references/accessibility-guide.md)         | WCAG compliance, ARIA patterns, focus management                      |
| [references/performance-guide.md](references/performance-guide.md)             | Dark mode migration, lazy loading, optimization                       |
| [assets/state-management.md](assets/state-management.md)                       | @track, Singleton Store, @lwc/state, Platform State Managers          |
| [assets/template-anti-patterns.md](assets/template-anti-patterns.md)           | LLM template mistakes (inline expressions, ternary operators)         |
| [assets/async-notification-patterns.md](assets/async-notification-patterns.md) | Platform Events + empApi subscription patterns                        |
| [assets/flow-integration-guide.md](assets/flow-integration-guide.md)           | Flow-LWC communication, apex:// type bindings                         |
| [assets/triangle-pattern.md](assets/triangle-pattern.md)                       | Triangle pattern for LWC component design                             |

### External References

- [PICKLES Framework (Salesforce Ben)](https://www.salesforceben.com/the-ideal-framework-for-architecting-salesforce-lightning-web-components/)
- [LWC Recipes (GitHub)](https://github.com/trailheadapps/lwc-recipes)
- [SLDS 2 Transition Guide](https://www.lightningdesignsystem.com/2e1ef8501/p/8184ad-transition-to-slds-2)
- [SLDS Styling Hooks](https://developer.salesforce.com/docs/platform/lwc/guide/create-components-css-custom-properties.html)
- [James Simone - Composable Modal](https://www.jamessimone.net/blog/joys-of-apex/lwc-composable-modal/)
- [James Simone - Advanced Jest Testing](https://www.jamessimone.net/blog/joys-of-apex/advanced-lwc-jest-testing/)

---

## License

See [LICENSE](LICENSE)
