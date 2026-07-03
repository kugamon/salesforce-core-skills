---
name: sf-flow
plugin: salesforce-core
argument-hint: '[create|update|validate] {FlowName} ...'
metadata:
  version: 2.2.0
description: >
  Creates and validates Salesforce flows with 110-point scoring and Winter '26 best practices
  using Salesforce MCP server. Use when building record-triggered flows, screen flows,
  autolaunched flows, scheduled flows, or reviewing existing flow performance.
  Usage: /sf-flow [create|update|validate] {FlowName} ...
---

# Salesforce Flow Development and Review

Expert Salesforce Flow Builder with deep knowledge of best practices, bulkification, and Winter '26 (API 65.0) metadata. Create production-ready, performant, secure, and maintainable flows using Salesforce MCP server for deployment.

## Dispatch

Parse `$ARGUMENTS` to determine the action:

| First argument or intent       | Workflow                 |
| ------------------------------ | ------------------------ |
| `create`, new flow request     | Create Flow              |
| `update`, modify existing flow | Update Flow              |
| `validate`, review, score      | Validate Flow            |
| _(no argument or unclear)_     | Ask the user (see below) |

When the operation is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What would you like to do?\n\n1. **Create** — generate a new Flow\n2. **Update** — fetch, modify, validate, and redeploy\n3. **Validate** — score an existing Flow")
```

Do NOT guess the operation or default to one. Wait for the user's answer.

---

## Approval Processes: Choose the Engine First

When a request is to build an approval (e.g. "create an approval process", "require approval before X", "deal/discount approval", "gate a stage until approved"), do NOT start building until the **engine** is decided:

| Engine                                        | Build with                                                                                                  | Use when                                                                                                                                                                 |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Flow Approval Orchestration** (recommended) | this skill (`processType` Orchestrator, record-triggered) + the Setup approval wizard for the approval step | Default. Salesforce's active investment; native record-change auto-trigger; Approval Trace audit log; recall/reassign; Apex-extensible; free (no orchestration credits). |
| **Legacy (classic) Approval Process**         | `sf-metadata` (`ApprovalProcess` metadata type)                                                             | Simple single-step manager approvals; need built-in **delegate approver**; org already standardized on classic.                                                          |

**If the user has not explicitly named the engine, ASK (one question) and recommend Flow Approval Orchestration.** Do not default silently.

```
AskUserQuestion(question="Build this as a **Flow Approval Orchestration** (recommended — record-change auto-trigger, audit trace, Salesforce's strategic direction) or a **legacy Approval Process** (simpler, built-in delegate approver)?")
```

**Set expectations up front (true for BOTH engines):**

- An approval process cannot _prevent_ a field transition by itself. To gate (e.g. block `Closed Won` until approved) you ALSO need a **validation rule** keyed off either a custom "approved" flag (set by a final-approval field update / background step) or `PRIORVALUE(StageName)`.
- Auto-trigger on record change is **native** to Flow record-triggered orchestrations; classic needs a separate record-triggered auto-submit flow.
- The orchestration's **approval step** subtype does not reliably round-trip through the Metadata API — assemble that step in the Setup approval wizard / Flow Builder. Build the supporting **approver screen flow** and **background field-update flow** with this skill, then wire them in the wizard.

### Minimize metadata round-trips

- **Read before update** for any element the API replaces wholesale (`Layout`, `ApprovalProcess`, `StandardValueSet`, `Flow`): fetch current → change the one field → send the complete payload. A partial payload silently drops siblings.
- **Use exact metadata element names** — do not infer them from the Setup UI label. Known mismatches: `recordEditability` (NOT `recordEditabilityType`); the "Submit for Approval" standard button is `Submit` inside `excludeButtons`; OpportunityStage values are governed by `won`/`closed`/`forecastCategory`, not just `label`.
- **Batch** field/criteria reads into one `soql_query` / `metadata_read` instead of one call per item.
- Prefer the surgical tool where one exists (`page_layout_update` / `permission_set_update` JSON-Patch) over a full `metadata_update` rebuild.

---

## Action Workflow: Create Flow

Create a new Flow following Winter '26 best practices.

### Step 1. Gather requirements

Use AskUserQuestion to collect:

- **Flow type**: Record-Triggered, Screen, Autolaunched, Scheduled, or Platform Event-Triggered
- **Trigger object** (if record-triggered): which Salesforce object
- **Trigger event** (if record-triggered): before save, after save, or both
- **Primary purpose**: one sentence description
- **Special requirements**: subflows, invocable actions, external callouts, etc.

### Step 2. Check for existing flow

Before generating, confirm the flow doesn't already exist:

```
metadata_list(
  type="Flow",
  sf_user="<sf_user>"
)
```

If it exists, suggest running with `update <FlowApiName>` instead.

### Step 3. Generate

Create the flow XML following the sf-flow skill guidelines (see Workflow Design section below):

- Proper API naming conventions (snake_case with descriptive prefix)
- Fault paths on all DML and callout elements
- Bulkification patterns (no DML or SOQL in loops)
- Description and labels on all elements
- `runInMode="SystemModeWithoutSharing"` only where justified

### Step 4. Validate before deploying — REQUIRED, MANUAL

> **This step is not optional and is not automated.** Skipping it has shipped Flows with broken email actions, missing fault paths, and `InvalidDraft` states that only surface at runtime. A skill-scoped `PreToolUse` hook (`scripts/pre-mcp-validate.py`) ships with this skill, but **it is not wired up in every runtime environment** — until you confirm the hook is registered for your host, treat the manual step below as the contract.

Write the generated metadata to a temp file (`/tmp/<FlowApiName>.flow-meta.xml` for XML, `/tmp/<FlowApiName>.flow.json` for JSON), then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/sf-flow/scripts/validate_flow_cli.py" "/tmp/<FlowApiName>.flow-meta.xml"
```

Fix any **CRITICAL** or **HIGH** issues before deploying — including missing `faultConnector` on `actionCalls`, `recordCreates`, `recordUpdates`, `recordDeletes`, `recordLookups`, `apexPluginCalls`, and `waits` with callouts. A score below 80% (88/110) is a hard stop unless you explicitly state in your response why the deployment is going ahead anyway.

**Self-check before every `metadata_create` / `metadata_update` / `tooling_api_dml` call on a Flow.** Answer these four questions out loud (in your reasoning) before invoking the tool:

1. Did I write the Flow metadata to a file?
2. Did I run `validate_flow_cli.py` on that file?
3. Did the validator output appear in my context, with a score and an issue list?
4. Are all CRITICAL/HIGH issues resolved?

If you cannot answer "yes" to all four, do not call the deployment tool. Stop, run the validator, and resume.

**Default fault-routing rule for every Flow.** Every element that can fault at runtime needs a `faultConnector`: every `actionCalls` (email, callout, invocable Apex), every `recordCreates` / `recordUpdates` / `recordDeletes` / `recordLookups`, every `apexPluginCalls`, and every `waits` involving a callout. Routing the fault to a no-op terminal element is acceptable; routing it to the success path is not (it hides failures).

### Step 5. Deploy

```
metadata_create(
  type="Flow",
  metadata=[{"fullName": "<FlowApiName>", "label": "<Flow Label>", "apiVersion": 65, "processType": "<ProcessType>", "status": "Draft", ...}]
)
```

### Step 6. Report

Show the final validation score and deployment status.

---

## Action Workflow: Update Flow

Fetch, modify, validate, and redeploy an existing Salesforce Flow.

### Parsing the request

The argument should be a flow API name: `update Auto_Lead_Assignment do X`

If no flow name is given, ask the user which flow to update and what changes are needed.

### Step 1. Fetch the current implementation

```
metadata_read(
  type="Flow",
  fullNames=["<FlowApiName>"],
  sf_user="<sf_user>"
)
```

If the flow is not found, suggest running with `create` instead.

### Step 2. Read and understand

Review the existing flow XML before making any changes. Understand:

- Flow type and trigger configuration
- Existing element names and labels
- What the requested change affects

### Step 3. Apply changes

Modify the flow following sf-flow skill guidelines. Preserve:

- Existing element names and API references (other flows/components may reference them)
- Existing fault paths and error handling
- Description and label conventions already in use

### Step 4. Validate before deploying — REQUIRED, MANUAL

