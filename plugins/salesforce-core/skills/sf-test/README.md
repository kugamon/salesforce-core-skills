# sf-test

Generate, review, and run Salesforce Apex test classes with a **120-point test-quality scoring rubric** — via any Salesforce MCP server.

## What it does

| Action | Description |
| --- | --- |
| `generate` | Test plan matrix (positive/negative/bulk/permission/async/callout) → test class with @TestSetup, factories, mocks, runAs → deploy → run |
| `review` | Score existing test classes against the 120-point rubric with line-level evidence |
| `run` | Queue via Tooling API, poll, report pass/fail + coverage per class |

The rubric deliberately punishes coverage-without-assertions — a high-coverage test class with weak assertions caps at 60/120.

## Examples

- "Write tests for AccountService"
- "Score the test classes in my org — which ones are coverage padding?"
- "Run all tests and show me classes under 75% coverage"

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
