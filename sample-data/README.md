# Sample Data — try the skills without a Salesforce org

Synthetic datasets for zero-setup demos. All names, companies, emails
(`*.example.com`), IDs (`*SAMPLE*`), and numbers are fictional.

| File | Rows | Feeds | Deliberate quirks to find |
| --- | --- | --- | --- |
| `campaigns.csv` | 12 campaigns | **sf-campaigns** | Two campaigns missing `ActualCost` (ROI can't be computed — data hygiene finding); one over budget; two with zero wins |
| `campaign_members.csv` | ~300 members | **sf-campaigns** | Mixed response statuses across campaign types |
| `leads.csv` | 40 leads | **sf-leads** | Missing titles/industries/websites at realistic rates; 4 wrong-domain emails (10% — records 5, 13, 27, 33, all pointing at `northwind.example.com` while the Company says otherwise: the de-anonymization misattribution pattern), plus emails from de-anon sources (`Leadpipe`/`RB2B`) that should be treated as unverified; mostly blank phones |

## Try it

Point Claude at this folder and ask:

> "Using the sample data in sample-data/, which campaigns are actually working? Rank by ROI and flag data problems."

> "Run a gap analysis on sample-data/leads.csv — which records need enrichment, and which emails look wrong?"

The skills follow the same workflow as against a live org — the CSVs simply
stand in for the SOQL results. Enrichment writes are proposed, not executed
(there's no org to write to).