The same four-question self-check from the **Create** workflow applies here. The hook is not guaranteed to be wired up; the manual validator run is the contract. Write the updated metadata to a temp file and validate:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/sf-flow/scripts/validate_flow_cli.py" "/tmp/<FlowApiName>.flow-meta.xml"
```

Fix any CRITICAL or HIGH issues before deploying. Score below 80% (88/110) is a hard stop unless you can explain why the deployment is going ahead anyway.

### Step 5. Deploy

```
metadata_update(
  type="Flow",
  metadata=[{"fullName": "<FlowApiName>", "label": "<Flow Label>", "apiVersion": 65, "processType": "<ProcessType>", "status": "Draft", ...}]
)
```

### Step 6. Report

Summarise the changes made and show the final validation score.

---

## Action Workflow: Validate Flow

Validate one or more Flows using the 110-point static analysis pipeline and return a scored report.

### Parsing the request

| Input after `validate`                                                               | Interpretation                                   |
| ------------------------------------------------------------------------------------ | ------------------------------------------------ |
| `Auto_Lead_Assignment`                                                               | Flow API name — fetch XML from org, validate     |
| `force-app/.../Auto_Lead_Assignment.flow-meta.xml` (ends `.flow-meta.xml` or `.xml`) | Local file — validate directly                   |
| `Auto_Lead_Assignment,Screen_Case_Intake`                                            | Comma-separated list — bulk fetch, validate each |
| `All`                                                                                | All Flow records in the org                      |
| _(no argument)_                                                                      | Ask the user what to validate                    |

### Validation script

The validation script is at `${CLAUDE_PLUGIN_ROOT}/skills/sf-flow/scripts/validate_flow_cli.py`. Locate it with:

```bash
# $CLAUDE_PLUGIN_ROOT is set by Claude Code. Other hosts: see references/execution-modes.md.
# If not set, find the script:
find ~/.claude/plugins -name "validate_flow_cli.py" 2>/dev/null | grep sf-flow | head -1
```

### Local file

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/sf-flow/scripts/validate_flow_cli.py" "<file_path>"
```

### Flow API name (fetch from org)

1. Fetch the Flow XML:

```
metadata_read(
  type="Flow",
  fullNames=["<FlowApiName>"],
  sf_user="<sf_user>"
)
```

2. Write the XML content to a temp file:

```
Write /tmp/validate_<FlowApiName>.flow-meta.xml  ← the flow XML
```

3. Validate:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/sf-flow/scripts/validate_flow_cli.py" "/tmp/validate_<FlowApiName>.flow-meta.xml"
```

4. Delete the temp file after validation.

### Comma-separated list

Fetch all flow XML bodies in a single call:

```
metadata_read(
  type="Flow",
  fullNames=["Flow1", "Flow2", "Flow3"],
  sf_user="<sf_user>"
)
```

**Fallback**: If the bulk read fails (timeout or size error), fall back to individual `metadata_read` calls per flow.

Validate each flow body (write → validate → delete). After all flows are validated, show a summary table sorted by score ascending (worst first):

| Flow                        | Score  | %   | Status          |
| --------------------------- | ------ | --- | --------------- |
| Before_Opportunity_Validate | 72/110 | 65% | Below threshold |
| Auto_Lead_Assignment        | 98/110 | 89% | Pass            |

### All

1. Fetch all flow names:

```
metadata_list(type="Flow", sf_user="<sf_user>")
```

2. Fetch flow XML in batches of 20 (large flows can make bigger batches fail):

```
metadata_read(
  type="Flow",
  fullNames=["Flow1", ..., "Flow20"],
  sf_user="<sf_user>"
)
```

**Backoff strategy**: If a batch of 20 fails (timeout or response size error), retry with 10, then 5, then fall back to individual reads for that batch.

3. Validate each flow (write → validate → delete).
4. Show the summary table sorted by score ascending.
5. Highlight any below 88/110 (80%) as requiring attention.

---

## 📋 Quick Reference: Validation and Deployment

**Flow Creation & Deployment Workflow:**

```text
1. Call org_init (REQUIRED - one per session)
2. Generate Flow metadata (JSON object — NOT XML)
3. Deploy via metadata_create tool (Salesforce MCP server)
4. Retrieve existing flows via metadata_read or metadata_list (Salesforce MCP server)
5. Query Flow metadata via tooling_api_query for FlowDefinition
6. Describe objects/fields via sobject_describe before flow creation
```

**Scoring**: 110 points across 6 categories. Minimum 88 (80%) for deployment. Trivial flows (single-step automations, test/throwaway flows) are exempt from the minimum threshold — score them for informational purposes but do not block deployment. Guardrail anti-pattern checks (DML in loops, missing fault paths) still apply regardless of complexity.

---

## Execution modes

This skill supports four execution modes — see
`references/execution-modes.md` for detection logic and full details,
and `references/mcp-pagination.md` for handling large MCP responses.

All Flow operations go through MCP tools regardless of mode. The mode
determines whether local tooling (filesystem, code execution) is
available for post-processing and how large query results are retrieved.

---

## Core Responsibilities

1. **Flow Generation**: Create well-structured Flow metadata (JSON) from requirements
2. **Strict Validation**: Enforce best practices with comprehensive checks and scoring
3. **the Salesforce MCP server Integration**: Deploy via metadata_create, retrieve via metadata_read/metadata_list
4. **Testing Guidance**: Provide type-specific testing checklists and verification steps

---

## ⚠️ CRITICAL: Salesforce MCP server Setup

**BEFORE using any Salesforce MCP tools:**

```python
org_init()
```

Call with no parameters — uses the default org. If a default is configured, confirm with the user before proceeding. If no default is configured, ask for the Salesforce user/alias.

This initializes your Salesforce org connection. It must be called once per session before using any of these Salesforce MCP tools:

- `metadata_create` (deploy flows)
- `metadata_read` (retrieve flows)
- `metadata_list` (list existing flows)
- `tooling_api_query` (query FlowDefinition)
- `sobject_describe` (verify objects/fields)
- `soql_query` (query org data)

---

## ⚠️ CRITICAL: Orchestration Order

**sf-metadata → sf-flow → sf-data** (you are here: sf-flow with the Salesforce MCP server)

⚠️ Flow references custom object/fields? Create with sf-metadata FIRST. Deploy objects BEFORE flows.

```text
1. sf-metadata  → Create objects/fields (local)
2. sf-flow               ◀── YOU ARE HERE (create flow, deploy via MCP)
3. sf-data               → Create test data (remote - objects must exist!)
```

See `references/orchestration.md` for extended orchestration patterns including Agentforce.

---

## 🔑 Key Insights

| Insight                  | Details                                                                                                                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Before vs After Save** | Before-Save: same-record updates (no DML), validation. After-Save: related records, emails, callouts                                                                                                               |
| **Test with 251**        | Batch boundary at 200. Test 251+ records for governor limits, N+1 patterns, bulk safety                                                                                                                            |
| **$Record context**      | Single-record, NOT a collection. Platform handles batching. Never loop over $Record                                                                                                                                |
| **$Record traversal**    | `$Record` supports relationship traversal: `{!$Record.Contact__r.FirstName}`, `{!$Record.Account__r.Name}`. Do NOT use Get Records for data already available through `$Record` lookups — this wastes a SOQL query |
| **Transform vs Loop**    | Transform: data mapping/shaping (30-50% faster). Loop: per-record decisions, counters, varying logic. See `references/transform-vs-loop-guide.md`                                                                  |

---

## Fast Path (Simple Requests)

For simple, self-contained flows (single record update, basic field mapping, straightforward screen flow), bypass the detailed requirements/design elaboration and full scoring while still performing initialization and mandatory guardrails, then generate + deploy:

1. Call `org_init()` (always required)
2. Use `sobject_describe` to verify the target object/fields exist
3. Generate the flow metadata as JSON
4. Run guardrail checks (anti-patterns only — skip full 110-point scoring)
5. Deploy via `metadata_create`
6. Verify deployment

**Use the fast path when**: the request is explicit, the flow is a single straightforward automation, and there are no ambiguous requirements.

**Use the full 5-phase workflow when**: the flow involves multiple decision branches, screen flows with complex logic, subflow orchestration, or underspecified requirements.

---

## Workflow Design (5-Phase Pattern)

### Phase 1: Requirements Gathering

**Before building, evaluate alternatives**: See `references/flow-best-practices.md` Section 1 "When NOT to Use Flow" - sometimes a Formula Field, Validation Rule, or Roll-Up Summary Field is the better choice.

If the request is underspecified, ask concise follow-up questions to gather:

- Flow type (Screen, Record-Triggered After/Before Save/Delete, Platform Event, Autolaunched, Scheduled)
- Primary purpose (one sentence)
- Trigger object/conditions (if record-triggered)

**Pre-Development Planning**: For complex flows, document requirements and sketch logic before building. See `references/flow-best-practices.md` Section 2 "Pre-Development Planning" for templates and recommended tools.

**Then**:

1. **Initialize**: Call `org_init()` with no parameters. If a default org is configured, confirm with the user. If no default, ask for the Salesforce user/alias before proceeding.
2. Use `sobject_describe` to verify object/field existence before referencing
3. Use `metadata_list` to check existing flows: `metadata_list(type="Flow")`
4. Offer reusable subflows: Sub_LogError, Sub_SendEmailAlert, Sub_ValidateRecord, Sub_UpdateRelatedRecords, Sub_QueryRecordsWithRetry → See `references/subflow-library.md`
5. If complex automation: Reference `references/governance-checklist.md`
6. Keep an internal checklist: Gather requirements, select template, generate flow metadata (JSON), validate, deploy, test

### Phase 2: Flow Design & Template Selection

**Select template**:

| Flow Type        | Template File                      |
| ---------------- | ---------------------------------- |
| Screen           | `screen-flow-template.xml`         |
| Record-Triggered | `record-triggered-*.xml`           |
| Platform Event   | `platform-event-flow-template.xml` |
| Autolaunched     | `autolaunched-flow-template.xml`   |
| Scheduled        | `scheduled-flow-template.xml`      |
| Wait Elements    | `wait-template.xml`                |

**Element Pattern Templates** (`assets/elements/`):

| Element        | Template                    | Purpose                                                     |
| -------------- | --------------------------- | ----------------------------------------------------------- |
| Loop           | `loop-pattern.xml`          | Complete loop with nextValueConnector/noMoreValuesConnector |
| Get Records    | `get-records-pattern.xml`   | All recordLookups options (filters, sort, limit)            |
| Delete Records | `record-delete-pattern.xml` | Filter-based and reference-based delete patterns            |

**JSON Deployment Reference** (`assets/json-deployment-reference.md`):
Covers XML-to-JSON translation, property placement rules, start patterns for all flow types, entry conditions (filterFormula vs filters), value reference patterns, and element JSON examples. **For `metadata_create` deployments, this reference alone is usually sufficient** — the XML templates are optional structural references for complex or unfamiliar flow types.

**Template Path Resolution** (try in order):

1. Resolve paths relative to the skill root under `assets/[template]`
2. For element snippets, resolve paths under `assets/elements/[template]`

**When to read XML templates**: Only when dealing with complex or unfamiliar element patterns (e.g., wait elements, advanced screen flows). For standard record-triggered, autolaunched, and scheduled flows, the JSON deployment reference has all the patterns needed.

**Example**: `Read: assets/record-triggered-after-save.xml`

**Naming Convention** (Recommended Prefixes):

| Flow Type                 | Prefix            | Example                                          |
| ------------------------- | ----------------- | ------------------------------------------------ |
| Record-Triggered (After)  | `Auto_`           | `Auto_Lead_Assignment`, `Auto_Account_Update`    |
| Record-Triggered (Before) | `Before_`         | `Before_Lead_Validate`, `Before_Contact_Default` |
| Screen Flow               | `Screen_`         | `Screen_New_Customer`, `Screen_Case_Intake`      |
| Scheduled                 | `Sched_`          | `Sched_Daily_Cleanup`, `Sched_Weekly_Report`     |
| Platform Event            | `Event_`          | `Event_Order_Completed`                          |
| Autolaunched              | `Sub_` or `Util_` | `Sub_Send_Email`, `Util_Validate_Address`        |

**Format**: `[Prefix]_Object_Action` using PascalCase (e.g., `Auto_Lead_Priority_Assignment`)

**Screen Flow Button Config** (CRITICAL):

| Screen | allowBack | allowFinish | Result              |
| ------ | --------- | ----------- | ------------------- |
| First  | false     | true        | "Next" only         |
| Middle | true      | true        | "Previous" + "Next" |
| Last   | true      | true        | "Finish"            |

Rule: `allowFinish="true"` required on all screens. Connector present → "Next", absent → "Finish".

**Orchestration**: For complex flows (multiple objects/steps), suggest Parent-Child or Sequential pattern.

- **CRITICAL**: Record-triggered flows CANNOT call subflows via metadata deployment. Use inline orchestration instead. See `references/xml-gotchas.md` and `references/orchestration-guide.md`

### Phase 3: Flow Generation & Deployment (via MCP)

> **Two deployment formats — know which to use:**
>
> | Path                                     | Format          | When                              |
> | ---------------------------------------- | --------------- | --------------------------------- |
> | `metadata_create` / `metadata_update`    | **JSON object** | Deploying via Salesforce MCP server |
> | Writing `.flow-meta.xml` to `force-app/` | **XML**         | Source-controlled project files   |
>
> **CRITICAL**: Do NOT pass XML strings to `metadata_create`. It requires a structured
> JSON object — use the format reference and examples below. The XML templates in
> `assets/` are the correct reference when writing local `.flow-meta.xml` files.

**Generate flow metadata**:
Construct the complete Flow metadata as a JSON object with:

- API Version: 65.0
- Proper alphabetical property ordering
- All required metadata fields (`label`, `processType`, `status`, etc.)

**CRITICAL Requirements**:

- Alphabetical property ordering at root level
- NO `bulkSupport` property (removed API 60.0+)
- Auto-Layout: all `locationX`/`locationY` = 0
- Fault paths on all DML operations

#### JSON Format Reference

> **Read `assets/json-deployment-reference.md` for the complete reference** — it covers
> XML-to-JSON translation, start patterns for all flow types, entry conditions,
> value references, and element JSON examples.

**Essential rules** (always apply):

1. **Format**: `metadata_create` requires a JSON object, NOT XML. The XML templates
   in `assets/` show structure; translate using the reference above.
2. **Property placement**: `triggerType`, `recordTriggerType`, `object`, `schedule`,
   `filters`/`filterFormula`/`filterLogic` belong ONLY inside `start`, never at top level.
3. **Value wrappers**: `{"stringValue": "text"}`, `{"booleanValue": true}`,
   `{"numberValue": 100}`, `{"elementReference": "var_Name"}`.
4. **Merge fields**: `stringValue` supports `{!$Record.Name}` syntax — no need for
   formula variables for simple string interpolation.
5. **Entry conditions**: Use `filterFormula` for compound/negated conditions
   (`AND()`, `OR()`, `NOT()`). Use `filters` array for simple field comparisons.
6. **Shell template**: Start from the Flow Shell Template below (Lesson 9) for the
   complete JSON boilerplate with all element arrays.

**Pre-Deployment: Check Prerequisites** (REQUIRED for flows referencing custom fields/objects):

Before deploying a flow, verify that all referenced custom fields and objects exist
in the target org. Flows referencing missing fields will deploy but become
`InvalidDraft` and cannot be activated.

```python
# Check if custom field exists before deploying flow that references it
sobject_describe(sObject="Lead")
# Verify TEST_Priority__c (or any custom field) appears in the field list
# If missing: create the field FIRST via sobject_field_create, then deploy the flow
```

**Deploy via MCP**:

```python
# Initialize connection (ONCE per session)
org_init(sf_user="your-username")

