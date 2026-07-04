---
name: sf-audit
plugin: salesforce-core
argument-hint: '[full|apex|flow|lwc|metadata|permissions|reports|integrations|coverage|licensing|team|change-history|data-quality] ...'
description: >
  Run a comprehensive Salesforce org audit producing 18 documents from a single scan.
  Inventories and scores Apex classes, triggers, Flows, Process Builders, Workflow Rules,
  LWC components, custom objects/fields, validation rules, formula fields, approval
  processes, escalation/assignment/auto-response rules, Profiles, and Permission Sets.
  Detects unused custom fields and objects (no data and/or no references in code, flows,
  layouts, or reports). Also covers Reports & Dashboards, integrations, test coverage,
  licensing, team evaluation, change history, data quality, and architectural analysis.
  Scans all formula and criteria logic for hardcoded Record IDs, Campaign names, Profile
  names, URLs, and other fragile values. Generates Word, Excel, HTML reports plus 12
  standalone analysis documents including a customer report and strategic engagement plan.
  Usage: /sf-audit [full|apex|flow|lwc|metadata|permissions|reports|integrations|coverage|licensing|team|change-history|data-quality] ...
metadata:
  version: 3.1.0
---

# Salesforce Org Audit

Run a comprehensive Salesforce org audit covering code quality, automation
health, data model design, and the permission model.

**Scoring**: Where a numeric rubric exists, defer to the corresponding domain
skill (`sf-apex`, `sf-flow`, `sf-lwc`,
`sf-metadata`). Do not invent your own criteria.

For categories without a numeric rubric (Triggers, Workflow Rules, Process
Builders, Profiles, Validation Rules, Formula Fields, Approval Processes,
Escalation Rules, Assignment Rules, Auto-Response Rules), produce an inventory
with qualitative findings and severity classifications.

---

## Dispatch

Parse `$ARGUMENTS` to determine the audit scope:

| First argument or intent                | Workflow                            |
| --------------------------------------- | ----------------------------------- |
| `full`, no scope specified after asking | Full Org Audit (all domains)        |
| `apex`                                  | Apex-only audit (C1-C2)             |
| `flow`                                  | Flow/automation-only audit (C3-C4)  |
| `lwc`                                   | LWC-only audit (C5)                 |
| `metadata`, `data-model`                | Metadata/data-model-only audit (C7) |
| `permissions`                           | Permissions-only audit (C6)         |
| `reports`                               | Reports & Dashboards only (C10)     |
| `integrations`                          | Integration analysis only (C11)     |
| `coverage`                              | Test coverage only (C12)            |
| `licensing`                             | Licensing analysis only (C13)       |
| `team`                                  | Team evaluation only (C14)          |
| `change-history`                        | Change history audit only (C15)     |
| `data-quality`                          | Data quality report only (C7 + DQ)  |
| _(no argument or unclear)_              | Ask the user (see below)            |

When the audit scope is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What would you like to audit?\n\n1. **Full** — comprehensive audit of the entire org\n2. **Apex** — Apex classes and triggers only\n3. **Flow** — Flows, Process Builders, and Workflow Rules only\n4. **LWC** — Lightning Web Components only\n5. **Metadata** — custom objects, fields, and data model only\n6. **Permissions** — Profiles, Permission Sets, and Permission Set Groups only")
```

Do NOT guess the scope or default to a full audit. Wait for the user's answer.

---

## Start here every time — read `audit_state.md` first

Before doing anything else, check whether a working document already exists:

```
Read: ./audit_output/audit_state.md
```

- **File exists** — you are resuming a previous audit. Read the state, note
  what is complete, and pick up from the `## Next Step` section. Tell the user:
  "Resuming audit from [last completed phase]. [X] of [Y] components processed."

- **File does not exist** — this is a fresh audit. Proceed to Prerequisites,
  then Environment Detection, then Phase A.

Keep `audit_state.md` up to date throughout. Update it after completing each
domain in Phase C. This file is your contract with your future self after
a context compaction.

---

## Prerequisites

Call `org_init()` first if not already done this session.

---

## Execution modes

Determine execution mode once, before Phase A. Four modes are supported —
see `references/execution-modes.md` for detection logic and full details.

### Audit-specific mode behaviour

| Mode                      | Body retrieval                      | Queries                |
| ------------------------- | ----------------------------------- | ---------------------- |
| `sfdx-repo`               | Read from disk (no API calls)       | MCP for live-only data |
| `cli`                     | `sf project retrieve start -m`      | `sf data query --json` |
| `mcp-plus-code-execution` | MCP tools; download `artifactUrl`   | MCP tools              |
| `mcp-core`                | MCP tools; `fetch_more` with cursor | MCP tools              |

**`sfdx-repo` specifics:**

- Read `.cls`, `.trigger`, `.flow-meta.xml`, and LWC bundles from disk.
- Still use MCP for live-only data: permission assignments, user counts,
  PSG status, active user queries.
- For incremental audits: use `git log` to detect changed files (Phase A3).

**`cli` specifics:**

- Bulk retrieve via `sf project retrieve start -m <type>`.
- Queries via `sf data query -q "..." --target-org <org> --json`.
- For incremental audits: filter by `LastModifiedDate` in queries.

**`mcp-plus-code-execution` specifics:**

- Bulk query first (e.g. `tooling_api_query: SELECT Id, Name, Body FROM
ApexClass WHERE NamespacePrefix = null ORDER BY Id`).
- When the response includes `instructions.artifactUrl`, download it and
  write the JSON to `./audit_output/intermediate/` for local processing.
- Run `pre_score.py` on the downloaded files (Strategy A).

**`mcp-core` specifics:**

- Same bulk queries, but page through large responses with
  `fetch_more(artifactId=..., cursor=_pagination.nextCursor)`.
- Process in batches of 5; discard bodies between batches (Strategy B).

In all modes, use MCP tools (`soql_query`, `tooling_api_query`,
`sobject_describe`) for targeted lookups when CLI is not needed.

---

## Incremental audit detection

If the user mentions a previous audit, asks to "update" an audit, or provides
a path to prior audit output, this is an **incremental audit**.

### Locating the previous audit

Look for `audit_state.md` in one of:

1. A user-provided path (e.g. `~/audits/2026-01/audit_output/`)
2. A git repository the user specifies
3. The default `./audit_output/` directory (if it contains a completed audit)

From the previous `audit_state.md`, extract:

- **Audit date** — the timestamp of the last completed audit
- **Component inventory** — names and scores of all previously scored components
- **Skipped components** — what was excluded and why

### Delta detection (per mode)

| Mode                      | How to find changed components                                               |
| ------------------------- | ---------------------------------------------------------------------------- |
| `sfdx-repo`               | `git log --after="<prev_date>" --name-only --diff-filter=ACMR -- force-app/` |
| `cli`                     | Add `AND LastModifiedDate > <prev_date>` to Tooling/SOQL queries             |
| `mcp-plus-code-execution` | Add `AND LastModifiedDate > <prev_date>` to Tooling/SOQL queries             |
| `mcp-core`                | Add `AND LastModifiedDate > <prev_date>` to Tooling/SOQL queries             |

### Delta categories

Classify every component into one of:

| Category      | Action                                                     |
| ------------- | ---------------------------------------------------------- |
| **Changed**   | Re-score against current rubric                            |
| **New**       | Score as new (not in previous audit)                       |
| **Removed**   | Mark as removed in reports                                 |
| **Unchanged** | Carry forward previous score — do not re-fetch or re-score |

Track these categories in `audit_state.md` and in the final reports.

---

## Handling large MCP responses

See `references/mcp-pagination.md` for the full artifact and pagination
reference. Key points for audits:

- **`mcp-plus-code-execution`**: download `instructions.artifactUrl` and
  write JSON to `./audit_output/intermediate/` for local processing with
  `pre_score.py`.
- **`mcp-core`**: page through with
  `fetch_more(artifactId=..., cursor=_pagination.nextCursor)`. Process in
  batches of 5; discard bodies between batches.
- **`sfdx-repo` / `cli`**: bodies come from disk or CLI — artifact
  responses are uncommon.

### Additional MCP constraints

1. **Flow single-row constraint** — Tooling query on `Flow` with `Metadata`
   returns only one row. Fetch Flow IDs first, then one row per ID.
2. **Permission queries** — PermissionSet/PSG datasets hit limits quickly.
   Use cursor windows and persist per-batch.

---

## Phase A — Quick Pass (always runs first)

The Quick Pass is a lightweight inventory. It fetches only metadata headers
— no source bodies — so it completes quickly even for large orgs.

**Goals:**

1. Count every component type across the whole org
2. Classify each component: **local** (NamespacePrefix = null) vs
   **managed package** (NamespacePrefix != null)
