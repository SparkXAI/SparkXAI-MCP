---
name: sparkx-query-market-data
description: >-
  Query Amazon SQP / ABA market search-term demand, own-store share and top-3 clicked ASINs via
  get_market_search_perf, or Sponsored Ads brand peer benchmarks (P25 / P50 / P75) via
  get_peer_benchmark. Use for named-term search volume and share, competitor click candidates,
  or whether ACOS / ROAS differs from peers. SQP is weekly; benchmarks are weekly or monthly.
  One authorized store per call. This skill evaluates supplied terms; it cannot discover
  unnamed market terms. For the store's own ad metrics use sparkx-query-ads-performance;
  for campaign settings use sparkx-query-entity-metadata.
  For targeted SQP diagnosis use sparkx-sqp-insight;
  for performance and peer ranges in a specified category use sparkx-category-scorecard.
metadata:
  version: 1.0.1
---

# Query Market and Peer Data

Two read tools answering two different questions. Both are **single-store and outside your own
ad data** - neither joins to campaigns, and **neither has a daily grain**.
`get_market_search_perf` is weekly only; `get_peer_benchmark` takes `WEEK` (default) or
`MONTH`.

| Tool | Answers | Reference |
|---|---|---|
| `get_market_search_perf` | How big is the demand for a term, how much of it do we get, who else is taking it | [`references/sqp-aba.md`](references/sqp-aba.md) |
| `get_peer_benchmark` | Are our numbers good or bad compared with similar brands | [`references/peer-benchmark.md`](references/peer-benchmark.md) |

Call `get_user_authorized_context` first. Both tools take **exactly one** authorized profile.
For Benchmark, pass `profileId` as a positive JSON integer. An array is accepted when every entry
is that same authorized ID. Start at `page: 1` with `pageSize` from 1 to 10,000 (default 1,000).
While `meta.hasNextPage` is true, increment only `page` to read the remaining rows.

**The two tools sit behind two different permissions, and neither is the ads-performance one.**
A token that reads ad performance cannot necessarily read either of these, so a failure here is
an authorization gap, not a bad query - name the missing one instead of retrying:

| Tool | Token scope | Menu permission |
|---|---|---|
| `get_market_search_perf` | `sqp:read` | `MCP_tool_SQP_ABA` |
| `get_peer_benchmark` | `benchmark:read` | `MCP_tool_benchmark` |

Each scope unlocks only its own tool, and a token issued before these scopes existed has
neither - it has to be re-authorized.

## Pick the tool from the question, not from the data source

- "How many people search X" / "what share do we have" / "which terms should we add" /
  "who is taking the clicks" -> `get_market_search_perf`
- "Is 30% ACOS high" / "what target should I set" / "how do we compare with the industry" /
  "did peers move too" -> `get_peer_benchmark`
- "Why did spend drop" -> usually **both**: the account tells you what changed, the market
  tells you whether it changed for everyone.

Many real questions need the account first. Find the terms, campaigns or categories worth
asking about with `get_ads_perf` / `get_entity_metadata`, then bring only those here. Pulling
the whole market and filtering afterwards is slow and usually hits the row cap.

## What both tools share

**Weeks run Sunday to Saturday.** On `get_market_search_perf`, `dateStart` is aligned **back**
to its Sunday and `dateEnd` **forward** to its Saturday, so the window you get is wider than the
one you asked for; `get_peer_benchmark` expands the dates to covering periods the same way, in
weeks or months depending on `timeUnit`. Say the actual window in the answer. Requested span is
at most 90 days on both.

**Market search data covers Seller profiles in US, CA, UK, DE, FR, IT, ES and JP only.**
Anywhere else, or a Vendor profile, has no SQP / ABA data at all - that is a coverage gap, not
a finding about the store. **Coverage also depends on the tenant being onboarded for this data**:
a Seller profile in a covered marketplace with ad spend can still return zero rows. An empty
result on its own does not prove which of the two it is - the weeks, the terms or the ASINs asked
for can also come back empty - so report it as "no data returned; tenant onboarding status to be
confirmed" and name what would settle it, rather than asserting either "not onboarded" or "no
demand" (`references/sqp-aba.md`, "Coverage limits").

**ABA columns come only from weekly `marketSearchQuery` rows.** `marketAsinQuery` carries none,
and neither does any aggregated row, so a run that needs both the per-ASIN view and ABA makes two
calls. The field names and the `abaStatus` flag are in `references/sqp-aba.md`.

