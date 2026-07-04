# sf-debug

Capture and analyze Salesforce debug logs through the Tooling API — trace flags, log retrieval, exception and governor-limit diagnosis — MCP-first against the live org.

## What it does

| Action | Description |
| --- | --- |
| `trace` | DebugLevel + TraceFlag setup (short expirations, guaranteed cleanup) |
| `logs` | Query ApexLog, fetch bodies via REST, chunked reading for big logs |
| `analyze` | Fatal errors → limit blocks → SOQL-in-loop signature → CPU hotspots → lock diagnosis; output is Diagnosis / Evidence / Fix / Prevention |
| `limits` | Meter analysis with 60%/85% warning thresholds, org-wide top offenders |

Pasted errors get triaged first — validation rules, duplicate rules, and missing-field errors identify themselves without log capture.

## Examples

- "Why am I getting 'Too many SOQL queries: 101' on opportunity save?"
- "Set up debug logging for the integration user and analyze the next failure"
- "Diagnose this UNABLE_TO_LOCK_ROW error"

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