3. Flag known generated / unmodifiable classes (see skip list below)
4. Collect surface quality signals: API versions, class sizes
5. If incremental: detect the delta (changed components since last audit)
6. Estimate the cost of the Deep Dive so the user can make an informed decision

### A1 — Component counts

**cli / MCP modes** — query counts:

```
tooling_api_query: SELECT COUNT(Id) total FROM ApexClass WHERE NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM ApexClass WHERE NamespacePrefix != null
tooling_api_query: SELECT COUNT(Id) total FROM ApexTrigger WHERE NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM FlowDefinition WHERE ActiveVersionId != null AND NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM LightningComponentBundle WHERE NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM CustomObject WHERE NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM ValidationRule WHERE NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM WorkflowRule WHERE NamespacePrefix = null
tooling_api_query: SELECT COUNT(Id) total FROM CustomField WHERE NamespacePrefix = null AND Formula != null
metadata_list: type=ApprovalProcess
soql_query: SELECT COUNT(Id) total FROM PermissionSet WHERE IsOwnedByProfile = false AND NamespacePrefix = null AND Type != 'Group'
soql_query: SELECT COUNT(Id) total FROM PermissionSetGroup
soql_query: SELECT COUNT(Id) total FROM Profile
soql_query: SELECT COUNT(Id) total FROM Report
soql_query: SELECT COUNT(Id) total FROM Dashboard
soql_query: SELECT COUNT(Id) total FROM ConnectedApplication
soql_query: SELECT COUNT(Id) total FROM NamedCredential WHERE NamespacePrefix = null
soql_query: SELECT COUNT(Id) total FROM UserLicense
```

**sfdx-repo mode** — count files on disk:

```bash
find force-app/main/default/classes -name "*.cls" | wc -l
find force-app/main/default/triggers -name "*.trigger" | wc -l
find force-app/main/default/flows -name "*.flow-meta.xml" | wc -l
find force-app/main/default/lwc -mindepth 1 -maxdepth 1 -type d | wc -l
```

Supplement with MCP queries for live-only data (Profiles, Permission Sets,
PSGs, user counts).

### A2 — Surface metadata for Apex classes (local only)

Fetch name, size, and API version — no body — for all local Apex classes.

**cli / MCP modes:**

```
tooling_api_query: SELECT Id, Name, LengthWithoutComments, ApiVersion
  FROM ApexClass
  WHERE NamespacePrefix = null
  ORDER BY Id
```

If the response includes `instructions.artifactId`, retrieve using the
strategy for your execution mode (see `references/mcp-pagination.md`).

**sfdx-repo mode** — read `-meta.xml` files for ApiVersion; use file size as
a proxy for `LengthWithoutComments`.

From this data, immediately flag:

- Classes with `ApiVersion < 50.0` (more than 4 years old) — LOW risk
- Classes with `LengthWithoutComments > 5000` — flag as large, note for review
- Classes matching the **generated/skip list** (see below)

### A3 — Delta detection (incremental only)

Skip this step for fresh audits.

**sfdx-repo mode:**

```bash
git log --after="<prev_audit_date>" --name-only --diff-filter=ACMR \
  -- force-app/main/default/classes/ force-app/main/default/triggers/ \
     force-app/main/default/flows/ force-app/main/default/lwc/
```

Parse the output to identify changed files. Map file paths to component names.

**cli / MCP modes:**

Add `AND LastModifiedDate > <prev_audit_date>` to the A2 query and equivalent
queries for triggers, flows, and LWC. Components not in the result set are
unchanged — carry forward their previous scores.

Also detect removed components: any component in the previous inventory that
no longer appears in the current full inventory count.

### A4 — Surface metadata for Flows and LWC

**Flows:**

```
tooling_api_query: SELECT Id, DeveloperName, ActiveVersionId,
  ActiveVersion.VersionNumber, ActiveVersion.ProcessType
  FROM FlowDefinition
  WHERE ActiveVersionId != null AND NamespacePrefix = null
  ORDER BY Id
```

Separate by `ActiveVersion.ProcessType`: Flows vs Process Builders.

**LWC:**

```
tooling_api_query: SELECT Id, DeveloperName, ApiVersion
  FROM LightningComponentBundle
  WHERE NamespacePrefix = null
  ORDER BY Id
```

### A5 — Write `audit_state.md`

Create `./audit_output/audit_state.md` with the Quick Pass results:

```markdown
# Audit State — {ORG_NAME} — {DATE}

## Mode

EXEC_MODE: sfdx-repo | cli | mcp-plus-code-execution | mcp-core
AUDIT_TYPE: fresh | incremental (previous: {PREV_DATE})

## Component Inventory (Phase A complete)

| Domain            | Local | Managed | Skipped (generated) | Delta |
| ----------------- | ----- | ------- | ------------------- | ----- |
| Apex Classes      | X     | Y       | Z                   | D     |
| Apex Triggers     | X     | -       | -                   | D     |
| Active Flows      | X     | -       | -                   | D     |
| Process Builders  | X     | -       | -                   | D     |
| LWC Components    | X     | -       | -                   | D     |
| Custom Objects    | X     | -       | -                   | D     |
| Validation Rules  | X     | -       | -                   | -     |
| Workflow Rules    | X     | -       | -                   | -     |
| Permission Sets   | X     | -       | -                   | -     |
| PSGs              | X     | -       | -                   | -     |
| Profiles          | X     | -       | -                   | -     |
| Reports           | X     | -       | -                   | -     |
| Dashboards        | X     | -       | -                   | -     |
| Connected Apps    | X     | -       | -                   | -     |
| Named Credentials | X     | -       | -                   | -     |
| User Licenses     | X     | -       | -                   | -     |

(Delta column: number of changed/new components for incremental audits)

## Skip List Applied

- MetadataService (generated, 12,000+ lines — not user-controlled)
- [any other skipped classes with reason]

## Surface Findings from Quick Pass

- [API version warnings]
- [oversized class flags]

## Deep Dive Progress

- [ ] C1: Apex Classes (0 / X local)
- [ ] C2: Apex Triggers (0 / X)
- [ ] C3: Flows (0 / X)
- [ ] C4: Process Builders (0 / X)
- [ ] C5: LWC (0 / X)
- [ ] C6: Permissions
- [ ] C7: Data Model (0 / X objects)
- [ ] C7b: Unused Fields & Objects
- [ ] C8: Workflow Rules
- [ ] C10: Reports & Dashboards
- [ ] C11: Integrations
- [ ] C12: Test Coverage
- [ ] C13: Licensing
- [ ] C14: Team Evaluation
- [ ] C15: Change History

## Scores Accumulated

[populated as deep dive runs]

## Carried Forward (incremental only)

[list of unchanged components with their previous scores]

## Next Step

-> Awaiting user approval for Deep Dive (Phase B)
```

### A6 — Scale Gate

After writing `audit_state.md`, check whether the org is large enough to
warrant special handling. Count the scoreable components per domain:

| Domain       | Count | Over 10? |
| ------------ | ----- | -------- |
| Apex Classes | {n}   | Y/N      |
| Triggers     | {n}   | Y/N      |
| Flows        | {n}   | Y/N      |
| LWC          | {n}   | Y/N      |
| Objects      | {n}   | Y/N      |

**If ANY domain exceeds 10**, inform the user before proceeding to Phase B:

> I found **{total}** components to score across **{domains}** domains.
>
> - **"Score all"** — I'll score every component.
> - **"Score a sample"** — I'll score the top 10 per domain ranked by risk
>   (old API version, large size, naming anomalies). The rest get surface
>   metrics only.
> - **"Quick pass only"** — Report with inventory data, no body downloads.

Record the user's choice in `audit_state.md` under `## Scoring Strategy`
(`full | sample | quick_pass`). Phase B and Phase C reference this value.

**If no domain exceeds 10**, proceed directly to Phase B.

### Generated / skip list

The following classes should be **noted but not scored** in the Deep Dive.
They are large or generated files that the org developer does not directly
author and cannot meaningfully improve:

| Class name pattern                       | Reason                                                          |
| ---------------------------------------- | --------------------------------------------------------------- |
| `MetadataService`                        | Andrew Fawcett's Apex Metadata API — generated, ~12,000 lines   |
| `fflib_*`                                | FinancialForce Apex Common library (managed-package equivalent) |
| `Callable_MockProvider`, `CallableMock*` | Test infrastructure, not production logic                       |

More broadly: if a class has `LengthWithoutComments > 8000` **and** a name
that does not correspond to a business domain concept (e.g. it looks like a
library or framework class), flag it for user confirmation rather than
spending time scoring it.

---

## Phase B — User Approval Gate

After Phase A, present a summary and ask for approval before starting the
Deep Dive. This is important: the Deep Dive can cost hundreds of API calls
on a large org.

Present something like:

---

**Quick Pass complete for {ORG_NAME}.**

**Local components to score:**

