# Ask first - confirm goal, budget and actions

One card, at most four questions. Pull 14-day ad spend and ACOS by category first so the options carry the store's
numbers. Skip what the user's sentence already answers. The report restates the answers in its first line.

**Q1 - Goal** (recommended first)
- Improve efficiency - hit an ACOS goal of {store ACOS + 3 points}% (Recommended when ACOS is above target)
- Drive sales - grow sales while ACOS stays at or under {x}%
- Expand traffic - more reach and clicks; ACOS can rise up to {x}%
  -> sets `--acos-goal` (both scripts) and `--goal` (budget_room.py); Scale needs the category's ACOS at or under it.

**Q2 - Budget for next month**
- Same total (Recommended) - money moves from campaigns over goal to capped campaigns under goal
- Increase by 10% / 20% (+{amount} a week)
- Decrease by 10% / 20%
  -> `--budget`; a decrease puts lowers first and reports any cut still needed.

**Q3 - Actions you want back**
- Ads, listing and price (Recommended) - full action table with owners
- Ads only - Ad manager rows only
- Report only - plays and goals, no change list hand-off

**Q4 - Scope** (only when more than 10 categories have spend)
- Top 10 by ad spend (Recommended) - about X% of spend · Top 20 · Let me pick

Store: ask only with more than one profile. Defaults when unanswered (or unattended): efficiency at store ACOS + 3
points, same budget, ads + listing + price, top 10 - stated at the top of the report.

Do not ask: the benchmark period, the conversion line, the brand, data coverage. Gaps are reported, not asked. Brand
names for the generic-search filter come from `asinBrand` of the advertised products (plus spacing variants); the report
lists the names used.

Asking first is not the execution confirmation. Writing budgets needs a separate confirmation of the `ready = yes` rows
(SKILL.md Step 5), in any language.