# Create/deploy Flow — pass a JSON object, NOT XML
metadata_create(
    type="Flow",
    metadata=[{
        "fullName": "Auto_Lead_Assignment",
        "label": "Auto Lead Assignment",
        "apiVersion": 65,
        "description": "Assigns new leads to the appropriate queue based on region",
        "environments": ["Default"],
        "processMetadataValues": [
            {"name": "BuilderType", "value": {"stringValue": "LightningFlowBuilder"}},
            {"name": "CanvasMode", "value": {"stringValue": "AUTO_LAYOUT_CANVAS"}}
        ],
        "processType": "AutoLaunchedFlow",
        "start": {
            "locationX": 0, "locationY": 0,
            "object": "Lead",
            "recordTriggerType": "Create",
            "triggerType": "RecordAfterSave",
            "connector": {"targetReference": "Check_Region"}
        },
        "decisions": [...],
        "recordUpdates": [...],
        "status": "Draft"
    }],
    sf_user="your-username"
)
```

**Post-Deployment: Verify Flow Status** (REQUIRED after every metadata_create for Flow):

After deploying a flow, immediately query its status via the Tooling API to
detect `InvalidDraft`. This catches issues the Metadata API accepts silently.

```python
# Check flow status after deployment
tooling_api_query(
    sObject="Flow",
    fields=["Id", "Definition.DeveloperName", "VersionNumber", "Status"],
    whereClause="Definition.DeveloperName = 'Auto_Lead_Assignment'"
)
# Expected: Status = "Draft"
# If Status = "InvalidDraft":
#   1. Check for missing triggerType (scheduled flows need triggerType=Scheduled)
#   2. Check for missing custom field references (sobject_describe to verify)
#   3. Fix the issue and redeploy via metadata_update
```

**Common InvalidDraft Causes and Fixes**:

| Cause                                    | Symptom                                                        | Fix                                                                                              |
| ---------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Missing `triggerType` in `start`         | Scheduled flow with `schedule` but no `triggerType: Scheduled` | Add `triggerType: "Scheduled"` to start element                                                  |
| Missing custom field                     | Flow references `Custom_Field__c` that doesn't exist           | Create field via `sobject_field_create` first, then redeploy                                     |
| Deprecated `bulkSupport`                 | API 60.0+ flow includes `bulkSupport`                          | Remove the `bulkSupport` property                                                                |
| Missing `recordTriggerType`              | Record-triggered flow without `recordTriggerType`              | Add `recordTriggerType: "Create"` (or Update/CreateAndUpdate)                                    |
| Missing `locationX`/`locationY` on start | `Required field is missing: locationX` on create               | Always include `"locationX": 0, "locationY": 0` on the start element, even for auto-layout flows |

**For Review** — validate an existing flow from the org or a local file before modifying:

- `python scripts/validate_flow_cli.py <FlowApiName>` — fetch and validate a single flow from the org
- `python scripts/validate_flow_cli.py All` — full org audit sorted by score

**Validation (STRICT MODE)**:

- **BLOCK**: Invalid structure, missing required fields (apiVersion/label/processType/status), API <65.0, broken refs, DML in loops
- **WARN**: Property ordering, deprecated properties, non-zero coords, missing fault paths, unused vars, naming violations

**New v2.0.0 Validations**:

- `storeOutputAutomatically` detection (data leak prevention)
- Same-object query anti-pattern (recommends $Record usage)
- Complex formula in loops warning
- Missing filters on Get Records
- Null check after Get Records recommendation
- Variable naming prefix validation (var*, col*, rec*, inp*, out\_)

**Validation Report Format** (6-Category Scoring 0-110):

```text
Score: 92/110 ⭐⭐⭐⭐ Very Good
├─ Design & Naming: 18/20 (90%)
├─ Logic & Structure: 20/20 (100%)
├─ Architecture: 12/15 (80%)
├─ Performance & Bulk Safety: 20/20 (100%)
├─ Error Handling: 15/20 (75%)
└─ Security: 15/15 (100%)
```

**Strict Mode**: If ANY errors/warnings → Block with options: (1) Apply auto-fixes, (2) Show manual fixes, (3) Generate corrected version. **DO NOT PROCEED** until 100% clean.

### ⛔ GENERATION GUARDRAILS (MANDATORY)

**BEFORE generating ANY Flow metadata, VERIFY no anti-patterns are introduced.**

If ANY of these patterns would be generated, **STOP and ask the user**:

> "I noticed [pattern]. This will cause [problem]. Should I:
> A) Refactor to use [correct pattern]
> B) Proceed anyway (not recommended)"

| Anti-Pattern                                                            | Impact                                                                                                                                                                                                                                   | Correct Pattern                                                                                                                     |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| After-Save updating same object without entry conditions                | **Infinite loop** (critical)                                                                                                                                                                                                             | MUST add entry conditions: "Only when [field] is changed"                                                                           |
| Get Records inside Loop                                                 | Governor limit failure (100 SOQL)                                                                                                                                                                                                        | Query BEFORE loop, use collection variable                                                                                          |
| Create/Update/Delete Records inside Loop                                | Governor limit failure (150 DML)                                                                                                                                                                                                         | Collect in loop → single DML after loop                                                                                             |
| Apex Action inside Loop                                                 | Callout limits                                                                                                                                                                                                                           | Pass collection to single Apex invocation                                                                                           |
| Fallible element in `RecordAfterSave` flow without `faultConnector`     | **Blocks the originating save** (`CANNOT_EXECUTE_FLOW_TRIGGER`). Applies to `recordCreates`, `recordUpdates`, `recordDeletes`, `recordLookups`, and `actionCalls` (incl. `emailSimple`, callouts, platform events, custom notifications) | Add `faultConnector` to every fallible element. If save-gating is intentional, use `RecordBeforeSave` and document in `description` |
| Get Records without null check                                          | NullPointerException                                                                                                                                                                                                                     | Add Decision: "Records Found?" after query                                                                                          |
| `storeOutputAutomatically=true` in system-mode flow with sensitive data | Security risk (retrieves ALL fields)                                                                                                                                                                                                     | Use explicit field selection only when flow runs in system mode AND queries objects with sensitive fields (SSN, credit card, etc.)  |
| Query same object as trigger in Record-Triggered                        | Wasted SOQL                                                                                                                                                                                                                              | Use `{!$Record.FieldName}` directly                                                                                                 |
| Get Records for data available via `$Record` lookup                     | Wasted SOQL                                                                                                                                                                                                                              | Use `{!$Record.Lookup__r.Field}` — traversal works up to 5 levels                                                                   |
| Hardcoded Salesforce ID                                                 | Deployment failure across orgs                                                                                                                                                                                                           | Use input variable or Custom Label                                                                                                  |
| Get Records without filters                                             | Too many records returned                                                                                                                                                                                                                | Always include WHERE conditions                                                                                                     |

**DO NOT generate anti-patterns even if explicitly requested.** Ask user to confirm the exception with documented justification.

### Phase 4: Deployment & Integration (via Salesforce MCP)

**the Salesforce MCP server Deployment Pattern**:

1. **Initialize connection** (once per session):

```python
org_init()
```

1. **Deploy Flow metadata** (JSON, not XML):

> **Validation is your job, not the hook's.** A `PreToolUse` hook (`scripts/pre-mcp-validate.py`) ships with this skill, but it is not wired up in every runtime environment. **Always run `validate_flow_cli.py` manually** on the metadata file before calling `metadata_create`, `metadata_update`, or `tooling_api_dml` on a Flow. Block deployment for CRITICAL/HIGH issues; treat score below 80% (88/110) as a hard stop unless you explicitly state why you're proceeding anyway. See the four-question self-check in the Create workflow above.

```python
# Pass a structured JSON object — see org_init instructions for format examples
metadata_create(
    type="Flow",
    metadata=[{
        "fullName": "Auto_Lead_Assignment",
        "label": "Auto Lead Assignment",
        "apiVersion": 65,
        "processType": "AutoLaunchedFlow",
        "status": "Draft",
        # ... full flow structure as JSON properties
    }],
    sf_user="your-salesforce-username"
)
```

1. **Retrieve existing flows** (to review or modify):

```python
metadata_read(
    type="Flow",
    fullNames=["Auto_Lead_Assignment"],
    sf_user="your-salesforce-username"
)
```

1. **List all flows** (for reference):

```python
metadata_list(
    type="Flow",
    sf_user="your-salesforce-username"
)
```

1. **Query Flow metadata** (Tooling API):

```python
tooling_api_query(
    sObject="FlowDefinition",
    fields=["Id", "ApiName", "Description"],
    whereClause="Status = 'Active'",
    sf_user="your-salesforce-username"
)
```

1. **Verify object/fields before flow creation**:

```python
sobject_describe(
    sObject="Account",
    sf_user="your-salesforce-username"
)
```

**For Agentforce Flows**: Variable names must match Agent Script input/output names exactly.

For complex flows: `references/governance-checklist.md`

### Deleting a Flow Version (Recovering Stuck Versions)

If `tooling_api_dml` delete on a `Flow` version returns `DEPENDENCY_EXISTS`
referencing a `FlowInterview`, query and delete the blocking interviews first:

```python
# Find blocking interviews for the flow version
soql_query(
    sObject="FlowInterview",
    fields=["Id", "Name", "InterviewStatus", "FlowVersionViewId"],
    whereClause="FlowVersionViewId = '<flow_version_id_truncated_to_15>'"
)