- Apex Classes: **{X}** (excl. {Z} generated/skipped)
- Apex Triggers: **{X}**
- Active Flows: **{X}** (incl. {PB} Process Builders)
- LWC Components: **{X}**
- Custom Objects: **{X}**

**Execution mode:** `{EXEC_MODE}`

[If incremental:]
**Delta since {PREV_DATE}:** {D} components changed, {N} new, {R} removed.
{U} unchanged scores will be carried forward.

[If mcp-plus-code-execution or mcp-core mode:]
**Estimated cost:** ~{total} sequential API calls.
For reference: 500 classes ~ 500 API calls ~ 20-40 minutes.

**Managed packages excluded by default.** {Y} managed-package classes
will be skipped unless you ask me to include them.

**Surface findings noticed in Quick Pass:**

- {count} classes older than API v50 ({list top 5})
- {count} classes larger than 5,000 lines
- {list any other flags}

**Proceed with full Deep Dive?** You can also say:

- "Yes, full audit" — scores all domains
- "Yes, just Apex and Flows" — skips LWC, Metadata
- "Just show me the quick pass results" — lightweight report from Phase A
  data only, no body downloads

[If the user chose "Score a sample" in A6, remind them here:
"You selected sample scoring — I'll score the top 10 per domain by risk."]

---

If the user says "just quick pass results", skip to Phase D (reports) and
generate reports based on what Phase A collected. Mark unscored domains as
"Not audited — surface metrics only."

---

## Phase C — Deep Dive

> **MANDATORY (when user chose "Score all" in A6): Score EVERY component. No sampling. No shortcuts.**
>
> When the user chose "Score all" in A6, you MUST individually fetch, read, and
> score **every single** Apex class, trigger, Flow, and LWC component in the
> org (minus the generated/skip list and managed packages). Do NOT:
>
> - Score a "representative sample" and extrapolate
> - Score only the first N items and summarize the rest
> - Skip items because the org is large or you are running low on context
> - Group multiple components into a single score
> - Estimate scores based on metadata (size, API version) without reading the body
>
> The batch sizes (20 for Apex, 10 for Flows/LWC) are **checkpointing
> intervals**, not limits. After each batch, update `audit_state.md` and
> continue to the next batch until every component is scored.
>
> **Completeness check:** Before marking any sub-phase complete, compare the
> count of scored components against the inventory count from Phase A. If they
> do not match (after accounting for skipped/generated items), you are not done.
> Keep processing until: `scored + skipped + carried_forward == inventory count`.
> (For fresh audits, `carried_forward` is 0.)

### Environment-aware processing

Choose your processing strategy based on what the environment supports:

**Strategy A — Pre-score on disk** (`sfdx-repo`, `cli`, or
`mcp-plus-code-execution`):

1. Fetch all bodies to `./audit_output/intermediate/` (via local filesystem,
   CLI bulk retrieve, or `artifactUrl` download — whichever mode applies)
2. Run the pre-scoring orchestrator:
   ```bash
   python scripts/pre_score.py \
     --intermediate-dir ./audit_output/intermediate \
     --output-dir ./audit_output \
     --threshold 70
   ```
3. Read `./audit_output/pre_score_summary.json`. Only review components
   listed in `needs_llm_review` (those scoring below 70% of max). Accept all
   other scores as-is — **do not load their bodies into context**.
4. For flagged components: read the body, apply the domain rubric, adjust the
   score if the script produced a false positive, and record the final score.
5. Write the final JSON score files and proceed to Phase C9 / Phase D.

This strategy keeps component bodies **out of context entirely** for the
majority of components, allowing audits of 500+ component orgs.

**Strategy B — Batch in context** (`mcp-core`):

1. Process components in batches of **5** (not 20). For each component:
   a. Fetch the body (via `fetch_more` with cursor, or direct query)
   b. Score it against the rubric
   c. Record the score in `audit_state.md` under `## Scores Accumulated`
   as one row: `| Name | Score/Max | Top Issue |`
   d. **Discard the body** before loading the next component
2. Never hold more than 2 component bodies in context simultaneously.
3. After each batch of 5, update `audit_state.md` with progress.

**How to choose:** Use Strategy A in `sfdx-repo`, `cli`, or
`mcp-plus-code-execution` mode. Use Strategy B in `mcp-core` mode.
See `references/execution-modes.md` for detection logic.

---

Update `audit_state.md` after completing each sub-phase. If the conversation
gets interrupted (context compaction, session end), the next session can
resume from the state file.

**In every phase: skip components where `NamespacePrefix != null`.**

**For incremental audits:** only process changed/new components. Carry forward
previous scores for unchanged components. Mark removed components.

### C1 — Apex Classes (deep)

**Score every local class.** Process in batches of 20 (for checkpointing). For each batch:

1. Fetch `Body`:
   - **sfdx-repo**: read from `force-app/main/default/classes/<ClassName>.cls`
   - **cli**: `sf project retrieve start -m ApexClass --target-org <org>`
     (bulk, one CLI call for all classes)
   - **MCP modes**: bulk query first — `tooling_api_query: SELECT Id, Name,
Body FROM ApexClass WHERE NamespacePrefix = null ORDER BY Id`. If the
     response includes `instructions.artifactId`, retrieve using the
     strategy for your mode (see `references/mcp-pagination.md`). Fall back
     to `SELECT Body FROM ApexClass WHERE Id = '<id>'` one at a time only
     if bulk query is not available.
2. Write each body to `./audit_output/intermediate/apex/<ClassName>.cls`
3. Score using the 150-point rubric from `sf-apex`
4. Track: class name, score, top 3 issues
5. After each batch of 20: update `audit_state.md` with progress and scores

**Skip any class on the generated/skip list.** Note its name and reason in
`audit_state.md` but do not score it.

**Continue batches until every local class is scored.** Then compute:

- Mean and median score
- Count below 70 (needs attention), below 50 (critical)
- Top 5 most common issue types across all classes

**Verify:** `scored + skipped + carried_forward == Phase A local class count`.
If not, identify and score the missing classes before proceeding.

Update `audit_state.md`: mark C1 complete, record aggregate stats.

### C2 — Apex Triggers (deep)

**Score every local trigger.** Follow the same completeness rules as C1.

1. Fetch trigger metadata:
   ```
   tooling_api_query: SELECT Id, Name, TableEnumOrId, ApiVersion, Status
     FROM ApexTrigger WHERE NamespacePrefix = null
   ```
2. Fetch `Body`:
   - **sfdx-repo**: read from `force-app/main/default/triggers/<Name>.trigger`
   - **cli**: `sf project retrieve start -m ApexTrigger --target-org <org>`
   - **MCP modes**: bulk query with artifact retrieval (same pattern as C1).
     Fall back to `SELECT Body FROM ApexTrigger WHERE Id = '<id>'` one at a
     time if needed.
3. Write each to `./audit_output/intermediate/triggers/<TriggerName>.trigger`
4. Score against the Apex rubric where applicable. Also flag trigger-specific
   issues:

| Finding                                                         | Severity |
| --------------------------------------------------------------- | -------- |
| Logic in trigger body instead of a handler class                | HIGH     |
| No bulkification (SOQL/DML inside loop over Trigger.new)        | CRITICAL |
| Multiple triggers on same object + event (execution order risk) | HIGH     |
| Missing before/after context checks                             | MEDIUM   |
| ApiVersion < 55.0                                               | LOW      |

**Verify:** `scored + skipped + carried_forward == Phase A local trigger count`.

Update `audit_state.md`: mark C2 complete.

### C3 — Flows (deep)

**Score every active Flow** (excluding Process Builders — those go to C4).
Use the Flow ID list from Phase A4.

1. Fetch flow definitions:
   - **sfdx-repo**: read from `force-app/main/default/flows/<Name>.flow-meta.xml`
   - **cli**: `sf project retrieve start -m Flow --target-org <org>`
   - **MCP modes**: `tooling_api_query` on `Flow` WHERE `Id = '<id>'` (one
     row per ID — single-row constraint applies)
2. Write each to `./audit_output/intermediate/flows/<DeveloperName>.flow-meta.xml`
3. Score using the 110-point rubric from `sf-flow`
4. Separate Process Builders (`ProcessType = 'Workflow'`) — inventory only,
   no Flow rubric score (see C4)
5. After every 10 flows, update `audit_state.md`

**Continue until every active Flow is scored.** Then verify:
`scored_flows + skipped_flows + carried_forward == Phase A active Flow count` and
`process_builders == Phase A Process Builder count`.

Update `audit_state.md`: mark C3 complete.

### C4 — Process Builders (inventory)

Process Builders (`ProcessType = 'Workflow'`) are legacy. Do not score
against the Flow rubric. Inventory and flag:

| Finding                                         | Severity |
| ----------------------------------------------- | -------- |
| Active Process Builder (should migrate to Flow) | HIGH     |
| > 10 criteria nodes                             | MEDIUM   |
| Invokes Apex actions                            | MEDIUM   |
| Multiple Process Builders on same object        | HIGH     |

