# Period-over-Period Comparison and Top Movers

One of the most common real questions: "how did this week compare to last week" and its natural follow-up, "which campaigns/keywords moved the most." Both require the same careful two-call procedure — get this wrong and you'll misreport growth, miss new/disappeared entities, or compute mathematically invalid ratios.

## Step 1 — Issue two structurally identical calls

**Period A (this week):**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-07-06",
  "dateEnd": "2026-07-12",
  "metrics": ["Impressions", "Clicks", "Spend", "Sales", "Conversions"],
  "select": ["campaign.campaignId_", "campaign.campaignName_"],
  "pageSize": 500,
  "userContext": "This week's campaign performance for WoW comparison"
}
```
**Period B (last week) — SAME length, SAME granularity, SAME filters as Period A:**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-29",
  "dateEnd": "2026-07-05",
  "metrics": ["Impressions", "Clicks", "Spend", "Sales", "Conversions"],
  "select": ["campaign.campaignId_", "campaign.campaignName_"],
  "pageSize": 500,
  "userContext": "Last week's campaign performance for WoW comparison"
}
```

**⚠️ No `campaignState` filter above, deliberately.** A general account-level WoW comparison should include paused/archived campaigns too — otherwise a campaign that was active last week and got paused this week never appears in Period A at all (it fails "currently enabled" in the *current* state, which is what `campaign.campaignState_` reflects), so it silently vanishes from **both** periods instead of correctly showing up as "disappeared" in Step 2. That defeats the whole point of a disappeared-entity analysis. Only add `{"campaign.campaignState_": "enabled"}` if the user specifically asked to scope the comparison to "my currently active campaigns" — and if you do, say so explicitly and don't then claim to explain drops via pausing/archiving, since those campaigns are excluded from the comparison outright, not captured as a visible "disappeared" row.

**Requirements for the two calls to be comparable:**
- **Date-range length depends on what kind of comparison this is — don't force strict equal-length in every case:**
  - **Week-over-week, or any rolling/fixed-length window** (e.g. "last 7 days vs the 7 days before that"): require **exact equal length** (7 vs 7, not 7 vs 30) — comparing different-length windows produces meaningless deltas, as in the example above.
  - **Full calendar month-over-month** (e.g. "July vs June"): calendar months are **not** the same length (28-31 days) — do **not** artificially force them to match by truncating the longer month or extending the shorter one, since that would misrepresent "July" as something other than all of July. Instead, compare the two full calendar months as-is, and **explicitly note the day-count difference** to the user (e.g. "July has 31 days, June has 30"). If the user cares about rate/efficiency rather than raw totals, additionally compute each month's **daily average** (`total ÷ day count`) alongside the raw totals, since a raw total comparison between a 31-day and a 30-day month is otherwise misleading.
  - **Month-to-date (e.g. "this month so far vs last month so far")**: align both periods to the **same number of elapsed days** (e.g. "July 1-19" vs "June 1-19", not all of June) — this is a case where equal length is correct and expected, unlike the full-calendar-month case above.