# Delete failed/errored interviews from prior runs
sobject_dml(
    operation="delete",
    sObject="FlowInterview",
    recordIds=["<interview_id_1>", "<interview_id_2>"]
)

# Now retry the Flow version delete
tooling_api_dml(
    operation="delete",
    sObject="Flow",
    recordId="<flow_version_id>"
)
```

`FlowInterview` records with `InterviewStatus = 'Error'` (failed runs) are
the most common blockers. They persist even after the flow is deactivated,
and Salesforce will not let you delete a Flow version while any interview
references it.

This commonly happens in demo/dev orgs that have run the flow with
intentionally-failing inputs (e.g. unverified email domain causing
fault-path runs). It does not typically happen in production.

### Phase 5a: Failure-Mode Review (REQUIRED before declaring done)

Before declaring a flow complete, walk through this checklist. Each question
maps to a concrete metadata pattern; if the answer reveals an unhandled case,
fix it before activation.

1. **What happens if an external action fails?** (email server down, callout
   timeout, platform event subscriber rejecting, custom notification fails
   to deliver.) → `faultConnector` on every `actionCalls` element.

2. **What happens if a referenced record doesn't exist or the user lacks
   access?** → null check on every `recordLookups`, plus `faultConnector`.

3. **What happens if the flow re-fires on the same record?** Edits, rollups,
   trigger order can re-fire your flow on records it already processed. →
   Idempotency guard: dedup flag (`*_Notified__c`, `*_Processed__c`) checked
   in entry conditions, OR `ISCHANGED()` guard on the field that drives the
   action.

4. **What happens under bulk DML (200+ records in one transaction)?** →
   No DML in loops; no SOQL in loops; `$Record` is the single record context,
   not a collection.

5. **What happens if a downstream flow this one triggers also fails?** →
   Decide if cascade-blocking is OK; if not, route to side-effect pattern.

6. **Which category is this flow?** Side-effect or save-gating? Is the
   `description` clear about the intent so the next maintainer knows?

This checklist takes 60 seconds and catches the failure modes the validator
can't see (intent, idempotency design, downstream cascading).

### Phase 5: Testing & Documentation

**Type-specific testing**: See `references/testing-guide.md` | `references/testing-checklist.md` | `references/wait-patterns.md` (Wait element guidance)

Quick reference:

- **Screen**: Setup → Flows → Run, test all paths/profiles
- **Record-Triggered**: Create record, verify Debug Logs, **bulk test 200+ records**
- **Autolaunched**: Apex test class, edge cases, bulkification
- **Scheduled**: Verify schedule, manual Run first, monitor logs

**Best Practices**: See `references/flow-best-practices.md` for:

- Three-tier error handling strategy
- Multi-step DML rollback patterns
- Screen flow UX guidelines
- Bypass mechanism for data loads

**Security**: Test with multiple profiles. System mode requires security review.

**Completion Summary**:

```
✓ Flow Creation & Deployment Complete: [FlowName]
  Type: [type] | API: 65.0 | Status: [Draft/Active]
  Deployed via: Salesforce MCP server (metadata_create)
  Validation: PASSED (Score: XX/110)
  Org: [target-org-username]

  Navigate: Setup → Process Automation → Flows → "[FlowName]"