Write to `./audit_output/intermediate/process_builders/inventory.md`.
Update `audit_state.md`: mark C4 complete.

### C5 — LWC (deep)

**Score every local LWC component.** Follow the same completeness rules as C1.

1. Fetch component source:
   - **sfdx-repo**: read from `force-app/main/default/lwc/<Name>/`
   - **cli**: `sf project retrieve start -m LightningComponentBundle --target-org <org>`
   - **MCP modes**: `metadata_read` or `LightningComponentResource` Tooling
     query grouped by bundle ID
2. Write each to `./audit_output/intermediate/lwc/<DeveloperName>/`
3. Score using the 165-point rubric from `sf-lwc`
4. After every 10 components, update `audit_state.md`

**Continue until every LWC component is scored.** Then verify:
`scored + skipped + carried_forward == Phase A local LWC count`.

Update `audit_state.md`: mark C5 complete.

### C6 — Profiles and Permissions

This phase does **not** download source bodies, so it runs faster than C1-C5.
Skip `NamespacePrefix != null`.

Run in this order:

1. Inventory Profiles
2. Inventory Permission Sets and Permission Set Groups (local namespace only)
3. Detect overly broad permissions
4. Count PS assignments, identify orphaned and over-assigned PSs
5. Check PSG health (Status = 'Outdated')

#### Key queries for C6

```
soql_query: SELECT Id, Name, UserType FROM Profile

soql_query: SELECT Id, Name, Label, Description, PermissionsModifyAllData,
  PermissionsViewAllData, PermissionsManageUsers, PermissionsAuthorApex
  FROM PermissionSet
  WHERE IsOwnedByProfile = false AND NamespacePrefix = null AND Type != 'Group'

soql_query: SELECT Id, DeveloperName, MasterLabel, Status, Description
  FROM PermissionSetGroup

soql_query: SELECT PermissionSetGroupId, PermissionSetGroup.DeveloperName,
  PermissionSetId, PermissionSet.Name
  FROM PermissionSetGroupComponent

soql_query: SELECT PermissionSetId, PermissionSet.Name, COUNT(Id) assignments
  FROM PermissionSetAssignment
  WHERE PermissionSet.IsOwnedByProfile = false
  GROUP BY PermissionSetId, PermissionSet.Name

soql_query: SELECT COUNT(Id) FROM User WHERE IsActive = true
```

Findings classification:

| Severity | Examples                                                                                    |
| -------- | ------------------------------------------------------------------------------------------- |
| CRITICAL | Non-admin PS with ModifyAllData; orphaned PS with broad access                              |
| HIGH     | PS with ViewAllData on sensitive objects; outdated PSGs; custom Profiles with ModifyAllData |
| MEDIUM   | Overlapping PSs that should be consolidated into PSGs                                       |
| LOW      | Missing descriptions on PSs; unused Profiles                                                |

Write outputs to `./audit_output/intermediate/permissions/`.
Update `audit_state.md`: mark C6 complete.

### C7 — Data Model, Validation Rules, and Formula Fields

**Score every local custom object.** Paginate `CustomObject` where `NamespacePrefix = null`.

For each custom object:

1. `sobject_describe(sObject="<ApiName>")` — get field count, relationship
   count, record type count
2. Score against the 120-point rubric from `sf-metadata`
3. Write summary to `./audit_output/intermediate/metadata/<ObjectApiName>.md`

#### Validation rules

Fetch the **full formula body** so hardcoded values can be detected:

```
tooling_api_query: SELECT Id, EntityDefinition.QualifiedApiName, ValidationName,
  Active, Description, ErrorConditionFormula, ErrorMessage
  FROM ValidationRule WHERE NamespacePrefix = null
```

For each validation rule, scan `ErrorConditionFormula` for anti-patterns using
these regex patterns:

| Pattern (case-insensitive)                                                                                                                                                 | What it catches                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `[a-zA-Z0-9]{15,18}` that matches an Id format (starts with `[0-9a-zA-Z]{3}` and passes Salesforce Id checksum or is a known prefix like `001`, `006`, `00Q`, `701`, etc.) | Hardcoded Record IDs                                          |
| Quoted string literals containing object names that exist in the org (e.g. `"Enterprise"`, `"Gold Partner"`)                                                               | Hardcoded record type / picklist names (fragile if renamed)   |
| `Campaign` or campaign-name string literals                                                                                                                                | Hardcoded Campaign names                                      |
| `Profile` name string literals (e.g. `"System Administrator"`, `"Sales User"`)                                                                                             | Hardcoded Profile names (use `$Profile.Name` sparingly)       |
| URL string literals (`https://`, `http://`)                                                                                                                                | Hardcoded URLs (should use Custom Metadata or Custom Setting) |

Findings for validation rules:

| Finding                                                            | Severity |
| ------------------------------------------------------------------ | -------- |
| Formula contains hardcoded Record ID(s)                            | HIGH     |
| Formula contains hardcoded Campaign name(s)                        | HIGH     |
| Formula contains hardcoded Profile name(s)                         | MEDIUM   |
| Formula contains hardcoded URL(s)                                  | MEDIUM   |
| Formula contains hardcoded record-type or picklist value string(s) | MEDIUM   |
| Active rule with no description                                    | MEDIUM   |
| Rule with no bypass mechanism (`$Permission` or custom setting)    | MEDIUM   |
| Inactive rules (cleanup candidates)                                | LOW      |
| Object with > 20 active rules (complexity risk)                    | MEDIUM   |

#### Formula fields

Fetch formula field definitions for every local custom object:

```
tooling_api_query: SELECT Id, EntityDefinition.QualifiedApiName, DeveloperName,
  QualifiedApiName, DataType, TableEnumOrId, Formula
  FROM CustomField
  WHERE NamespacePrefix = null AND Formula != null
```

> **Note:** The `Formula` field is only available via the Tooling API on
> `CustomField`. In `sfdx-repo` mode, read formula bodies from
> `force-app/main/default/objects/<Object>/fields/<Field>.field-meta.xml`
> (the `<formula>` element).

For each formula field, scan the `Formula` body for the same anti-patterns
listed above for validation rules (hardcoded IDs, Campaign names, Profile
names, URLs, record-type/picklist strings).

Additional formula-field-specific findings:

| Finding                                                            | Severity |
| ------------------------------------------------------------------ | -------- |
| Formula contains hardcoded Record ID(s)                            | HIGH     |
| Formula contains hardcoded Campaign name(s)                        | HIGH     |
| Formula contains hardcoded Profile name(s)                         | MEDIUM   |
| Formula contains hardcoded URL(s)                                  | MEDIUM   |
| Formula contains hardcoded record-type or picklist value string(s) | MEDIUM   |
| Formula references field that does not exist (compile error risk)  | HIGH     |
| Formula exceeds 5 000 characters (readability / compile-size risk) | MEDIUM   |
| Formula uses `VLOOKUP` (deprecated function)                       | MEDIUM   |
| Formula has deeply nested `IF` statements (> 5 levels)             | LOW      |

Write formula field findings to
`./audit_output/intermediate/metadata/formula_fields.md` and persist to
`formula_fields.json`.

Cross-object analysis (beyond per-object scoring):

- Objects with no relationships (orphaned objects)
- Missing descriptions on custom objects
- Outdated API versions (< 55.0)
- Objects with > 100 custom fields (complexity risk)

**Verify:** `scored + skipped + carried_forward == Phase A local custom object count`.

Update `audit_state.md`: mark C7 complete.

### C7b — Unused Custom Fields and Objects

Identify custom fields and custom objects that appear unused. "Unused" means
either (a) no records contain data for the field/object, or (b) the field/object
is not referenced in other org artifacts (Apex, Flows, validation rules, formula
fields, page layouts, reports, list views), or both. Flag each condition
independently — either one in isolation is worth surfacing.

#### Step 1 — Identify custom fields with no data

For each local custom object (from C7), query for custom fields that have zero
populated records. Use a single Tooling API query per object to get all custom
fields, then check population via SOQL:

```
tooling_api_query: SELECT DeveloperName, QualifiedApiName, DataType,
  Description, TableEnumOrId
  FROM CustomField
  WHERE NamespacePrefix = null
    AND TableEnumOrId = '<CustomObject__c>'
```

For each custom field, check whether any record has data:

```
soql_query: SELECT COUNT(Id) total FROM <Object__c> WHERE <Field__c> != null LIMIT 1
```

> **Performance note:** For objects with many custom fields, batch the
> population checks — run up to 10 in parallel where the mode supports it.
> In `sfdx-repo` mode, skip population checks (record data is not available
> locally) and set `has_data: null` in the output JSON. The report generator
> renders this as "Unknown" in all formats.

