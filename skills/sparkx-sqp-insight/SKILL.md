---
name: sparkx-sqp-insight
description: >-
  Diagnose Amazon Search Query Performance (SQP) for selected search terms or ASINs.
  Compare own and market demand, purchase share, conversion, and weekly ABA evidence;
  use ad performance and change history as context when asked. Read-only, no execution
  or budget plan. Use for SQP, market share, search-term drops, and launch traction.
metadata:
  version: 1.0.2
---

# SQP Insight

Use existing read-only MCP tools only. No local execution, spreadsheet imports, or scripts.
Read [MCP queries and evidence rules](references/data-sources.md) for the request shapes.
If the reference is missing, report the incomplete installation and ask for the full Skill
directory instead of fetching files one by one or improvising the workflow.
Report in the user's language; keep tool labels, search terms, and ASINs intact.

## Start with an answer

1. Resolve one authorized store with `get_user_authorized_context`. Use the store and scope
   already provided; only ask if several authorized stores match or none can be resolved.
   SQP covers Seller profiles in US, CA, UK, DE, FR, IT, ES and JP, subject to data coverage.
2. Use the user's terms or ASINs first. For a broad audit, sample up to 10 actual shopper
   queries from spend-ranked ad rows, with bounded paging if the first page is mostly
   product-page traffic. Exclude product-page ASIN values; show the sample scope and never
   label it a store-wide ranking. For broad scope,
   a successful recent-spend check can avoid unnecessary SQP calls; see the reference.
3. Honor user-specified dates for both periods. Compare only complete Sunday-Saturday
   weeks contained in each requested range. If only the current period is given, use as
   many consecutive complete prior weeks as are included in the current comparison, ending
   the day before its first included week. Do not build a baseline from the originally
   requested day count or include service-expanded boundary weeks in the comparison.
   If either period contains no complete weeks, show covering-week context only and do
   not report a period-over-period change. Only when neither period is supplied, default
   to the last four complete weeks and, for a change question, the preceding four.
   Show requested and analyzed dates when they differ. Respect the 90-day cap and
   coverage checks in the reference. Prefer one aggregate per term per matched period;
   use weekly rows for ABA or when the actual weekly pattern matters.
4. Lead with a finding, then a short table of the returned metrics, an evidence-backed next
   check, and data gaps. Give a partial result first if it is useful. Ask a single focused
   follow-up only when missing scope or evidence would change the answer.

## Choose the evidence

- **Term or store sample:** `marketSearchQuery` for own vs market counts, shares and rates.
  Compare like metrics on matched coverage; flagged low-sample rates are not evidence.
- **Product on a term:** `marketAsinQuery` for the requested ASINs. Compare returned rows;
  repeated market counts across ASINs are not additive.
- **ABA:** a separate weekly `marketSearchQuery` pull for the same terms when needed. Show rank
  and concentration, not search volume inferred from rank. Top-three ASINs are most clicked,
  not necessarily competitors.
- **Change or launch:** optionally confirm timing with `get_operation_log` and read matching
  scoped ad metrics with `get_ads_perf`. Report patterns, not causality. SQP includes organic
  and paid activity with a different attribution window from ads. Do not subtract ad orders
  from SQP purchases or infer revenue from SQP.

## Limits

No exhaustive store audit, merged cross-ASIN market totals, modeled lost orders, automated
opportunity ranking, or bid/budget sizing. Give human follow-up recommendations only, not
write-ready rows, executable plans or files. A separate request for a specific edit belongs to
the owning edit Skill and its own confirmation workflow. Default to a Markdown chat report.