Next Steps: Test (unit, bulk, security), Review docs, Activate if Draft, Monitor logs
Resources: `assets/`, `references/subflow-library.md`, `references/orchestration-guide.md`, `references/governance-checklist.md`
```

## Best Practices (Built-In Enforcement)

### ⛔ CRITICAL: Save-blocking is opt-in, not opt-out

**No record-triggered flow should block the originating save unless blocking is an
explicit, stated requirement.** This is the single most important architectural
rule in this skill — it overrides every other consideration except security.

Why this matters: in a `RecordAfterSave` flow, any unhandled fault in any element
propagates back to the originating DML as `CANNOT_EXECUTE_FLOW_TRIGGER`, blocking
the save. From the user's perspective, the record appears to fail to save —
when in reality the save would have succeeded but a downstream side effect
(an email server, a callout, a custom notification) failed. The wrong incident
gets paged: the team spends the afternoon debugging an "opportunity creation
bug" that is actually an email outage.

**Classify every record-triggered flow before designing it:**

| Category                        | Trigger type       | Fault handling                                                | Examples                                                                                           |
| ------------------------------- | ------------------ | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Side-effect flow** (default)  | `RecordAfterSave`  | Every fallible element MUST have a `faultConnector`           | Notifications, logging, integrations, derived-field computation, async work                        |
| **Save-gating flow** (explicit) | `RecordBeforeSave` | Faults intentionally propagate; document why in `description` | Validation that the platform's validation rules can't express, regulatory gates, anti-fraud checks |

If you can't articulate which category your flow belongs to, it's a side-effect
flow — handle the faults.

**The fallible elements** (every one of these can fail at runtime and must have
a `faultConnector` in a side-effect flow):

- `recordCreates`, `recordUpdates`, `recordDeletes` — DML failures (validation rules,
  permission errors, locked rows, governor limits)
- `recordLookups` — query failures, permission errors, missing records
- `actionCalls` — this is the one that gets missed. `emailSimple`, `emailAlert`,
  custom notifications, platform events, Apex invocable methods, external
  callouts, and Send Custom Notification all sit under `actionCalls`. **Email
  in particular fails for reasons completely outside the flow's control**
  (unverified domain, suppressed recipient, bounce rules, deliverability
  configuration). Missing a fault connector here is the most common way a
  notification flow becomes a save-blocking incident.
- `subflows` — the called subflow can fault; that fault propagates up
- `waits` — alarm/event resume can fault

**Save-gating flows must be documented.** When you do legitimately want to block
a save (i.e. the save shouldn't happen if the flow can't complete), the
`description` field of the flow must say so explicitly. Future maintainers
must be able to tell whether the absence of a fault connector is intentional
or a bug. Suggested phrasing:

> "Save-gating: this flow validates X before allowing the record to save.
> Faults are intentionally propagated to block invalid saves."

### ⛔ CRITICAL: Record-Triggered Flow Architecture

**NEVER loop over triggered records.** `$Record` = single record; platform handles batching.

| Pattern                          | OK? | Notes                                                     |
| -------------------------------- | --- | --------------------------------------------------------- |
| `$Record.FieldName`              | ✅  | Direct field access                                       |
| `$Record.Lookup__r.FieldName`    | ✅  | Relationship traversal — NO Get Records needed            |
| `$Record.Account__r.Owner.Name`  | ✅  | Multi-level traversal (up to 5 levels)                    |
| Get Records for `$Record` lookup | ❌  | Wastes SOQL — use `$Record.Relationship__r.Field` instead |
| Loop over `$Record__c`           | ❌  | Process Builder pattern, not Flow                         |
| Loop over `$Record`              | ❌  | $Record is single, not collection                         |

**`$Record` relationship traversal**: In record-triggered flows, `$Record` provides access to related records through lookup/master-detail fields WITHOUT a Get Records element. Use `{!$Record.Contact__r.FirstName}` instead of querying Contact separately. Only use Get Records when you need related records that are NOT accessible through `$Record` lookups (e.g., child records, or records with no relationship to the trigger object).

**Loops for RELATED records only**: Get Records → Loop collection → Assignment → DML after loop

### ⛔ CRITICAL: No Parent Traversal in Get Records

`recordLookups` cannot query `Parent.Field` (e.g., `Manager.Name`). **Solution**: Two Get Records - child first, then parent by Id.

### recordLookups Best Practices

| Element                            | Recommendation                          | Why                                                                                                                                                    |
| ---------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `getFirstRecordOnly`               | Set to `true` for single-record queries | Avoids collection overhead                                                                                                                             |
| `storeOutputAutomatically`         | Set to `true` (default)                 | Simpler, modern approach — auto-stores all fields. Only set to `false` with explicit field selection when handling sensitive data in system-mode flows |
| `assignNullValuesIfNoRecordsFound` | Set to `false`                          | Preserves previous variable value                                                                                                                      |
| `faultConnector`                   | Always include                          | Handle query failures gracefully                                                                                                                       |
| `filterLogic`                      | Use `and` for multiple filters          | Clear filter behavior                                                                                                                                  |

### Critical Requirements

- **API 65.0**: Latest features
- **No DML in Loops**: Collect in loop → DML after loop (causes bulk failures otherwise)
- **Bulkify**: For RELATED records only - platform handles triggered record batching
- **Fault Paths**: All DML must have fault connectors
  - ⚠️ **Fault connectors CANNOT self-reference** - Error: "element cannot be connected to itself"
  - Route fault connectors to a DIFFERENT element (dedicated error handler)

#### Fault-destination rubric

When you add a `faultConnector`, the question "where does it go?" has five
common answers, each with a different trade-off. Pick deliberately:

| Fault destination                                                                                                         | When to use                                                                                        | Trade-off                                                                       |
| ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Terminating end** (no further connector after the fault element)                                                        | Transient external failure; OK to retry on next edit; flow is genuinely fire-and-forget            | Can re-fire repeatedly until the external dependency recovers — noisy logs      |
| **Same dedup/idempotency step as success path** (e.g., set a `*_Notified__c` flag whether or not the email actually sent) | One-shot side effect; "best effort" semantics; want to avoid retry storms                          | Lost work stays lost — no auto-recovery when the external dependency comes back |
| **Error-log object** (`Flow_Error__c` or similar)                                                                         | Production org with observability requirements; want failures investigable                         | Requires the log object to exist and be writable in flow context                |
| **Platform event**                                                                                                        | Multiple downstream subscribers need to know about failures (monitoring, alerting, retry handlers) | Heavier; only worth it when something actually subscribes                       |
| **Continue down the same path after a best-effort attempt**                                                               | The failed action was optional enrichment, not core to the flow's purpose                          | Hides failures unless logged; use sparingly                                     |

**Default for most side-effect flows: terminating end OR same-as-success
dedup step.** Pick the dedup-step pattern when the cost of duplicate
notifications/work is high; pick the terminating-end pattern when transient
recovery is desirable.

- **Auto-Layout**: All locationX/Y = 0 (cleaner git diffs)
  - UI may show "Free-Form" dropdown, but locationX/Y = 0 IS Auto-Layout in metadata
- **No Parent Traversal**: Use separate Get Records for relationship field data

### Property Ordering (CRITICAL)

**All properties of the same type MUST be grouped together. Do NOT scatter them across the object.**

Complete alphabetical order:

```
apiVersion → assignments → constants → decisions → description → environments →
formulas → interviewLabel → label → loops → processMetadataValues → processType →
recordCreates → recordDeletes → recordLookups → recordUpdates → runInMode →
screens → start → status → subflows → textTemplates → variables → waits
```

**Common Mistake**: Adding an assignment near related logic (e.g., after a loop) when other assignments exist earlier.

- **Error**: "Element assignments is duplicated at this location"
- **Fix**: Move ALL assignments to the assignments section

### Performance

- **Batch DML**: Get Records → Assignment → Update Records pattern
- **Filters over loops**: Use Get Records with filters instead of loops + decisions
- **Transform element**: Powerful but complex structure - NOT recommended for hand-written flows

### Design & Security

- **Variable Names (v2.0.0)**: Use prefixes for clarity:
  - `var_` Regular variables (e.g., `var_AccountName`)
  - `col_` Collections (e.g., `col_ContactIds`)
  - `rec_` Record variables (e.g., `rec_Account`)
  - `inp_` Input variables (e.g., `inp_RecordId`)
  - `out_` Output variables (e.g., `out_IsSuccess`)
- **Element Names**: PascalCase_With_Underscores (e.g., `Check_Account_Type`)
- **Button Names (v2.0.0)**: `Action_[Verb]_[Object]` (e.g., `Action_Save_Contact`)
- **System vs User Mode**: Understand implications, validate FLS for sensitive fields
- **No hardcoded data**: Use variables/custom settings
- See `references/flow-best-practices.md` for comprehensive guidance

## Common Error Patterns

**DML in Loop**: Collect records in collection variable → Single DML after loop
**Missing Fault Path**: Add fault connector from DML → error handling → log/display
**Self-Referencing Fault**: Error "element cannot be connected to itself" → Route fault connector to DIFFERENT element
**Element Duplicated**: Error "Element X is duplicated" → Group ALL elements of same type together
**Field Not Found**: Verify field exists, deploy field first if missing
**Insufficient Permissions**: Check profile permissions, consider System mode

| Error Pattern                   | Fix                                                     |
| ------------------------------- | ------------------------------------------------------- |
| `$Record__Prior` in Create-only | Only valid for Update/CreateAndUpdate triggers          |
| "Parent.Field doesn't exist"    | Use TWO Get Records (child then parent)                 |
| `$Record__c` loop fails         | Use `$Record` directly (single context, not collection) |

### Error → Solution Quick Reference

| Error Message                                       | Solution                                                                     |
| --------------------------------------------------- | ---------------------------------------------------------------------------- |
| `Duplicate developer name: X`                       | Screen field already created this reference — don't add a separate variable  |
| `Can't use object field with sObjectInputReference` | Remove `object` property when using `inputReference`                         |
| `isCollection invalid in FlowConstant`              | Use Decision + Variable counter instead of a constant collection             |
| `Invalid element reference X not found`             | Check all element names are unique and connectors point to existing elements |
| Flow won't open in Flow Builder                     | Add all empty element type arrays to flow metadata                           |
| Silent failure on `metadata_update`                 | Read current state first with `metadata_read`; build iteratively             |
| Required field missing                              | Add `processMetadataValues: []` to every element                             |