#### Step 2 — Identify custom objects with no records

For each local custom object, check record count:

```
soql_query: SELECT COUNT(Id) total FROM <Object__c>
```

Objects with `total == 0` are flagged as "no data."

#### Step 3 — Cross-reference analysis (artifact references)

Search for references to each custom field and custom object across org
artifacts. A field/object is "unreferenced" if it does not appear in any of:

1. **Apex classes and triggers** — search for the field/object API name in all
   fetched bodies (from C1/C2 intermediate files)
2. **Flows** — search Flow XML for the field/object API name (from C3
   intermediate files)
3. **Validation rules** — search `ErrorConditionFormula` for the field API name
   (from C7 data)
4. **Formula fields** — search `Formula` body for the field API name (from C7
   data)
5. **Workflow rules** — search criteria and field-update formulas (from C8 data)
6. **Page layouts** — query layout assignments:
   ```
   metadata_read: type=Layout, fullNames=["<Object__c>-*"]
   ```
   Check whether the field appears in any layout section.
7. **Reports and list views** — query via Tooling API:
   ```
   tooling_api_query: SELECT Id, DeveloperName FROM Report
     WHERE DeveloperName LIKE '%<ObjectName>%'
   ```

> **`sfdx-repo` mode:** search for the field/object API name across all files
> in `force-app/` using `grep -r`. For page layouts, check
> `force-app/main/default/layouts/<Object>-*.layout-meta.xml`.

> **Shortcut for large orgs:** If the org has more than 500 custom fields
> total, limit the cross-reference search to fields that already failed the
> population check (no data). Fields with data are less likely to be truly
> unused.

#### Step 4 — Classify and write findings

For each custom field, assign a category:

| Condition                   | Category           | Severity |
| --------------------------- | ------------------ | -------- |
| No data AND no references   | Unused             | HIGH     |
| No data but has references  | Empty              | MEDIUM   |
| Has data but no references  | Unreferenced       | MEDIUM   |
| Has data and has references | Active (no action) | —        |

For each custom object with no records:

| Condition                      | Category           | Severity |
| ------------------------------ | ------------------ | -------- |
| No records AND no references   | Unused             | HIGH     |
| No records but has references  | Empty              | MEDIUM   |
| Has records but no references  | Unreferenced       | MEDIUM   |
| Has records and has references | Active (no action) | —        |

Write findings to:

- `./audit_output/unused_fields.json`
- `./audit_output/unused_objects.json`

See `references/report-input-schema.md` for the JSON schema.

Update `audit_state.md`: mark C7b complete, record counts:

- Unused fields (no data + no references): {n}
- Empty fields (no data, but referenced): {n}
- Unreferenced fields (has data, but not referenced): {n}
- Unused objects: {n}
- Empty objects: {n}
- Unreferenced objects: {n}

### C8 — Workflow Rules

#### Inventory and criteria

```
tooling_api_query: SELECT Id, Name, TableEnumOrId
  FROM WorkflowRule WHERE NamespacePrefix = null
```

For each workflow rule, retrieve the **full metadata** (criteria formula and
actions) so formulas can be inspected:

```
metadata_read: type=WorkflowRule, fullNames=["<ObjectApiName>.<RuleName>", ...]
```

> **`sfdx-repo` mode:** read from
> `force-app/main/default/workflows/<ObjectApiName>.workflow-meta.xml`
> (each `<rules>` element contains `<formula>` and `<criteriaItems>`).

From the metadata, extract:

1. **Criteria formula** (`<formula>` element or `formula` property) — the
   Boolean expression that fires the rule.
2. **Field-update formulas** — each `WorkflowFieldUpdate` may have a
   `formula` property when `operation = Formula`.
3. **Email template references** — from `WorkflowAlert` actions.

#### Anti-pattern scanning

Scan every criteria formula and field-update formula for the same hardcoded-
value patterns used in C7 (Record IDs, Campaign names, Profile names, URLs,
record-type/picklist strings).

Write to `./audit_output/intermediate/workflow_rules/inventory.md`.

Findings:

| Finding                                                               | Severity |
| --------------------------------------------------------------------- | -------- |
| Active Workflow Rule (should migrate to Flow)                         | HIGH     |
| Field updates that may conflict with Flows on same object             | CRITICAL |
| Outbound messages (integration dependency)                            | MEDIUM   |
| Multiple automation types on same object (Workflow + Flow + PB)       | CRITICAL |
| Criteria formula contains hardcoded Record ID(s)                      | HIGH     |
| Criteria formula contains hardcoded Campaign name(s)                  | HIGH     |
| Field-update formula contains hardcoded Record ID(s)                  | HIGH     |
| Field-update formula contains hardcoded value(s) (Profile, URL, etc.) | MEDIUM   |

Update `audit_state.md`: mark C8 complete.

### C8b — Other Declarative Logic (approval, escalation, assignment rules)

Salesforce stores Boolean / formula logic in several additional metadata types.
Inventory each and scan for hardcoded-value anti-patterns.

#### Approval processes

```
metadata_read: type=ApprovalProcess, fullNames=["*"]
```

> **`sfdx-repo` mode:** read from
> `force-app/main/default/approvalProcesses/`.

For each approval process, inspect:

- **Entry criteria formula** (`entryCriteria.formula`)
- **Step criteria formulas** (each `approvalStep.entryCriteria.formula`)

Findings:

| Finding                                                    | Severity |
| ---------------------------------------------------------- | -------- |
| Entry criteria contains hardcoded Record ID(s)             | HIGH     |
| Entry criteria contains hardcoded Campaign/Profile name(s) | MEDIUM   |
| Step criteria contains hardcoded value(s)                  | MEDIUM   |
| Active approval process with no description                | LOW      |

#### Escalation rules

```
metadata_read: type=EscalationRules, fullNames=["Case"]
```

> Escalation rules typically exist only on Case. If the org customises other
> objects, query `metadata_list: type=EscalationRules` first.

Inspect each `<escalationRule>` → `<ruleEntry>` for `<formula>` or
`<criteriaItems>` containing hardcoded values.

#### Assignment rules (Lead & Case)

```
metadata_read: type=AssignmentRules, fullNames=["Lead", "Case"]
```

Inspect each `<assignmentRule>` → `<ruleEntry>` for `<formula>` or
`<criteriaItems>` containing hardcoded values.

#### Auto-response rules (Lead & Case)

```
metadata_read: type=AutoResponseRules, fullNames=["Lead", "Case"]
```

Inspect each `<autoResponseRule>` → `<ruleEntry>` for `<formula>` or
`<criteriaItems>` containing hardcoded values.

#### Consolidated findings for C8b

| Finding                                                      | Severity |
| ------------------------------------------------------------ | -------- |
| Approval entry/step criteria contains hardcoded Record ID(s) | HIGH     |
| Approval entry/step criteria contains hardcoded name(s)      | MEDIUM   |
| Escalation rule criteria contains hardcoded value(s)         | MEDIUM   |
| Assignment rule criteria contains hardcoded value(s)         | MEDIUM   |
| Auto-response rule criteria contains hardcoded value(s)      | MEDIUM   |

Write all C8b findings to
`./audit_output/intermediate/declarative_logic/other_rules.md` and persist
to `other_rules_findings.json`.

Update `audit_state.md`: mark C8b complete.

### C10 — Reports & Dashboards Inventory

Inventory every Report and Dashboard in the org. Identify stale, unused, and
duplicated items.

#### Queries

```
soql_query: SELECT Id, Name, FolderName, LastRunDate, CreatedDate,
  LastModifiedDate, Format
  FROM Report
  ORDER BY FolderName, Name

soql_query: SELECT Id, Title, FolderName, LastViewedDate, CreatedDate,
  LastModifiedDate
  FROM Dashboard
  ORDER BY FolderName, Title
```

> **`sfdx-repo` mode:** Reports and Dashboards are live-only metadata.
> Always query via MCP even when bodies are read from disk.

#### Analysis

For each item, classify:

- **Stale**: no `LastRunDate` / `LastViewedDate`, or last activity > 12 months ago
- **Duplicate name**: multiple reports/dashboards with the same `Name`/`Title`
  in different folders

#### Findings

| Finding                                              | Severity |
| ---------------------------------------------------- | -------- |
| Report/Dashboard never run/viewed                    | MEDIUM   |
| Report/Dashboard not run/viewed in > 12 months       | LOW      |
| Duplicate report/dashboard names across folders      | LOW      |
| Folder with > 50 items (organisational complexity)   | LOW      |
| Report using legacy format (Tabular with no filters) | LOW      |

Write inventory to `./audit_output/intermediate/reports_dashboards/`.
Persist to `reports_dashboards.json`.

**Schema:**