- **Same granularity** — if Period A is grouped by week, Period B must be too (don't compare a daily breakdown to a weekly one).
- **Same filters in both calls, whatever you choose** — if you do add `campaignState` or any other filter to Period A, Period B must use the identical filter, or you're comparing different populations, not the same campaigns over time.
- **Both `select` include `campaign.campaignId_`** (the ID, not just the name) — see Step 2.
- **Fully paginate both calls** (`hasNextPage` loop, or a `pageSize` large enough to get everything in one page) **before** comparing — do not take "Top 10 of Period A" and "Top 10 of Period B" independently and then compare those two Top-10 lists. A campaign ranked #11 in Period A that jumped to #3 in Period B would be invisible if you only fetched each period's own Top 10. Pull the full comparable population from both periods first, then rank/filter on the merged, joined result.

## Step 2 — Join by ID, not by name

**Align rows using `campaign.campaignId_` (or `campaignId_`/`targetId_`/etc, whatever ID field applies to the entity you're comparing) — never by `campaignName_`.** Campaign names can be renamed between periods, and two different campaigns can legitimately share a name. Build a lookup keyed by ID for each period's result set, then join:

- **In both periods** → a normal comparison row.
- **In Period A only (new)** → Period A is the current/this-week period, so a row appearing only here is new to this period. Its "prior period" value is absent, not zero — see Step 4 on how to handle the % change for these.
- **In Period B only (disappeared)** → Period B is the prior/last-week period, so a row appearing only here existed/had activity last week but not this week (paused, deleted, or simply zero activity this period). Report it separately — don't silently drop it, and don't show it with `0` values that could be misread as "this week's number is zero" without context.

## Step 3 — Recompute derived metrics, don't average them

The two example requests above only ask for base metrics (`Impressions`, `Clicks`, `Spend`, `Sales`, `Conversions`) — they do **not** include `ACOS`/`CTR`/`CVR`/`ROAS`. If you need those for each period's row, either (a) add them to `metrics` in both calls so the API computes them per-period directly, or (b) compute them yourself from the base metrics each period already returned:

```
ACOS = Spend / Sales × 100
CTR  = Clicks / Impressions × 100
CVR  = Conversions / Clicks × 100
ROAS = Sales / Spend
```

Either way, compute/request each period's derived metric **independently from that period's own totals**. The mistake to avoid is a **third**, blended calculation — e.g. do not average Period A's ACOS and Period B's ACOS to produce some kind of "combined" ACOS; each period's ACOS stands on its own. (Same underlying principle as merging split time-windows in the aggregation-over-time example — never average pre-computed ratios across different underlying sums.)

## Step 4 — Compute deltas, handling zero denominators explicitly

```
change = Period A (this week) − Period B (last week)
change % = change / Period B × 100        [ONLY if Period B ≠ 0]
```

- **If Period B's value is `0` and Period A's is nonzero** (or the campaign is "new" per Step 2): there is no valid percentage — division by zero. Report this as "new" or "N/A (no prior-period baseline)", never as "+∞%" or a fabricated large number.
- **If both periods are `0`**: change % is `0` or "flat" / "no activity in either period" — don't compute `0/0`.
- **If Period A is `0` and Period B was nonzero** (a "disappeared" entity per Step 2): this is a `-100%` change if you want to express it that way, but it's often clearer to just say "no longer active this period" alongside the prior period's value.

## Step 5 — Sort the merged, joined result for "Top movers"

Once you have one row per entity (by ID) with both periods' values and a computed `change`/`change %`, split into three buckets first, then rank:

- **New / disappeared entities** (per Step 2) — list these **separately**, not mixed into a % or absolute ranking. They have no valid `change %` (division by zero) and forcing them through a floor filter below would just silently drop them from view instead of surfacing them as the "new" or "disappeared" finding they actually are.
- **Top movers by absolute change** (entities present in both periods) — sort by e.g. `Spend` change in dollars. To judge "is this campaign big enough to matter" before ranking, use **`max(Period A Spend, Period B Spend)`** as the size filter (not just one period) — since a campaign that shrank from big-to-small still had real weight worth flagging, even though its *current* value alone might look small.
- **Top movers by % change** (entities present in both periods) — `change %` divides by **Period B** (the prior-period value, the denominator — see Step 4), so the floor filter that actually protects against small-base blowups must be on **Period B, not Period A**: e.g. `{"Period B Spend": ">=": 100}`. Filtering on Period A instead does not work — a campaign going from $1 (Period B) to $101 (Period A) would pass an "`Period A Spend > 100`" filter and still show as a meaningless "+10000%" mover; flooring Period B is what actually excludes that case.

Report both the raw values (Period A, Period B) and the computed delta in all three buckets — don't just show the % change alone, since "+45%" is meaningless to the user without knowing whether that's $10 or $10,000.
