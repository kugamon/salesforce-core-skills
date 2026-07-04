# sf-security

Audit Salesforce orgs and codebases for security vulnerabilities with a **100-point scored report** and an **AppExchange security review readiness checklist** — via any Salesforce MCP server.

## What it does

| Action | Description |
| --- | --- |
| `audit` | Org-wide scan: CRUD/FLS, injection, sharing, secrets, Lightning security, PII — scored report in Word/Excel/HTML |
| `review` | Targeted scan of named classes/components with line-level findings |
| `fix` | Prioritized remediation (Critical → Low) deployed via MCP, then re-scored |

Any Critical finding caps the grade — a 92-point org with one hardcoded secret is not "Excellent". Includes the ISV-side AppExchange checklist: blockers vs advisories, plus the false-positive documentation format reviewers accept.

## Examples

- "Run a security audit on my org"
- "Is this codebase ready for AppExchange security review?"
- "Check OrderController for SOQL injection and CRUD/FLS issues"

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