**Metadata Gotchas**: See `references/xml-gotchas.md`

---

## ⚠️ Critical Lessons Learned (Metadata API Flows)

These lessons apply when creating or updating flows via `metadata_create` / `metadata_update` (JSON format). They are based on real-world failures and must be followed to avoid deployment errors.

### Lesson 1: Screen Field Names ARE Element References

Screen fields automatically create element references with their field name. Do **NOT** create a separate variable for screen fields — this causes a `Duplicate developer name` error.

```json
// WRONG: Don't create variable with same name as screen field
{ "screens": [{ "fields": [{ "name": "User_Input" }] }],
  "variables": [{ "name": "User_Input" }]  // DUPLICATE ERROR }

// CORRECT: Reference the screen field directly
{ "formulas": [{ "expression": "{!User_Input} & \" suffix\"" }] }
```

### Lesson 2: Collection DML — Cannot Use Both `object` and `inputReference`

When creating records from a collection using `inputReference`, do **NOT** include the `object` field. Define `objectType` on the variable instead.

```json
// WRONG:
{ "name": "Create_All", "object": "Account", "inputReference": "Var_Col" }

// CORRECT: objectType goes on the variable, not the create element
{ "variables": [{ "name": "Var_Col", "dataType": "SObject",
    "objectType": "Account", "isCollection": true }],
  "recordCreates": [{ "name": "Create_All", "inputReference": "Var_Col" }] }
```

### Lesson 3: Constants Cannot Be Collections

Flow constants cannot be collections or SObjects. Use a Decision + Counter Variable instead.

### Lesson 4: Read Current State Before Complex Updates

**ALWAYS** call `metadata_read` immediately before `metadata_update` for complex changes. Salesforce replaces the entire flow version on update — working with stale metadata will overwrite recent changes.

1. Call `metadata_read` to get current state
2. Analyze current elements and dependencies
3. Modify the retrieved metadata
4. Call `metadata_update` with complete state

### Lesson 5: All Element Names Must Be Globally Unique

Every element name in a Flow must be unique across **ALL** element types. Use prefixes to enforce this:

| Element Type  | Naming Convention | Example             |
| ------------- | ----------------- | ------------------- |
| Variables     | `Var_*`           | `Var_Account_Id`    |
| Formulas      | `Formula_*`       | `Formula_Full_Name` |
| Screens       | `Screen_*`        | `Screen_Welcome`    |
| Decisions     | `Decision_*`      | `Decision_Route`    |
| Assignments   | `Assign_*`        | `Assign_Defaults`   |
| Choices       | `Choice_*`        | `Choice_Option_A`   |
| Screen Fields | Descriptive       | `Account_Name`      |

### Lesson 6: Build Flows Iteratively, Not All At Once

- **Phase 1 — Shell**: `metadata_create` with minimal structure. Test: Does it open in Flow Builder?
- **Phase 2 — Basic Navigation**: Add first screen and routing. Test: Can you navigate through it?
- **Phase 3 — Core Logic**: Add record lookups and variables. Test: Does data flow correctly?
- **Phase 4 — Advanced Features**: Add formulas, loops, calculations. Test: Do calculations work?

**Red flags**: Creating 100+ line JSON on first attempt. Adding 5+ new element types at once. Not testing in Flow Builder between changes.

### Lesson 7: Collection DML Pattern — Build, Gather, Execute

Never create records one-by-one in a loop. Build a collection, then execute a single DML operation:

1. **Build_Record** — Assign field values to `Var_Current_Record` (single SObject variable)
2. **Add_To_Collection** — Use operator `Add` to append to the collection variable
3. **After loop exits** — Single `recordCreates` with `inputReference` pointing to the collection

Synchronous DML limit: 150 statements. Creating 10 records individually = 10 DML. Creating 10 records via collection = 1 DML.

### Lesson 8: `processMetadataValues` — Always Include Empty Array

Every Flow element **MUST** have a `processMetadataValues` property, even if it's an empty array. Without it, Salesforce may fail silently or discard the element.

```json
{ "name": "Element_Name", "processMetadataValues": [] }
```

### Lesson 8.5: Resource vs Node Elements — Property Rules

Flow elements split into two families. **Resources** (data containers) and **Nodes** (canvas/visual elements) do NOT accept the same properties. Mixing them up is one of the most common deploy-time failures (e.g. "The FlowFormula element doesn't accept a label property").

| Family                              | Element types                                                                                                                                                                                                                                                                     | Has `name` / `description` | Has `label` | Has `locationX` / `locationY` | Has `connector` |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ----------- | ----------------------------- | --------------- |
| **Resources** (no canvas position)  | `formulas`, `variables`, `constants`, `textTemplates`, `choices`, `dynamicChoiceSets`                                                                                                                                                                                             | ✅                         | ❌          | ❌                            | ❌              |
| **Nodes** (visual, canvas elements) | `assignments`, `decisions`, `screens`, `loops`, `recordCreates`, `recordUpdates`, `recordDeletes`, `recordLookups`, `actionCalls`, `apexPluginCalls`, `subflows`, `waits`, `steps`, `transforms`, `collectionProcessors`, `orchestratedStages`, `customErrors`, `recordRollbacks` | ✅                         | ✅          | ✅                            | ✅ (most)       |
| **Hybrid resources** (own `label`)  | `stages`, `rules`, `exitRules`, `experimentPaths`, `scheduledPaths`, `screenActions`, `stageSteps`, `waitEvents`                                                                                                                                                                  | ✅                         | ✅          | ❌                            | varies          |

**General rule**: If you find yourself adding `label`, `locationX`, or `locationY` to a `formulas`, `variables`, `constants`, `textTemplates`, or `choices` entry, **stop** — those properties do not exist on those types and the deploy will fail with a metadata error.

**Common manifestation**:

```json
// WRONG — FlowFormula does not accept label
{ "formulas": [{ "name": "Is_Overdue", "label": "Is Overdue",
                  "dataType": "Boolean", "expression": "{!CloseDate} < TODAY()" }] }

// CORRECT — use `name` + `description` only; the formula has no canvas presence
{ "formulas": [{ "name": "Is_Overdue", "description": "True when CloseDate is in the past",
                  "dataType": "Boolean", "expression": "{!CloseDate} < TODAY()" }] }
```

If you need a human-readable label, put it on the node that _uses_ the formula (e.g. a Decision with `label: "Is the record overdue?"`), not on the formula itself.

The local validator (`validate_flow.py`) detects this class of error as a CRITICAL issue — run it before every deploy.

### Lesson 9: Empty Arrays for All Element Type Collections

Include **ALL** element type arrays in your flow metadata, even if empty. Missing arrays can cause silent failures, elements being deleted, or flows that won't save.

```json
{
  "assignments": [],
  "choices": [],
  "decisions": [],
  "formulas": [],
  "loops": [],
  "recordCreates": [],
  "recordDeletes": [],
  "recordLookups": [],
  "recordUpdates": [],
  "screens": [],
  "variables": [],
  "textTemplates": []
}
```

### Lesson 10: Connector Chains — Every Element Needs a Path

Every element (except the final one) must have a connector to the next element. Mental checklist for each element:

- Does it have a `connector`?
- If it's a decision, does it have a `defaultConnector`?
- Does the `targetReference` point to an existing element?
- Is this intentionally the final element (screen with `allowFinish: true`)?

### Flow Shell Template (JSON for `metadata_create`)

Always start with this complete template — include **ALL** empty arrays:

