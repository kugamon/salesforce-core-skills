# Execution Modes

## Tool-name mapping (read this first)

The tool names used across these skills — `org_init`, `soql_query`,
`sobject_dml`, `sobject_describe`, `metadata_create`, `metadata_update`,
`tooling_api_query`, `tooling_api_dml`, `apex_execute` — are **capability
conventions, not literal tool names**. Map each to whatever your connected
Salesforce MCP server actually exposes BEFORE calling anything. Typical
mappings (mcp-salesforce-connector family):

| Convention | Common real tool |
| --- | --- |
| `soql_query` | `run_soql_query` |
| `sobject_describe` | `get_object_fields` |
| `sobject_dml` | `create_record` / `update_record` / `delete_record` (or `bulk_*`) |
| `tooling_api_query` | `tooling_execute` with `query/?q=...` (GET) |
| `tooling_api_dml` | `tooling_execute` POST/PATCH/DELETE on `sobjects/...` |
| `metadata_create` / `metadata_update` | `restful` / `tooling_execute` against Metadata or Tooling endpoints — note CustomObject creation is NOT available via Tooling REST (see sf-metadata) |
| `apex_execute` | `apex_execute` |
| `rest_call` (generic REST / raw endpoint) | `restful` — the escape hatch that reaches endpoints the query and describe tools cannot: `ui-api/object-info/{Object}/picklist-values/...`, `sobjects/{Object}/describe`, `limits/`, sub-resource GETs |
| `org_init` | your server's init/connection tool; if none exists, verify with `SELECT Id FROM Organization LIMIT 1` and proceed |

Never report a capability as missing because a conventional name isn't
present — find the connector's equivalent and record the mapping once in
your working notes.

**When `sobject_describe` maps to a thin tool.** Some connectors'
`get_object_fields` returns only `name`, `label`, `type`, `updateable` —
not enough for a describe-first phase that needs `length`, `nillable`,
`calculated`, or indexability. Recover the richer metadata from the Tooling
API:

```sql
SELECT QualifiedApiName, DataType, Length, IsCompound, IsNillable, IsCalculated
FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'Account'
```

Two caveats. `FieldDefinition` returns **no rows for compound-address child
fields** (`BillingStreet`, `BillingCity`, `BillingState`, `BillingPostalCode`,
`BillingCountry`), so address lengths stay unverifiable on a thin connector —
say so rather than assuming a limit. And describe of any depth does not prove
which of two fields an org actually uses; **populated-rate sampling does**.

**When the connector has no generic REST tool.** The authoritative way to read
active picklist values is the UI API picklist-values endpoint, reached through
`restful`. Without it, fall back to the describe's active-value list, and if
the describe is thin too, record picklist validity as an **unverified
assumption** and propose no picklist writes. Do not substitute a `GROUP BY` of
the stored data — that reports what was written, not what is still active, and
retired values look valid in it. State the limitation in the report.

Calling conventions differ too — some connectors take structured parameters,
others a raw SOQL string, so check the tool's schema before building the call.
Tooling `runTestsAsynchronous` requires POST (GET returns 405), and raw
sub-resource GETs (e.g. `sobjects/ApexLog/{id}/Body`) go through the generic
REST tool, not the query tool.

## Headless runs (no user available)

When running non-interactively (subagent, scheduled task, CI): approval
gates degrade predictably rather than blocking. Read-only steps proceed
with assumptions stated in the output. Org WRITES the skill gates behind
user approval stay **propose-only** unless the caller explicitly granted
write permission for named artifacts. `AskUserQuestion` steps become
"choose the safest default and record the decision." Never silently skip a
gate — record what would have been asked and what was chosen.


All These Salesforce skills support four execution modes. The mode
determines how metadata is retrieved, how large responses are handled, and
what local tooling is available.

Detect the mode **once** at the start of a session and record it in any
state files. Skills may define mode-specific behaviour in their own
SKILL.md; this document covers the shared fundamentals.

---

## Mode 1 — `sfdx-repo` (metadata on disk)

The working directory (or a user-specified path) is a Salesforce DX project
with metadata already retrieved.

**Detection:**

```bash
test -f sfdx-project.json && echo "SFDX project found"
```

If found, read `sfdx-project.json` to locate the source directory (usually
`force-app/main/default`). Confirm the user wants to use local metadata —
it may be stale relative to the live org.

