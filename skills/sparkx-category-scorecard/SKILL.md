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

## Quadrant placement, only when both axes are verified

Offer the 2-by-2 only when **both** coordinates rest on verified data, and only when the
request is about what to do rather than what the numbers are. Otherwise name the axis that is
missing and stop there. An unverified placement is the failure this gate exists for: a
confident-looking verdict resting on an Unknown bucket or an account-level peer row.

The quadrant is the only part that needs `sqp:read` and the `MCP_tool_SQP_ABA` permission.
**Missing it skips the quadrant and nothing else** - own performance and any usable peer range
are delivered as normal, and the report says the market axis was not accessible, which is a
permission gap rather than a finding about demand. The same applies where SQP has no coverage:
Vendor profiles and marketplaces outside US, CA, UK, DE, FR, IT, ES and JP have no market axis
at all.

- **x - shoppers buy vs market:** own purchases per click over the market's, from a
  `marketAsinQuery` pull for the confirmed ASINs over the same complete weeks (see the
  reference). Needs the confirmed ASIN scope; a category guess does not qualify. Line at 0.80x.
- **y - ads vs peers:** the brand's value against the peers' median within one matched row,
  from a peer benchmark on a **verified** browse node. Account-level rows, default-node rows,
  and nodes inferred from a BSR label or a product title do not qualify. **The goal picks the
  metric** - conversion reads ROAS, consideration reads cost per click, awareness reads CPM -
  so the comparison is decided before the row is read, never chosen from whichever number in
  that row favours a conclusion. **Each metric has its own direction, and the axis is "at or
  better than the median" either way:** ROAS at or above the peers' median qualifies, cost per
  click and CPM at or below it qualify. Say which metric and which direction is being read,
  and never let a cost metric's "lower" be read as the losing side.

|  | Ads at or better than peers' median | Ads worse than peers' median |
|---|---|---|
| **Buy >= 0.80x the market** | Scale | Fix ad cost |
| **Buy < 0.80x the market** | Fix listing | Fix first |

**The two axes must describe the same thing before they can be combined.** Align them first:
the same complete weeks, and the same brand and node as the confirmed ASIN scope. Two axes that
each have data are not a quadrant - an x built on four weeks of two products against a y built
on one week of the brand's whole category would still land on `Scale` while describing two
different businesses. **When they cannot be aligned, show the two readings side by side with
their own periods and scopes, and attach no quadrant label.** There is no indicative placement.

Give both coordinates, the weeks each covers, and the node the peer row came from. One scope is
one point: say which quadrant it sits in and why; do not draw a chart of a single bubble. The
placement reads two numbers - it is not an instruction and never authorizes a budget change,
a bid change or any edit.

## Report

- **Category and scope:** store, dates, confirmed ASINs or count, and mapping gaps.
- **Own performance:** returned metrics and optional leading ASINs within that scope.
- **Peer comparison:** matched range and own benchmark metric, or why peers are not comparable.
- **Quadrant:** only if both axes were verified - the quadrant, both coordinates and their
  weeks. Otherwise one line naming the axis that could not be verified.
- **Next check:** up to three evidence-backed observations or follow-ups. Ask no question if
  the available evidence answers the request.

Do not provide a whole-store ranking, inferred category map, an unverified or multi-category
2-by-2, budget allocation, projected TACOS, proposed execution amounts, or a write-ready
change list. This Skill never writes and does not request confirmation to execute. Use the owning edit Skill only for a
separate, explicitly specified edit request.
