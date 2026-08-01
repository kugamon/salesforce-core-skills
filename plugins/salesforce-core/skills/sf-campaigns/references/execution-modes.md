# Execution Modes

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