**Capabilities:**

- Read `.cls`, `.trigger`, `.flow-meta.xml`, LWC bundles, and other
  metadata directly from disk — no API calls for body retrieval.
- Use MCP tools only for live-only data (permission assignments, user
  counts, org limits, etc.).
- For incremental operations: use `git log` to detect changed files.
- Code execution (Python, jq, etc.) is available.

---

## Mode 2 — `cli` (Salesforce CLI)

The Salesforce CLI (`sf`) is installed and authenticated to the target org.

**Detection:**

```bash
command -v sf >/dev/null 2>&1 && sf --version
sf org display --target-org <alias-or-username> --json 2>/dev/null
```

Both checks must pass — the CLI must be installed **and** authenticated to
a usable org. Verify the target org matches the org selected during
`org_init()`. If the CLI is present but not authenticated, or if the
orgs differ, warn the user and fall back to `mcp-plus-code-execution`.

**Capabilities:**

- Bulk retrieve via `sf project retrieve start -m <type>`.
- Queries via `sf data query -q "..." --target-org <org> --json`.
- Code execution (Python, jq, etc.) is available.
- Use MCP tools for targeted lookups when CLI is not needed.

---

## Mode 3 — `mcp-plus-code-execution` (MCP + local tooling)

MCP tools are the only connection to Salesforce, but the environment has a
writable filesystem and can execute code (Python, shell, jq, etc.).

This is the typical mode in most AI coding tools with
**OpenAI Codex**.

**Detection:**

Neither `sfdx-project.json` nor an authenticated `sf` CLI is available,
but the environment supports code execution and file writes:

```bash
# Verify code execution
python3 --version >/dev/null 2>&1 || python --version >/dev/null 2>&1
# Verify writable filesystem
test -w . && echo "writable"
```

Both checks must pass. Being able to write files to disk **and** execute
code is the key differentiator from `mcp-core`.

**Capabilities:**

- All metadata via `tooling_api_query`, `metadata_read`, `soql_query`,
  `sobject_describe`, etc.
- **Artifact download**: when a response includes `instructions.artifactUrl`,
  fetch the URL and write the full JSON to a local file for processing.
  See `references/mcp-pagination.md` for details.
- Code execution for post-processing (scoring scripts, report generation,
  jq transforms, etc.).

---

## Mode 4 — `mcp-core` (MCP only)

MCP tools are the only connection to Salesforce, and there is **no local
filesystem or code execution**.

This is the typical mode in **chat interfaces** and **API-only** contexts.

**Detection:**

Fallback when none of the above modes are detected. If `python3 --version`
fails and you cannot write files to disk, you are in `mcp-core`.

**Capabilities:**

- All metadata via MCP tools (same as `mcp-plus-code-execution`).
- **No artifact download** — cannot fetch URLs or write files.
- Large responses must be paged through in-context using
  `fetch_more(artifactId=..., cursor=...)`. See
  `references/mcp-pagination.md` for details.
- Process data in small batches; discard between batches to manage context.

---

## Mode summary

| Mode                      | Body retrieval   | Artifact handling                     | Code execution | Speed   |
| ------------------------- | ---------------- | ------------------------------------- | -------------- | ------- |
| `sfdx-repo`               | Local filesystem | N/A (data on disk)                    | Yes            | Fastest |
| `cli`                     | `sf` CLI bulk    | N/A (CLI writes to disk)              | Yes            | Fast    |
| `mcp-plus-code-execution` | MCP tools        | Download `artifactUrl` to working dir | Yes            | Medium  |
| `mcp-core`                | MCP tools        | `fetch_more` with cursor (in-context) | No             | Slowest |

In all modes, call `org_init()` first to establish the MCP connection.

---

## Plugin root path

Skills reference validation scripts via `${CLAUDE_PLUGIN_ROOT}`. This env
var is set automatically by Claude Code when a plugin is active. Other
hosts should set their own equivalent before invoking skill scripts:

| Host         | Environment variable  |
| ------------ | --------------------- |
| Claude Code  | `$CLAUDE_PLUGIN_ROOT` |
| OpenAI Codex | `$CODEX_PLUGIN_ROOT`  |
| Other        | `$PLUGIN_ROOT`        |

If none of these are set, skills fall back to searching for the script:

```bash
find ~/ -name "<script_name>.py" 2>/dev/null | head -1
```
