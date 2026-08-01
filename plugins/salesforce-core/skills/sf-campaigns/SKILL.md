---
name: sf-campaigns
plugin: salesforce-core
argument-hint: '[report|analyze|compare] {campaign-name} ...'
metadata:
  version: 1.0.0
description: >
  Analyzes Salesforce campaign performance via a Salesforce MCP server —
  member counts, response and conversion rates, pipeline generated, ROI, cost
  per lead, and lead-source patterns. Use when the user asks to analyze
  campaigns, check campaign performance or ROI, asks "which campaigns are
  working", wants a campaign report, campaign metrics, campaign member
  analysis, or lead source analysis.
  Usage: /sf-campaigns [report|analyze|compare] {campaign-name} ...
---

# Salesforce Campaign Analysis

Marketing analyst for Salesforce campaigns. Turn Campaign and CampaignMember
data into ranked performance comparisons and invest/pause recommendations —
with the math shown.

## Dispatch

| Argument or intent                          | Workflow |
| ------------------------------------------- | -------- |
| `report`, "how are campaigns doing"         | Portfolio Report (all active) |
| `analyze` + name, "deep dive on X"          | Single-Campaign Deep Dive |
| `compare`, "A vs B", "rank my campaigns"    | Comparison & Ranking |

Initialize the org connection first (`org_init` convention — see
`references/execution-modes.md`).

## Portfolio Report

1. Query active campaigns:

```sql
SELECT Id, Name, Type, Status, StartDate, EndDate, NumberOfLeads,
       NumberOfContacts, NumberOfResponses, NumberOfConvertedLeads,
       NumberOfOpportunities, NumberOfWonOpportunities,
       AmountAllOpportunities, AmountWonOpportunities,
       BudgetedCost, ActualCost
FROM Campaign WHERE IsActive = true ORDER BY StartDate DESC LIMIT 50
```

2. Compute per campaign (guard every division against null/zero):

| Metric | Formula |
| --- | --- |
| Members | NumberOfLeads + NumberOfContacts |
| Response rate | NumberOfResponses / members |
| Conversion rate | NumberOfConvertedLeads / NumberOfLeads |
| Pipeline generated | AmountAllOpportunities |
| Win amount | AmountWonOpportunities |
| ROI | (AmountAllOpportunities − ActualCost) / ActualCost × 100 |
| Cost per lead | ActualCost / NumberOfLeads |
| Budget variance | ActualCost − BudgetedCost |

3. Present ranked by ROI (or pipeline when costs are unrecorded — say which
   and why), then close with recommendations: increase / maintain / pause /
   restructure per campaign, grounded in the numbers.

Campaigns with no ActualCost make ROI meaningless — flag them as a data
hygiene finding rather than silently ranking them last.

## Single-Campaign Deep Dive

Pull member detail and work the funnel:

```sql
SELECT Id, LeadOrContactId, Status, HasResponded, FirstRespondedDate,
       Lead.Name, Lead.Company, Lead.LeadSource, Lead.IsConverted,
       Contact.Name, Contact.Account.Name
FROM CampaignMember WHERE CampaignId = '<id>' LIMIT 2000
```

Report: funnel (added → responded → converted → opportunity → won), response
timing distribution (FirstRespondedDate − campaign StartDate), member-status
breakdown, and the influenced-opportunity list
(`SELECT ... FROM Opportunity WHERE CampaignId = '<id>'` plus
OpportunityContactRole paths when campaign influence matters). Note the
attribution model in use — primary campaign source vs influence — because the
same campaign can look brilliant under one and invisible under the other.

## Comparison & Ranking

Same metrics across the named campaigns (or by Type across the portfolio),
plus pattern analysis: which LeadSource values convert best, seasonal/timing
effects when StartDates span quarters, and campaign-type benchmarks (webinar
vs event vs listing vs nurture). Rank on the metric that matches the user's
goal — pipeline efficiency (ROI) and volume (members) rarely agree.

## Output

Tables for rankings and funnels, per report-template.md §7 instincts — and
when the user wants a document deliverable, follow
`sf-audit/references/report-template.md` §7–8 (visualizations, single-file
animated HTML) rather than dumping tables into prose.

## Cross-skill handoffs

- Query tuning or bulk exports → **sf-data**
- Campaign-sourced leads needing enrichment before scoring → **sf-leads**
- Full org marketing-data hygiene → **sf-audit** (data quality section)

## Custom-field discernment (customized orgs)

Standard fields aren't always where the truth lives. Before computing
metrics in an unfamiliar org:

1. Describe Campaign (and Opportunity when computing pipeline) and list
   populated custom fields whose names shadow the standard metrics —
   `Actual_Spend__c` beside an empty `ActualCost`,
   `Total_Contract_Value__c` beside a stale `Amount`, custom member-status
   fields beside `Status`.
2. Detect shadowing with a sampling query: compare populated-rate and
   recency of the standard field vs the candidate
   (`SELECT COUNT(Id), COUNT(ActualCost), COUNT(Actual_Spend__c) FROM Campaign`).
3. When a shadow candidate wins on population, **ask the user which field
   is authoritative before computing** — a confident ROI from the wrong
   field is worse than a question. Record the choice in the report's
   methodology note so the numbers are auditable.

## Demo mode (no org)

The repo ships synthetic data at `sample-data/` (campaigns.csv,
campaign_members.csv). When no Salesforce MCP server is connected — or the
user asks for a demo — run the same workflows against those CSVs and say
so in the output. The dataset contains deliberate hygiene findings
(missing costs, zero-win campaigns) worth surfacing.
