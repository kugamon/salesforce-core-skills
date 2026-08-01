# sf-leads

Enrich Salesforce Leads and Contacts with verified web research — titles, industries, websites, LinkedIn profiles — written back via any Salesforce MCP server with per-field citations and approval gates.

## What it does

| Action | Description |
| --- | --- |
| `find` | Gap analysis: which records are missing what, at what rate |
| `enrich` | Research → confidence-rated proposals → approved batch updates (≤10) |
| `report` | Updated/skipped/low-confidence summary with sources |

Hard rules: no writes without approval, no overwriting existing data, no identity guesses, sources cited on every value.

## Examples

- "Find leads missing industry or title and enrich the top 10"
- "Research and fill in the company info for the leads from last week's webinar"
- "Enrich Jane Doe at Acme — I need her current title"

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
