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
2. Honor user-specified windows. Work with complete Sunday-Saturday weeks contained in
   the request; if it contains no complete week, show covering-week context only and make
   no period-change claim. Default to the last four complete weeks when no current window
   is given. Respect the 90-day cap in the reference.
3. Use the user's terms or ASINs first. For a broad audit, choose 8-10 shopper queries
   from spend-ranked ad rows; stop when the sample is sufficient. Follow the reference
   for ASIN-like values, at most three pages, and the recent-spend check.
4. **Read the current period first.** Reuse that result for coverage; do not make a separate
   routine probe. Pull a baseline only for a change question. Preserve a user-specified
   baseline; otherwise anchor the baseline on the first complete week actually included
   in the comparable current block. A missing trailing week can shorten that block;
   counts alone cannot identify weeks, and a gap in the middle is not a shorter continuous
   window. Use the reference to verify the week sets before making change claims. Show the
   requested, aligned, and usable periods when they differ.
5. Lead with a finding, then a short table of the returned metrics, an evidence-backed next
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
