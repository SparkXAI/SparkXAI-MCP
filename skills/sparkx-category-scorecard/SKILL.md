---
name: sparkx-category-scorecard
description: >-
  Compare advertising performance and available brand peer ranges for one specified
  Amazon category or a confirmed set of ASINs. Read-only and scoped; not a whole-store
  category ranking, budget allocation, or advertising edit.
metadata:
  version: 1.0.2
---

# Category Scorecard

Use existing read-only MCP tools only. No scripts, local execution, or spreadsheet imports.
Use [the MCP data contract](references/data-contract.md) for scoped query shapes and fallbacks.
If the reference is missing, report the incomplete installation and ask for the full Skill
directory instead of fetching files one by one or improvising category scores.
Default to a short Markdown report in the user's language.

## Start with what can be verified

1. Resolve one authorized store with `get_user_authorized_context`. Reuse the user's
   category and any ASIN scope already confirmed. When needed, inspect relevant ASIN
   metadata in a bounded query to propose a mapping; do not equate a BSR label, deal node,
   or word in a product title with a verified browse-category assignment.
2. If the ASIN scope is confirmed, query aggregate ad performance for it with `get_ads_perf`;
   use the requested dates within the tool limit, or the last 14 complete store-local days
   if none were given. For a request over 90 days, report a dated, clearly partial subperiod
   as described in the reference. Show spend, ad sales, and ACOS where
   available, with period and currency. If only part is confirmed, show that subset as such.
   If no scope can be confirmed, show what was verifiable (for example, matching peer data
   or which ASINs need confirmation), then ask one targeted question. Never label store
   or campaign totals as category performance. Do not start with a budget questionnaire.
3. Get a matching brand peer row with `get_peer_benchmark` when a browse node can be verified.
   Give P25/P50/P75 with the node/level, brand, ad type, goal, and latest complete returned
   period. Show the brand's own benchmark value next to its matched peer range; keep local
   ASIN-scope ad metrics separate when their coverage differs. No valid match: finish the
   self-performance report and explain the gap. Account/default-node data is context only
   unless the returned node is verified as the requested category.
   If the peer period does not match the requested dates, label any available peer row as
   separate background; do not imply it covers the requested period.
4. Only if relevant, check a few named campaigns for budget usage or recent budget changes,
   or check inventory signals for named products. Their evidence is separate from the
   category totals. Report data gaps and suggest what a human should verify next.

## Report

- **Category and scope:** store, dates, confirmed ASINs or count, and mapping gaps.
- **Own performance:** returned metrics and optional leading ASINs within that scope.
- **Peer comparison:** matched range and own benchmark metric, or why peers are not comparable.
- **Next check:** up to three evidence-backed observations or follow-ups. Ask no question if
  the available evidence answers the request.

Do not provide a whole-store ranking, inferred category map, 2-by-2 score, budget allocation,
projected TACOS, proposed execution amounts, or a write-ready change list. This Skill never
writes and does not request confirmation to execute. Use the owning edit Skill only for a
separate, explicitly specified edit request.
