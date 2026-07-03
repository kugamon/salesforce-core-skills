# Handling Large MCP Responses

When an MCP tool response exceeds ~75 k characters, the server stores the
full result as an **artifact** and returns a truncated preview with
retrieval metadata:

```json
{
  "records": [
    /* up to 3 preview records */
  ],
  "instructions": {
    "artifactId": "abc123",
    "artifactUrl": "https://..."
  },
  "_pagination": {
    "nextCursor": "cursor_string"
  }
}
```

Any tool that returns data can produce an artifact — `soql_query`,
`tooling_api_query`, `metadata_read`, `sobject_describe`, etc.

---

## Detecting an artifact response

Check for `instructions.artifactId` in the response. If present, the full
data was **not** returned inline — only a preview was included.

The response may also contain:

- `instructions.artifactUrl` — a signed URL to download the full dataset.
- `_pagination.nextCursor` — a cursor for paging through the artifact.

---

## Retrieval by execution mode

| Mode                      | Strategy                                                                |
| ------------------------- | ----------------------------------------------------------------------- |
| `sfdx-repo`               | Data is on disk — artifact responses are uncommon.                      |
| `cli`                     | Data retrieved via CLI — artifact responses are uncommon.               |
| `mcp-plus-code-execution` | Fetch `instructions.artifactUrl` and write the JSON to a local file.    |
| `mcp-core`                | Page through with `fetch_more(artifactId=..., cursor=...)` (see below). |

### `mcp-plus-code-execution` — download the artifact

Fetch the signed URL and save the result locally:

```
# Pseudocode — use whatever HTTP fetch is available in the environment
response = fetch(instructions.artifactUrl)
write("./output/artifact_abc123.json", response.body)
```

This gives you the **complete dataset** in a single request, ready for
local processing (scoring scripts, jq transforms, report generation).

### `mcp-core` — paginate with `fetch_more`

When you cannot download URLs, page through the artifact:

```
fetch_more(
  artifactId = instructions.artifactId,
  cursor     = _pagination.nextCursor
)
```

**`cursor` is required.** Calling `fetch_more` without a cursor will
return an error. Always pass the `nextCursor` from the previous response's
`_pagination` object.

Each page returns the next chunk of data plus a new `_pagination.nextCursor`
(if more pages remain). Process each page immediately and discard it before
fetching the next to manage context size.

---

## Best practices

1. **Check every MCP response** for `instructions.artifactId` — any tool
   can produce an artifact when the result is large enough.
2. **Prefer `artifactUrl` download** when the environment supports it —
   it is faster and avoids loading large datasets into the conversation.
3. **In `mcp-core`**, process and discard each page before fetching the
   next. Never hold more than one or two pages in context simultaneously.
4. **Artifacts expire after 1 hour.** If you get an expiry error, re-run
   the original query to generate a fresh artifact.