```json
{
  "reports": [
    {
      "name": "Pipeline by Stage",
      "folder": "Sales Reports",
      "format": "MATRIX",
      "last_run_date": "2025-11-01",
      "created_date": "2024-03-15",
      "is_stale": false
    }
  ],
  "dashboards": [
    {
      "name": "Executive KPIs",
      "folder": "Leadership",
      "last_viewed_date": "2026-01-10",
      "created_date": "2024-06-01",
      "is_stale": false
    }
  ],
  "findings": [{ "severity": "MEDIUM", "message": "12 reports have never been run" }]
}
```

Update `audit_state.md`: mark C10 complete.

### C11 — Integration Analysis

Inventory all integration-related metadata: Connected Apps, Named Credentials,
External Services, Outbound Messages, and Platform Events.

#### Queries

```
soql_query: SELECT Id, Name, MasterLabel
  FROM ConnectedApplication

soql_query: SELECT Id, DeveloperName, Endpoint
  FROM NamedCredential
  WHERE NamespacePrefix = null

tooling_api_query: SELECT Id, DeveloperName, Description
  FROM ExternalServiceRegistration

tooling_api_query: SELECT Id, Name, EndpointUrl, ApiVersion
  FROM WorkflowOutboundMessage
  WHERE NamespacePrefix = null

tooling_api_query: SELECT Id, DeveloperName
  FROM PlatformEventChannel
  WHERE NamespacePrefix = null

soql_query: SELECT Id, DeveloperName
  FROM PlatformEventChannelMember
  WHERE NamespacePrefix = null
```

> **`sfdx-repo` mode:** Connected Apps, Named Credentials, and External
> Services are live-only. Always query via MCP.

#### Findings

| Finding                                                     | Severity |
| ----------------------------------------------------------- | -------- |
| Named Credential with deprecated authentication protocol    | HIGH     |
| Connected App with no description                           | LOW      |
| Outbound Message using API version < 50.0                   | MEDIUM   |
| Platform Event with no subscribers (orphaned)               | MEDIUM   |
| External Service with no active references in Flows or Apex | MEDIUM   |
| Named Credential endpoint using HTTP (not HTTPS)            | CRITICAL |
| > 10 Connected Apps (review consolidation opportunities)    | LOW      |

Write to `./audit_output/intermediate/integrations/`.
Persist to `integrations.json`.

**Schema:**

```json
[
  {
    "type": "ConnectedApp",
    "name": "Slack Integration",
    "endpoint": null,
    "findings": [{ "severity": "LOW", "message": "No description provided" }]
  },
  {
    "type": "NamedCredential",
    "name": "ERP_Endpoint",
    "endpoint": "https://erp.example.com/api",
    "findings": []
  }
]
```

Update `audit_state.md`: mark C11 complete.

### C12 — Test Coverage Report

Retrieve Apex test coverage data and identify gaps.

#### Queries

```
tooling_api_query: SELECT ApexClassOrTriggerId, ApexClassOrTrigger.Name,
  NumLinesCovered, NumLinesUncovered
  FROM ApexCodeCoverageAggregate
  ORDER BY ApexClassOrTrigger.Name

tooling_api_query: SELECT PercentCovered
  FROM ApexOrgWideCoverage
```

> **Note:** `ApexCodeCoverageAggregate` only contains data if tests have been
> run recently. If the query returns empty results, note this in findings and
> recommend running all tests before the audit.

#### Analysis

For each class/trigger in the coverage data:

1. Compute `coverage_pct = NumLinesCovered / (NumLinesCovered + NumLinesUncovered) * 100`
2. Cross-reference with C1 class names to identify **classes with zero coverage**
   (present in C1 inventory but absent from coverage aggregate)
3. Flag classes below the 75% deployment threshold

#### Findings

| Finding                                                       | Severity |
| ------------------------------------------------------------- | -------- |
| Org-wide coverage below 75% (deployment risk)                 | CRITICAL |
| Class with 0% test coverage                                   | HIGH     |
| Class with coverage below 75%                                 | MEDIUM   |
| Coverage data is empty or stale (recommend running all tests) | HIGH     |
| Trigger with no test coverage                                 | HIGH     |

Write to `./audit_output/intermediate/test_coverage/`.
Persist to `test_coverage.json`.

**Schema:**

```json
{
  "org_wide_pct": 82.5,
  "classes": [
    {
      "name": "AccountService",
      "lines_covered": 120,
      "lines_uncovered": 30,
      "coverage_pct": 80.0
    }
  ],
  "findings": [{ "severity": "HIGH", "message": "3 classes have 0% test coverage" }]
}
```

Update `audit_state.md`: mark C12 complete.

### C13 — Licensing Analysis

Inventory all license types and their utilisation. Identify waste and capacity
risks.

#### Queries

```
soql_query: SELECT Id, Name, TotalLicenses, UsedLicenses, Status
  FROM UserLicense

soql_query: SELECT Id, PermissionSetLicenseKey, MasterLabel,
  TotalLicenses, UsedLicenses, Status
  FROM PermissionSetLicense

soql_query: SELECT Id, NamespacePrefix, AllowedLicenses, UsedLicenses,
  ExpirationDate, Status
  FROM PackageLicense
```

#### Analysis

For each license:

1. Compute `utilization_pct = UsedLicenses / TotalLicenses * 100`
   (handle TotalLicenses = -1 as "unlimited")
2. Compute `available = TotalLicenses - UsedLicenses`
3. Flag waste (low utilisation) and capacity risk (high utilisation)

#### Findings

| Finding                                               | Severity |
| ----------------------------------------------------- | -------- |
| License with < 10% utilisation (potential cost waste) | HIGH     |
| License with > 90% utilisation (capacity risk)        | MEDIUM   |
| Expired license still present                         | HIGH     |
| Package license expiring within 90 days               | MEDIUM   |
| Permission Set License with 0 assignments             | MEDIUM   |
| License cost optimisation opportunity > $5K annually  | HIGH     |

Write to `./audit_output/intermediate/licensing/`.
Persist to `licensing.json`.

**Schema:**

```json
{
  "user_licenses": [
    {
      "name": "Salesforce",
      "total": 100,
      "used": 75,
      "available": 25,
      "utilization_pct": 75.0
    }
  ],
  "permission_set_licenses": [
    {
      "name": "SalesforceCPQ_CPQStandardPerm",
      "label": "Salesforce CPQ License",
      "total": 50,
      "used": 5,
      "available": 45,
      "utilization_pct": 10.0
    }
  ],
  "package_licenses": [
    {
      "namespace": "SBQQ",
      "allowed": 50,
      "used": 5,
      "expiration_date": "2026-12-31",
      "status": "Active"
    }
  ],
  "findings": [
    {
      "severity": "HIGH",
      "message": "SalesforceCPQ_CPQStandardPerm: 10% utilisation — 45 unused licenses"
    }
  ]
}
```

Update `audit_state.md`: mark C13 complete.

### C14 — Team Evaluation

Analyse user distribution, activity, and role assignment patterns.

#### Queries

```
soql_query: SELECT Id, Name, Username, Profile.Name, UserRole.Name,
  IsActive, LastLoginDate, CreatedDate
  FROM User
  WHERE IsActive = true
  ORDER BY Profile.Name, Name

soql_query: SELECT UserId, COUNT(Id) login_count
  FROM LoginHistory
  WHERE LoginTime = LAST_N_DAYS:180
  GROUP BY UserId

soql_query: SELECT PermissionSetId, PermissionSet.Name,
  AssigneeId, Assignee.Name
  FROM PermissionSetAssignment
  WHERE PermissionSet.IsOwnedByProfile = false
```

#### Analysis

For each active user:

1. Compute `days_since_login` from `LastLoginDate`
2. Count permission set assignments per user
3. Group users by Profile and Role for distribution analysis

Cross-cutting analysis:

- Users per Profile (identify over-used generic profiles)
- Users per Role (identify unbalanced hierarchies)
- Users with no Role assignment
- Admin users (System Administrator profile or ModifyAllData permission)

#### Findings

| Finding                                                       | Severity |
| ------------------------------------------------------------- | -------- |
| User inactive > 90 days (security risk — should deactivate)   | HIGH     |
| User with no Role assigned (visibility gap)                   | MEDIUM   |
| > 10 users on System Administrator profile                    | HIGH     |
| User with > 15 Permission Set assignments (over-permissioned) | MEDIUM   |
| Profile used by only 1 user (consolidation candidate)         | LOW      |
| User created but never logged in                              | MEDIUM   |

Write to `./audit_output/intermediate/team/`.
Persist to `team_evaluation.json`.

**Schema:**

```json
{
  "active_users": 150,
  "users": [
    {
      "name": "Jane Smith",
      "username": "jane@acme.com",
      "profile": "System Administrator",
      "role": "CEO",
      "last_login": "2026-04-01",
      "days_since_login": 6,
      "permission_set_count": 4,
      "login_count_180d": 95
    }
  ],
  "profile_distribution": [
    { "profile": "System Administrator", "user_count": 8 },
    { "profile": "Standard User", "user_count": 42 }
  ],
  "findings": [
    {
      "severity": "HIGH",
      "message": "12 users inactive for > 90 days"
    }
  ]
}
```