**There is no daily grain.** If the user asks about one day, or compares two days, say so and
answer with the week containing that day as background - do not silently present a week as if
it were the day.

**Missing periods are not filled and are not zero**, but "missing" and "filtered out" are two
different things and only one of them is worth telling the user about:

- A week genuinely absent from the data is a gap. For a market-only query the response
  **names the missing weeks for you** - read them out of the response rather than deriving
  them from the rows you got back.
- A week whose rows your own `filters` removed is **not** reported as missing, and should not
  be described as one. The data was there; your threshold excluded it.

Either way a gap is not zero demand and not zero spend, and you should not average across it.

**A result can hold three kinds of row, and they do not mean the same thing.** Say which one a
number came from rather than calling the whole response "market data":

| Row | Source | Has own-store columns |
|---|---|---|
| Main | the store's own SQP table. Market `total_*` repeats on every ASIN row, so the tool de-duplicates it **within the store** per term and week - it is not summed across your ASINs | yes |
| Main, market columns widened | a main-table row kept whole, with only its **market** columns recomputed from the cross-store table over weeks the store itself has no row for | yes - but they cover fewer weeks than the market columns beside them |
| Supplemented | the **cross-store** market table, filling terms the store's table has no row for at all | no - they stay empty, never `0` |
| `marketOnly: true` | the cross-store market table for the whole query | none are returned |

Supplementing happens on an ordinary query too, not only under `marketOnly` - but only when you
gave exact terms, did not pass `asins`, are not querying by ASIN, and every metric filter is a
market metric. With an own-brand or share filter in play it is skipped on purpose: a missing
main-table row might just mean your filter excluded it, and filling it would read as "the store
never ran this term". The response reports how many rows were filled and how many had weeks
extended - relay that instead of presenting the set as uniform.

Widening the market columns of a main row happens only on `aggregate: true`, and only when no
metric filter is set. On such a row `marketWeekCount` is larger than `weekCount`, so the
own-over-market ratio is **not** a share for one period and understates the real share - check
the two before quoting one. Details in [`references/sqp-aba.md`](references/sqp-aba.md).

**Nothing here joins to your ad data.** Pull each side separately and put them together in the
answer. Two traps that follow:

- SQP purchases and ad orders use **different attribution** (24 hours vs 7 / 14 days). Never
  subtract one from the other to derive organic sales.
- Market click-through rate, the store's own ASIN click-through rate and the ad click-through
  rate have **three different denominators**. Never compare them as if they were the same
  number. Details in [`references/sqp-aba.md`](references/sqp-aba.md).

## What the tools already do for you

Do not redo these in post-processing - doing them twice is the failure mode.

| Already done | So |
|---|---|
| ABA click / conversion share is converted to 0-100 | Do not multiply by 100 again |
| ACOS percentiles are derived from reversed ROAS percentiles | Do not invert them yourself; P25 is already the good end |
| Week alignment, de-duplication of market totals, rate recomputation when aggregating | Just read the numbers - but know which de-duplication you got, see below |
| Low-sample flagging | Read the `*LowSample` flags instead of applying your own thresholds |

Both tools return a `meta.hint` carrying the rules that apply to that specific response. Read
it and carry its restrictions into the answer.

## Say what the numbers cannot support

These are the claims that go wrong most often:

1. **"No data" is not "no demand" and not "zero".** Market rows can be missing because the
   term is not in the table, the brand has no peer group, the period has no default category
   node, or the store never ran that term. The response distinguishes these - relay which one.
2. **A low-sample rate is not a finding.** When `*LowSample` is true the rate is still
   returned, but do not rank by it, pick terms with it, or call performance good or bad on it.
3. **Peer benchmarks are per brand, not per category**, and there is no campaign-level
   benchmark. See the Benchmark reference before judging a single campaign - the default
   answer there is "do not use it".
4. **Share here is share of a search term**, not share of voice on a placement. If the user
   asked about share of voice, say which one you are giving them.
5. **The term list is capped.** SQP keeps at most 100 search terms per ASIN per week, so any
   "all our terms" list is really "the top 100 per ASIN" - say so when listing.

## Before answering

1. State the actual aligned week window and any missing weeks.
2. Say which rows are market-only, which carry own-store data, and which are low-sample.
3. When you used peer data, say the brand, the category level, the ad product and the goal -
   those four decide which peer group the numbers came from.
4. Keep ad data and market data visibly separate in the answer; do not present a combined
   figure that no single source produced.