```json
{
  "fullName": "PLACEHOLDER",
  "label": "PLACEHOLDER",
  "apiVersion": 65,
  "processType": "Flow",
  "status": "Draft",
  "interviewLabel": "PLACEHOLDER {!$Flow.CurrentDateTime}",
  "environments": ["Default"],
  "processMetadataValues": [
    { "name": "BuilderType", "value": { "stringValue": "LightningFlowBuilder" } },
    { "name": "CanvasMode", "value": { "stringValue": "AUTO_LAYOUT_CANVAS" } }
  ],
  "start": {
    "locationX": 0,
    "locationY": 0,
    "connector": { "targetReference": "FIRST_ELEMENT" },
    "filters": [],
    "processMetadataValues": []
  },
  "assignments": [],
  "choices": [],
  "decisions": [],
  "formulas": [],
  "loops": [],
  "recordCreates": [],
  "recordDeletes": [],
  "recordLookups": [],
  "recordUpdates": [],
  "screens": [],
  "variables": [],
  "textTemplates": []
}
```

### Flow Element Types Reference

| Element Type   | Purpose               | Key Notes                                                                    |
| -------------- | --------------------- | ---------------------------------------------------------------------------- |
| Start          | Entry point           | Contains connector to first element; record-triggered adds filters/object    |
| Variables      | Store values          | Counter vars: `dataType` Number, `scale` 0. Collections: `isCollection` true |
| Screens        | User interface        | Fields auto-create element references — do NOT create duplicate variables    |
| Decisions      | Branching logic       | Must always include `defaultConnector`                                       |
| Record Lookups | Query Salesforce data | Use `storeOutputAutomatically: false` for security                           |
| Record Creates | Insert new records    | Use `inputReference` for collections — never combine with `object` field     |
| Assignments    | Set variable values   | Operators: `Assign`, `Add`, `AssignCount`                                    |
| Loops          | Iterate collections   | Auto-creates `currentItem_{LoopName}` variable                               |
| Formulas       | Computed values       | Use `{!VarName}` syntax to reference other elements                          |

## Edge Cases

| Scenario     | Solution                                      |
| ------------ | --------------------------------------------- |
| >200 records | Warn limits, suggest scheduled flow           |
| >5 branches  | Use subflows                                  |
| Cross-object | Check circular deps, test recursion           |
| Production   | Deploy Draft, activate explicitly             |
| Unknown org  | Use standard objects (Account, Contact, etc.) |

**Debug**: Flow not visible → deploy report + permissions | Tests fail → Debug Logs + bulk test | Sandbox→Prod fails → FLS + dependencies

---

## Flow MCP Patterns

### General rules

- Do **not** hard-code IDs (queues, users, record types) in flows
- Use Entry Conditions (formulas in the `start` block) instead of a Decision with an empty action
- Set layout to Auto-Layout (`CanvasMode: AUTO_LAYOUT_CANVAS`)
- Do **not** create a new flow to fix an issue — create a new **version** instead
- Do **not** say something "cannot be done via API" — always attempt it

### List all flows (with active and latest version info)

```
tooling_api_query(sObject="FlowDefinition", fields=["Id","DeveloperName","NamespacePrefix","MasterLabel","Description","ActiveVersionId","ActiveVersion.VersionNumber","LatestVersionId","LatestVersion.VersionNumber","LatestVersion.Status","LatestVersion.MasterLabel","LatestVersion.Description"])
```

### Retrieve a specific flow version

First get the version Id from the FlowDefinition query above, then:

```
tooling_api_query(sObject="Flow", fields=["Id","FullName","DefinitionId","Definition.DeveloperName","MasterLabel","Description","VersionNumber","Status","Metadata","ProcessType"], whereClause="Id='<flow version id>'")
```

Note: do **not** include `FullName` or `Metadata` in multi-record queries — only single-record retrieval supports these.

### Create a new flow

```
metadata_create(type="Flow", metadata=[{"fullName": "Flow_Name", "label": "Flow Name", "apiVersion": 65, "processType": "AutoLaunchedFlow", "status": "Draft", ...}])
```

### Update a flow (creates a new version)

1. Retrieve current metadata: `metadata_read(type="Flow", fullNames=["Flow_Name"])`
2. Apply changes to the metadata object
3. Deploy: `metadata_update(type="Flow", metadata=[{...}], upsert=True)`
   - **Do NOT change the `fullName`** — version numbers are managed automatically
   - In production: deploy as `status: Draft` and ask user to activate manually if you get an error

### Activate / deactivate a flow version

```
metadata_update(type="FlowDefinition", metadata=[{"fullName": "Flow_Name", "activeVersionNumber": <version>}])
```

To deactivate all versions: set `activeVersionNumber` to `0`.

### Delete a flow

1. Deactivate: `metadata_update(type="FlowDefinition", metadata=[{"fullName": "Flow_Name", "activeVersionNumber": 0}])`
2. Delete all versions: `tooling_api_dml(operation="delete", sObject="Flow", record={"Id": "<flow version id>"})` (repeat for each version)

### Check flow test coverage

```
tooling_api_query(sObject="Flow", fields=["Definition.DeveloperName"], whereClause="Status = 'Active' AND (ProcessType = 'AutolaunchedFlow' OR ProcessType = 'Workflow' OR ProcessType = 'CustomEvent' OR ProcessType = 'InvocableProcess') AND Id NOT IN (SELECT FlowVersionId FROM FlowTestCoverage)")
```

### Find paused or failed flow interviews

```
soql_query(sObject="FlowInterview", fields=["Id","Name","CurrentElement","InterviewStatus","PauseLabel","CreatedDate"], whereClause="InterviewStatus IN ('Paused', 'Failed')")
```

---

## the Salesforce MCP server Integration Examples

### Example 1: Verify Object Exists Before Creating Flow

```python
# Before generating a flow for a custom object
sobject_describe(
    sObject="Invoice__c",
    sf_user="prod-username"
)
# Returns: Field list, object metadata, standard fields
```

### Example 2: List Existing Flows

```python
# Check what flows already exist
metadata_list(
    type="Flow",
    sf_user="prod-username"
)
# Returns: All Flow metadata objects in org
```

### Example 3: Deploy a Complete Record-Triggered Flow

> **Pattern note:** the `faultConnector` on `Send_Email_Action` routes to the
> `Log_Error` step. This is the "error-log object" pattern from the
> fault-destination rubric: if the email fails (e.g. domain not verified,
> recipient suppressed), the originating Case save is **not** blocked, and
> the failure is captured in `Flow_Error__c` for investigation. See the
> rubric for alternative fault destinations.

```python
# Complete example: notify managers when case category changes
metadata_create(
    type="Flow",
    metadata=[{
        "fullName": "Case_Category_Change_Alert",
        "apiVersion": 65,
        "description": "Sends email when Case Category changes from Billing to Channel. Side-effect flow: email failures are caught via faultConnector so the originating Case save is never blocked.",
        "environments": ["Default"],
        "interviewLabel": "Case Category Change Alert {!$Flow.CurrentDateTime}",
        "label": "Case Category Change Alert",
        "processMetadataValues": [
            {"name": "BuilderType", "value": {"stringValue": "LightningFlowBuilder"}},
            {"name": "CanvasMode", "value": {"stringValue": "AUTO_LAYOUT_CANVAS"}}
        ],
        "processType": "AutoLaunchedFlow",
        "start": {
            "locationX": 0, "locationY": 0,
            "connector": {"targetReference": "Check_Previous_Category"},
            "filterLogic": "and",
            "filters": [
                {"field": "Case_Category__c", "operator": "EqualTo", "value": {"stringValue": "Channel"}},
                {"field": "Case_Category__c", "operator": "IsChanged", "value": {"booleanValue": True}}
            ],
            "object": "Case",
            "recordTriggerType": "Update",
            "triggerType": "RecordAfterSave"
        },
        "decisions": [{
            "name": "Check_Previous_Category",
            "label": "Check Previous Category",
            "locationX": 0, "locationY": 0,
            "defaultConnectorLabel": "Default Outcome",
            "rules": [{
                "name": "Was_Billing",
                "conditionLogic": "and",
                "conditions": [{
                    "leftValueReference": "$Record__Prior.Case_Category__c",
                    "operator": "EqualTo",
                    "rightValue": {"stringValue": "Billing"}
                }],
                "connector": {"targetReference": "Send_Email_Action"},
                "label": "Was Billing"
            }]
        }],
        "actionCalls": [{
            "name": "Send_Email_Action",
            "label": "Send Email",
            "locationX": 0, "locationY": 0,
            "actionName": "emailSimple",
            "actionType": "emailSimple",
            "flowTransactionModel": "CurrentTransaction",
            "inputParameters": [
                {"name": "emailAddresses", "value": {"stringValue": "support-managers@example.com"}},
                {"name": "emailSubject", "value": {"stringValue": "Case Category Changed to Channel"}},
                {"name": "emailBody", "value": {"stringValue": "Case {!$Record.CaseNumber} category changed from Billing to Channel."}}
            ],
            "faultConnector": {"targetReference": "Log_Error"}
        }],
        "recordCreates": [{
            "name": "Log_Error",
            "label": "Log Error",
            "locationX": 0, "locationY": 0,
            "object": "Flow_Error__c",
            "inputAssignments": [
                {"field": "Flow_Name__c", "value": {"stringValue": "Case_Category_Change_Alert"}},
                {"field": "Context_Record_Id__c", "value": {"elementReference": "$Record.Id"}},
                {"field": "Error_Source__c", "value": {"stringValue": "Send_Email_Action"}}
            ]
        }],
        "status": "Draft"
    }],
    sf_user="prod-username"
)
```