Update `audit_state.md`: mark C14 complete.

### C15 — Change History Audit

Retrieve setup audit trail and deployment history to identify change patterns
and risks.

#### Queries

```
soql_query: SELECT CreatedDate, CreatedBy.Name, Action, Section, Display
  FROM SetupAuditTrail
  ORDER BY CreatedDate DESC
  LIMIT 2000

tooling_api_query: SELECT Id, Status, CreatedDate, CreatedBy.Name,
  CompletedDate, NumberComponentsDeployed, NumberComponentErrors
  FROM DeployRequest
  ORDER BY CreatedDate DESC
  LIMIT 100
```

> **Retention note:** SetupAuditTrail retains up to 180 days of history in
> most editions. The 2000-row LIMIT covers approximately 6 months for a
> moderately active org.

#### Analysis

1. Group audit trail entries by `Section` (e.g. "Manage Users", "Customize",
   "Data Management") to show change distribution
2. Identify top changers (users with the most setup changes)
3. Compute deployment success rate: `successful / total * 100`
4. Detect rapid-fire changes (> 20 changes by the same user in a single day)

#### Findings

| Finding                                                      | Severity |
| ------------------------------------------------------------ | -------- |
| Deployment failure rate > 20%                                | HIGH     |
| Changes made by a now-deactivated user                       | MEDIUM   |
| > 50 setup changes in a single day by one user (change risk) | MEDIUM   |
| No deployments in last 90 days (stale org / manual changes)  | LOW      |
| Permission-related changes without documented change request | MEDIUM   |
| Production changes outside business hours (> 50% of changes) | LOW      |

Write to `./audit_output/intermediate/change_history/`.
Persist to `change_history.json`.

**Schema:**

```json
{
  "audit_trail": [
    {
      "date": "2026-04-01T14:30:00Z",
      "user": "Admin User",
      "action": "Changed field-level security",
      "section": "Manage Users",
      "detail": "Changed field Account.Revenue__c"
    }
  ],
  "change_distribution": [
    { "section": "Manage Users", "count": 245 },
    { "section": "Customize", "count": 189 }
  ],
  "top_changers": [{ "user": "Admin User", "change_count": 312 }],
  "deployments": [
    {
      "id": "0Af...",
      "status": "Succeeded",
      "date": "2026-03-28T10:00:00Z",
      "user": "Release Manager",
      "components_deployed": 45,
      "component_errors": 0
    }
  ],
  "deployment_success_rate": 85.0,
  "findings": [
    {
      "severity": "HIGH",
      "message": "Deployment failure rate is 15% (15 of 100 deployments failed)"
    }
  ]
}
```

Update `audit_state.md`: mark C15 complete.

---

## Phase C9 — Completeness Gate (before reports)

Before proceeding to Phase D, verify that every **user-approved** domain is
complete. Read `audit_state.md` and check only the domains the user selected
in Phase B. (For a full audit, check all rows; for a selective audit like
"just Apex and Flows", check only the approved domains.)

| Domain               | Expected (from Phase A)        | Scored | Skipped | Carried Fwd | Match? |
| -------------------- | ------------------------------ | ------ | ------- | ----------- | ------ |
| Apex Classes         | {A1 local Apex class count}    | {n}    | {n}     | {n}         | Y/N    |
| Triggers             | {A1 local Apex trigger count}  | {n}    | {n}     | {n}         | Y/N    |
| Flows                | {A4 active Flow count}         | {n}    | {n}     | {n}         | Y/N    |
| LWC                  | {A4 local LWC count}           | {n}    | {n}     | {n}         | Y/N    |
| Objects              | {A1 local custom object count} | {n}    | {n}     | {n}         | Y/N    |
| Reports & Dashboards | —                              | —      | —       | —           | JSON?  |
| Integrations         | —                              | —      | —       | —           | JSON?  |
| Test Coverage        | —                              | —      | —       | —           | JSON?  |
| Licensing            | —                              | —      | —       | —           | JSON?  |
| Team Evaluation      | —                              | —      | —       | —           | JSON?  |
| Change History       | —                              | —      | —       | —           | JSON?  |

Match = `Scored + Skipped + Carried Fwd == Expected`. (For fresh audits,
Carried Fwd is 0 for all rows.)

For C10–C15 (inventory/findings domains), the gate checks whether the
corresponding JSON output file exists in `./audit_output/`. These domains do
not have component-level scoring, so the JSON? column confirms the file was
written.

**If any approved-domain row shows "N", go back and score the missing
components before generating reports.** Domains the user excluded in Phase B
should be marked "Not audited" and do not block report generation.

---

## Phase D — Reports

Produce three report files in `./audit_output/`. See `references/report-template.md`
for brand tokens (the Salesforce MCP server blue `#417AE4`, cyan `#14DDDD`), HTML CSS, docx-js
patterns, and openpyxl patterns — follow it exactly for consistent output.
If the user provides their own template, use that instead — their template
always takes precedence over the default.

**For incremental audits:** include all components (changed + unchanged) in
reports. Mark each component's status:

- **Re-scored** — changed since last audit, freshly evaluated
- **Carried forward** — unchanged since last audit, previous score retained
- **New** — not in previous audit
- **Removed** — in previous audit but no longer in org

Include a delta summary section showing what changed between audits.

### Word report (`Salesforce_Org_Audit_Report.docx`)

Sections (in order):

1. Executive summary: org, date, full component inventory, overall health score
2. [If incremental] Delta summary: changes since previous audit
3. Apex Classes: scores ranked lowest to highest, top issues per class
4. Apex Triggers: inventory with findings
5. Flows: scores ranked lowest to highest, top issues per flow
6. Process Builders: inventory with migration priorities
7. LWC: scores ranked lowest to highest, top issues per component
8. Profiles & Permissions: hierarchy and findings by severity
9. Data Model: object scores ranked lowest to highest, field/relationship summary
10. Validation Rules: inventory with findings (including formula anti-patterns)
11. Formula Fields: inventory with hardcoded-value findings
12. Workflow Rules: inventory with migration priorities and formula findings
13. Other Declarative Logic: approval, escalation, assignment, and auto-response rule findings
14. Unused Fields & Objects: fields and objects with no data and/or no references in other artifacts
15. Automation Overlap: objects with multiple automation types active
16. Hardcoded Values Summary: cross-cutting view of all hardcoded IDs, names, and URLs found across formulas, validation rules, workflow rules, and other logic
17. Reports & Dashboards: inventory with stale/unused flags
18. Integration Analysis: connected apps, named credentials, external services, platform events
19. Test Coverage: org-wide coverage, per-class breakdown, zero-coverage classes
20. Licensing: licence types, utilisation, waste, capacity risks
21. Team Evaluation: user distribution, inactive users, role gaps
22. Change History: setup audit trail summary, deployment success rate
23. Top 10 recommendations across all domains

Mark any domain that was not fully scored (e.g. "quick pass only") as
"Surface metrics only — body not downloaded."

### Excel report (`Salesforce_Org_Audit_Scores.xlsx`)

One sheet per domain, plus a Summary sheet. Columns per domain:

- Apex Classes: Name, Score, API Version, Lines, Top Issues, Status
- Apex Triggers: Name, Object, Events, Findings, Severity, Status
- Flows: Name, ProcessType, Score, Top Issues, Status
- Process Builders: Name, Object, Criteria Count, Actions, Priority
- LWC: Name, Score, Category Breakdown, Top Issues, Status
- Profiles: Name, UserType, Key Permissions, Findings
- Permission Sets: Name, Label, Assignments, Findings, Severity
- Custom Objects: Name, Score, Field Count, Relationship Count, Top Issues
- Validation Rules: Name, Object, Active, Findings, Severity
- Formula Fields: Name, Object, DataType, Formula Length, Findings, Severity
- Workflow Rules: Name, Object, Action Types, Priority, Formula Findings
- Other Declarative Logic: Type, Name, Object, Findings, Severity
- Unused Fields: Object, Field, Data Type, Has Data, Referenced In, Category, Severity
- Unused Objects: Object, Record Count, Referenced In, Category, Severity
- Hardcoded Values: Component Type, Name, Severity, Finding
- Reports & Dashboards: Name, Type, Folder, Last Run/Viewed, Created, Is Stale
- Integrations: Type, Name, Endpoint, Findings, Severity
- Test Coverage: Class/Trigger Name, Lines Covered, Lines Uncovered, Coverage %
- Team: Name, Username, Profile, Role, Last Login, Days Inactive, PS Count
- Change History: Date, User, Action, Section, Detail
- Licensing: License Name, Type, Total, Used, Available, Utilization %
- Summary: overall score, component counts, finding counts by severity,
  automation overlap matrix, [if incremental] delta summary

