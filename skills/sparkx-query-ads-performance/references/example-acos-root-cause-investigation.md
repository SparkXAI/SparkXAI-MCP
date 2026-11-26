# ACOS Root-Cause Investigation (Chaining All 3 Tools)

A common troubleshooting ask: "why did my ACOS go up?" Answering this well requires chaining all 3 tools — but the output should always be framed as **correlated changes / possible contributing factors**, never as a confirmed causal claim. `get_operation_log` tells you a change happened in the same window; it does not prove that change *caused* the ACOS movement (other factors — competition, seasonality, external traffic shifts — are outside what these tools can observe).

## Step 1 — Confirm and quantify the change (get_ads_perf, two periods)

Use the same two-call procedure as the Period-over-Period example: identical length/granularity/filters, joined by `campaign.campaignId_`.

**This week:**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-07-06",
  "dateEnd": "2026-07-12",
  "metrics": ["Spend", "Sales", "ACOS", "Clicks", "CPC", "Conversions", "CVR"],
  "select": ["campaign.campaignId_", "campaign.campaignName_"],
  "orderBy": [{"field": "ACOS", "direction": "DESC"}],
  "pageSize": 500,
  "userContext": "This week's ACOS by campaign to investigate a reported increase"
}
```
**Last week — same shape:**
```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-29",
  "dateEnd": "2026-07-05",
  "metrics": ["Spend", "Sales", "ACOS", "Clicks", "CPC", "Conversions", "CVR"],
  "select": ["campaign.campaignId_", "campaign.campaignName_"],
  "pageSize": 500,
  "userContext": "Last week's ACOS by campaign for comparison"
}
```

No `campaignState` filter here either, for the same reason as the Period-over-Period example: if a campaign got paused this week, filtering to `enabled` would drop it from the current-period call entirely rather than surface it as a "disappeared" campaign worth investigating — and a paused campaign disappearing is itself a plausible explanation for an account-level ACOS shift (the mix of remaining campaigns changed), so excluding it would hide a real answer.

Join by `campaignId_`, compute each campaign's ACOS delta (recomputed from that period's own Spend/Sales, per the Period-over-Period example — never averaged). **Treat large Spend/Sales/ACOS changes on campaigns with meaningful business volume as investigation candidates** — don't claim this precisely quantifies "how much this campaign drove the account-level ACOS change." Account-level ACOS is `total Spend / total Sales` across all campaigns; a rigorous decomposition of how each campaign's individual change contributed to that ratio's movement is more involved than "ACOS delta × spend," and that simple heuristic can misrank contributors. Use it to pick where to look next, not as a precise attribution.

Since `CPC` and `CVR` are also pulled, you can narrow the likely mechanism before even checking the log: a large `CPC` increase points toward bid-side changes; a large `CVR` drop points toward something on the conversion/targeting side rather than bidding.

## Step 2 — Check what changed in that window (get_operation_log)

For the campaign(s) identified in Step 1, query the operation log over the **same window** (this week), scoped to that campaign:

```json
{
  "profileIds": [4404871489220462],
  "dateStart": "2026-07-06",
  "dateEnd": "2026-07-12",
  "resourceIds": [{"idEntity": "campaign", "ids": [298539385213868]}],
  "pageSize": 200,
  "userContext": "What changed on this campaign during the week its ACOS increased"
}
```

Look at `operationType`/`changeField`/`previousValue`/`newValue`/`changedBy` for anything that plausibly relates to the mechanism suggested by Step 1 (e.g. `Keyword Targeting Bid Increased` if CPC rose, `Automatic Targeting Enabled` or targeting changes if CVR dropped).

**If `truncated=true`, follow `sparkx-query-operation-log`'s own recursive date-splitting procedure first** (bisect the window into non-overlapping sub-ranges, repeat until every sub-range returns `truncated=false`) — do **not** jump straight to adding an `operationType`/`actionType` filter as the fix. Narrowing by type changes *what you're searching for*, not just how much of it you retrieve — if the real cause was some other kind of change you didn't anticipate (e.g. a placement adjustment when you'd guessed bid changes), a type filter would silently hide it. Only fall back to a type filter if a single day is still `truncated=true` on its own (the date-split floor) or the user explicitly said they only care about one type of change — and if you do narrow by type, say plainly that the result is a partial view of that campaign's changes, not its complete history.

## Step 3 — Check current configuration for additional context (get_entity_metadata)

```json
{
  "profileIds": [4404871489220462],
  "entity": "campaign",
  "filters": {"campaignId": {"in": [298539385213868]}},
  "userContext": "Current config of the campaign under investigation"
}
```

This tells you the campaign's *current* `biddingStrategy`, `dailyBudget`, `targetingType`, etc — useful to confirm whether a change surfaced in Step 2 is still in effect, or to notice a config detail (e.g. `biddingStrategy: autoForSales`) that's relevant context even if it didn't change this week.

## Step 4 — Present findings as correlation, not proven causation

**Correct framing**: "Campaign X's ACOS rose from 22% to 41% this week, driven mainly by a CPC increase (from $0.80 to $1.35). The operation log shows a manual bid increase on 3 keywords in this campaign on 2026-07-08, changed by [operator]. This is a plausible contributing factor, though other factors (competition, seasonality) could also be involved — the data available doesn't let us confirm it's the sole cause."

**Avoid**: "The ACOS increase was caused by the bid change on 2026-07-08." — stating a single change as *the* cause overstates what a time-correlation between a metric shift and a logged change can actually prove. If no operation-log entry lines up with the metric shift at all, say that too ("no logged changes to this campaign in that window — the shift may be driven by an external factor such as competition, seasonality, or marketplace-wide trends, which aren't visible through these 3 tools") rather than implying an explanation exists when none was found.