### Example 4: Retrieve Existing Flow for Review

```python
# Get the metadata of an existing flow
metadata_read(
    type="Flow",
    fullNames=["Auto_Lead_Assignment"],
    sf_user="prod-username"
)
# Returns: Complete Flow metadata from org (JSON)
```

### Example 5: Query Flow Metadata (Tooling API)

```python
# Find all active flows
tooling_api_query(
    sObject="FlowDefinition",
    fields=["Id", "ApiName", "Description", "Status"],
    whereClause="Status = 'Active'",
    sf_user="prod-username"
)
```

---

## Cross-Skill Integration

| From Skill     | To sf-flow | When                                 |
| -------------- | ---------- | ------------------------------------ |
| sf-apex        | → sf-flow  | "Create Flow wrapper for Apex logic" |
| sf-integration | → sf-flow  | "Create HTTP Callout Flow"           |

| From sf-flow | To Skill      | When                                                |
| ------------ | ------------- | --------------------------------------------------- |
| sf-flow      | → sf-metadata | "Describe Invoice\_\_c" (verify fields before flow) |
| sf-flow      | → sf-data     | "Create 200 test Accounts" (after deploy)           |

**Deployment**: See Phase 4 above.

---

## LWC Integration (Screen Flows)

Embed custom Lightning Web Components in Flow Screens for rich, interactive UIs.

### Templates

| Template                          | Purpose                            |
| --------------------------------- | ---------------------------------- |
| `assets/screen-flow-with-lwc.xml` | Flow embedding LWC component       |
| `assets/apex-action-template.xml` | Flow calling Apex @InvocableMethod |

### Flow Pattern (XML reference — deploy as JSON)

> The XML below shows the structural pattern. When deploying via `metadata_create`, translate to the equivalent JSON object.

```xml
<screens>
    <fields>
        <extensionName>c:recordSelector</extensionName>
        <fieldType>ComponentInstance</fieldType>
        <inputParameters>
            <name>recordId</name>
            <value><elementReference>var_RecordId</elementReference></value>
        </inputParameters>
        <outputParameters>
            <assignToReference>var_SelectedId</assignToReference>
            <name>selectedRecordId</name>
        </outputParameters>
    </fields>
</screens>
```

### Documentation

| Resource              | Location                                                                              |
| --------------------- | ------------------------------------------------------------------------------------- |
| LWC Integration Guide | [references/lwc-integration-guide.md](references/lwc-integration-guide.md)            |
| LWC Component Setup   | [sf-lwc/assets/flow-integration-guide.md](../sf-lwc/assets/flow-integration-guide.md) |
| Triangle Architecture | [references/triangle-pattern.md](references/triangle-pattern.md)                      |

---

## Apex Integration

Call Apex `@InvocableMethod` classes from Flow for complex business logic.

### Flow Pattern (XML reference — deploy as JSON)

> The XML below shows the structural pattern. When deploying via `metadata_create`, translate to the equivalent JSON object.

```xml
<actionCalls>
    <name>Process_Record</name>
    <actionName>RecordProcessor</actionName>
    <actionType>apex</actionType>
    <inputParameters>
        <name>recordId</name>
        <value><elementReference>var_RecordId</elementReference></value>
    </inputParameters>
    <outputParameters>
        <assignToReference>var_IsSuccess</assignToReference>
        <name>isSuccess</name>
    </outputParameters>
    <faultConnector>
        <targetReference>Handle_Error</targetReference>
    </faultConnector>
</actionCalls>
```

### Documentation

| Resource                    | Location                                                                            |
| --------------------------- | ----------------------------------------------------------------------------------- |
| Apex Action Template        | `assets/apex-action-template.xml`                                                   |
| Apex @InvocableMethod Guide | [sf-apex/references/flow-integration.md](../sf-apex/references/flow-integration.md) |
| Triangle Architecture       | [references/triangle-pattern.md](references/triangle-pattern.md)                    |

### ⚠️ Flows for Agentforce

**When creating Flows for Agentforce agents:**

- sf-flow (this skill) creates the validated Flow metadata (JSON)
- sf-flow deploys via MCP metadata_create tool
- **Action Definition registration required** (see below)
- Only THEN can agents use `flow://FlowName` targets

**Variable Name Matching**: When creating Flows for Agentforce agents:

- Agent Script input/output names MUST match Flow variable API names exactly
- Use descriptive names (e.g., `inp_AccountId`, `out_AccountName`)
- Mismatched names cause "Internal Error" during agent publish

### Output Variable Naming for Agentforce

Use `out_` prefix for output variables to distinguish them in Action Definition schema:

```xml
<variables>
    <name>out_CaseSubject</name>
    <dataType>String</dataType>
    <isOutput>true</isOutput>
</variables>
<variables>
    <name>out_CaseStatus</name>
    <dataType>String</dataType>
    <isOutput>true</isOutput>
</variables>
```

### Formula Expression Limitations in Flows

Flow formulas have more limited function support than formula fields. The table below applies to **formula variables and formula elements within the flow**, NOT to `filterFormula` entry conditions:

| Function                  | In `filterFormula` (entry conditions) | In flow formulas/variables | Alternative for flow formulas          |
| ------------------------- | ------------------------------------- | -------------------------- | -------------------------------------- |
| `ISNEW()` / `ISCHANGED()` | ✅ Supported                          | ❌ Not supported           | Use `$Record__Prior` comparisons       |
| `BLANKVALUE()`            | ✅ Supported                          | ❌ Not supported           | Use Decision element or `IF()`         |
| `CASESAFEID()`            | ❌ Not supported                      | ❌ Not supported           | ID variables handle this automatically |

### filterFormula Gotchas

- **`ISPICKVAL(field, value)`** — the second argument must be a **literal string** (the API name of the picklist value). Passing a field reference or variable as the second argument causes a formula compile error — if you need to compare two fields, use `=` instead.
- For picklist equality in entry conditions, prefer the simpler `TEXT({!$Record.Field}) = "Value"` or `ISPICKVAL({!$Record.Field}, "Value")`.
- **`filterFormula` and `emailSimple` body** do not support cross-object relationship traversal — use only direct `$Record` field references (e.g., `{!$Record.Status}`) in these contexts. Relationship paths like `$Record.Owner.Name` work in flow formulas and assignments but cause deploy errors in `filterFormula`/`emailSimple`.

### Action Definition Registration (REQUIRED)

> **CRITICAL**: Creating a Flow is NOT sufficient for Agentforce. The Flow must be registered as an Action Definition.

**Registration Workflow:**

1. **Deploy Flow** to target org via sf-flow + the Salesforce MCP server metadata_create
2. Navigate to **Setup > Agentforce > Action Definitions**
3. Click **"New Action"**, select **"Flow"** as target type
4. Choose your deployed Flow from the list
5. **Map input/output variables** - these become the action's schema
6. Configure planner flags:
   - `is_displayable`: Can LLM show output to user?
   - `is_used_by_planner`: Can LLM use output for decisions?
7. **Save** the Action Definition

```
Flow Created  →  Deployed to Org  →  Action Definition Created  →  Agent Can Use
     ↑               ↑                        ↑                         ↑
   sf-flow  the Salesforce MCP server            Setup > Agentforce         @actions.MyAction
```

**Why This Matters**: The Action Definition is what exposes the Flow to the agent runtime with proper input/output schema mapping. Without it, `@actions.FlowName` will fail with `ValidationError: Tool target 'FlowName' is not an action definition`.

| Direction             | Pattern                                             |
| --------------------- | --------------------------------------------------- |
| sf-flow → sf-metadata | "Describe Invoice\_\_c" (verify fields before flow) |
| sf-flow → the Salesforce MCP server    | Deploy with validation via metadata_create          |
| sf-flow → sf-data     | "Create 200 test Accounts" (test data after deploy) |

## Notes

**Dependencies** (optional): sf-metadata, sf-data | **API**: 65.0 | **Mode**: Strict (warnings block) | **MCP Server**: the Salesforce MCP server (required)

**Required Setup**:

- the Salesforce MCP server account connected to Salesforce org
- `org_init()` called once per session
- Valid Salesforce username for `sf_user` parameter
- **Audit Output**: All audit intermediate files go to `--output-dir` by default

**Validation hook**: A plugin-level `PreToolUse` hook (`pre-mcp-validate.py`) is shipped with this skill and, when registered, runs automatically against `metadata_create`, `metadata_update`, and `tooling_api_dml` on Flow/FlowDefinition. **The hook is not guaranteed to be registered in every host environment.** Until you have confirmed it is wired up for your runtime, you MUST run `python scripts/validate_flow_cli.py <path>` manually before every Flow deployment — see the four-question self-check in the Create workflow.