(Status column for incremental audits: Re-scored / Carried forward / New)

### HTML report (`Salesforce_Org_Audit_Report.html`)

Single self-contained file (inline CSS/JS, no external requests) with the modern-design and animation kit from `references/report-template.md` §8. Every HTML deliverable in this skill follows the same standard, and every report format meets the §7 visualization minimums (gauge, category breakdown, distribution chart, top-N).

Same content as Word, formatted for browser. Include:

- Score distribution visual — inline SVG chart, animated per report-template.md §7–8
- Links to intermediate source files
- Collapsible PS/PSG hierarchy tree
- Automation overlap matrix table
- [If incremental] Delta highlight: colour-code changed vs unchanged rows

### Standalone documents (12 additional files)

After generating the 3 core reports, produce 12 standalone documents. This
brings the total output to **18 documents** from a single org scan.

Run `generate_reports.py` with `--standalone` to produce all standalone
documents. The script reads the same intermediate JSON files and generates:

#### Data-driven standalone documents (from their own JSON intermediates)

| Document                            | Format | Source JSON               | Key content                                                           |
| ----------------------------------- | ------ | ------------------------- | --------------------------------------------------------------------- |
| `Reports_Dashboards_Inventory.xlsx` | XLSX   | `reports_dashboards.json` | Full inventory with stale flags, folder breakdown                     |
| `Integration_Analysis.html`         | HTML   | `integrations.json`       | Connected apps, named credentials, external services, platform events |
| `Test_Coverage_Report.html`         | HTML   | `test_coverage.json`      | Org-wide %, per-class table, zero-coverage highlight                  |
| `Licensing_Analysis.html`           | HTML   | `licensing.json`          | Licence utilisation, waste, capacity risk, cost optimisation          |
| `Team_Evaluation.html`              | HTML   | `team_evaluation.json`    | User distribution, inactive users, role gaps, admin count             |
| `Change_History_Audit.html`         | HTML   | `change_history.json`     | Setup audit trail summary, deployment success rate, top changers      |

#### Synthesis standalone documents (derived from all collected data)

These documents cross-reference multiple data sources to produce higher-level
analysis. The `generate_reports.py` script builds them from the full
`compute_summary()` output plus all intermediate JSON files.

| Document                           | Format | What it synthesises                                                                                                                                                                                                                                                             |
| ---------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Data_Quality_Report.html`         | HTML   | Record completeness from metadata_scores (field counts, missing descriptions), data hygiene signals from validation rules, formula anti-patterns. During C7, run spot-check completeness queries on the top 5 objects by record count and write results to `data_quality.json`. |
| `Technical_Impact_Assessment.html` | HTML   | Risk scoring: test coverage gaps × code quality scores × permissions severity × automation overlap. Each component gets a composite risk score. Top 20 highest-risk components highlighted.                                                                                     |
| `Architectural_Analysis.html`      | HTML   | Org architecture patterns: automation overlap matrix, trigger handler patterns, object relationship density, integration complexity, naming convention consistency, API version distribution.                                                                                   |
| `Customer_Report.docx`             | DOCX   | **Non-technical, client-facing.** Health score with traffic-light visual. Top 5 risks in business language (no Apex/SOQL jargon). Effort estimates for remediation. Summary of cost optimisation opportunities from licensing analysis.                                         |
| `Strategic_Engagement_Plan.docx`   | DOCX   | Phased remediation roadmap: Phase 1 (Critical, 0–30 days), Phase 2 (High, 30–90 days), Phase 3 (Medium, 90–180 days). T-shirt effort sizing per workstream (Security, Performance, Technical Debt, Automation Modernisation).                                                   |
| `Technical_Team_Briefing.html`     | HTML   | Developer-oriented: code quality hotspots (worst-scoring components), specific fix instructions per top finding type, test coverage gaps per class, change history patterns by developer.                                                                                       |

#### Data Quality — spot-check queries during C7

During C7 (Data Model), after scoring custom objects, run spot-check data
quality queries on the **top 5 objects by record count**:

```
soql_query: SELECT COUNT(Id) FROM <Object>
soql_query: SELECT COUNT(Id) FROM <Object> WHERE <RequiredField> = null
```

For each object, check 3–5 key fields for null/blank rates. Write results to
`data_quality.json`:

```json
{
  "objects": [
    {
      "name": "Account",
      "record_count": 50000,
      "field_completeness": [
        { "field": "Industry", "null_count": 12000, "null_pct": 24.0 },
        { "field": "BillingCity", "null_count": 8500, "null_pct": 17.0 }
      ]
    }
  ],
  "findings": [
    {
      "severity": "HIGH",
      "message": "Account.Industry is null for 24% of records (12,000 of 50,000)"
    }
  ]
}
```

#### Complete file manifest (18 documents)

After Phase D, `audit_output/` should contain:

```
# 3 core reports
Salesforce_Org_Audit_Report.docx
Salesforce_Org_Audit_Report.html
Salesforce_Org_Audit_Scores.xlsx

# 6 data-driven standalone reports
Reports_Dashboards_Inventory.xlsx
Integration_Analysis.html
Test_Coverage_Report.html
Licensing_Analysis.html
Team_Evaluation.html
Change_History_Audit.html

# 6 synthesis standalone reports
Data_Quality_Report.html
Technical_Impact_Assessment.html
Architectural_Analysis.html
Customer_Report.docx
Strategic_Engagement_Plan.docx
Technical_Team_Briefing.html

# Always present
audit_state.md
audit_summary.json
```

### Post-generation review

After all 18 reports are written, ask the user:

> "Reports are ready. Would you like to adjust the style, layout, or structure
> of any of the reports before we wrap up?"

If the user requests changes, regenerate only the affected report(s).

---

## Phase E — Summary to user

Tell the user:

- **Org inventory**: full counts for every category (including formula fields)
- **Overall health score**: weighted average across scored domains
- **Components needing attention**: count below 70, by domain
- **Permissions findings**: count by severity
- **Legacy automation**: active Workflow Rules and Process Builders count
- **Unused fields & objects**: count of unused (no data + no references),
  empty (no data, referenced), and unreferenced (has data, not referenced)
  custom fields and objects — cleanup candidates
- **Automation overlap warnings**: objects with multiple automation types
- **Hardcoded values found**: total count of hardcoded Record IDs, Campaign
  names, Profile names, URLs, and other fragile literals found across
  validation rules, formula fields, workflow rules, and other declarative logic
- **Reports & Dashboards**: total count, stale count, unused count
- **Integrations**: connected apps, named credentials, external services,
  platform events — key findings
- **Test coverage**: org-wide %, count of classes with 0% coverage
- **Team**: active users, inactive > 90 days, users with no role, admin count
- **Change history**: deployment success rate, top changers, change volume
- **Licensing**: utilisation summary, cost optimisation opportunities,
  unused entitlements value estimate
- **Top 3 most common issues per domain**
- **Skipped components**: what was skipped and why (generated classes,
  managed packages)
- [If incremental] **Delta summary**: what changed since last audit,
  score trends (improved / regressed / unchanged)
- **Where report files were saved** (list all 18 documents)

Update `audit_state.md`: mark all phases complete.

---

## Routing reference

| Request                             | Skill            |
| ----------------------------------- | ---------------- |
| Fix or review an Apex class/trigger | `sf-apex`        |
| Fix or review a Flow                | `sf-flow`        |
| Fix or review an LWC component      | `sf-lwc`         |
| Fix a permission or Profile issue   | `sf-permissions` |
| Fix a metadata / data model issue   | `sf-metadata`    |
| Query or update data                | `sf-data`        |
| Visualize architecture or hierarchy | `sf-diagram`     |

## Build order (when fixing issues)

1. **Metadata** — fix data model issues first
2. **Permissions** — update Profiles, PSs, PSGs after metadata is correct
3. **Apex + Flows + LWC** — deploy in parallel if independent
4. **Legacy migration** — migrate Workflow Rules and Process Builders to Flows
5. **Data** — load test data and verify with SOQL after code is deployed

---

## Dependencies

### Salesforce MCP server tools

#### Required

- org_init
- tooling_api_query
- metadata_read
- soql_query
- sobject_describe

#### Optional

- metadata_create
- metadata_update
- fetch_more — paginate through large responses with cursor (`mcp-core`
  mode; see `references/mcp-pagination.md`)

### Local execution tools

- Python 3 — for `pre_score.py` and `generate_reports.py` (Strategy A only)
- Salesforce CLI (`sf`) — for `cli` mode bulk retrieval and queries
- `jq` (optional) — for post-processing CLI JSON exports
- `git` — for `sfdx-repo` mode incremental delta detection

---

## License

MIT License — see [LICENSE](LICENSE) for details.

