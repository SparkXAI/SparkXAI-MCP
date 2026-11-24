# Output

## Shape of every answer

1. **Verdict with its number** - the first sentence answers the question.
2. **Scope line** - store, Sun-Sat weeks, sources (tool / which exports), events excluded,
   sample gate, missing weeks, any cap (tool `meta.truncated`, 10,000-row export, top 100 per ASIN).
3. **Evidence** - one small table or 3-5 bullets. Before / after / change for change questions.
4. **Actions** - what to do and who owns it (ads -> Plan mode; listing, price, stock, delivery
   -> the named team). Direction only for bids and budgets in Diagnose mode.
5. **What SQP cannot tell here** - one line, only the gap that matters for this question.
6. **Retail calendar line** - when an event is within 6 weeks: days to it and whether the
   advice is for build-up, harvest or retention.

Language follows the user. Numbers come from `sqp_summary.json` and MCP results, never
re-derived in prose. Percent points are "pt"; shares are % of the market; orders are orders.

## Two versions

| | Exec (owner, brand lead, client meeting) | Operator (ad manager, CSM, agency) |
|---|---|---|
| Length | 3-5 lines | Short sections + ranked tables |
| Lead | The verdict: "Market -12%, you -9%, share up 0.3 pt" | Same verdict + scope line |
| Body | 3 numbers to bring to the meeting, 1-3 decisions this week, in dollars where ads data gives dollars | Ranked list: query or parent ASIN, orders at stake, stage, next step, owner |
| IDs | None | ASINs, queries, campaign names for hand-off |
| Close | What SQP cannot tell | Same + confidence (sample, coverage, caps) |

Default: exec version (the main users are customers on SparkX MCP). Switch to operator when the user asks for a list or detail. Pick from the question: "explain to my client / boss", "summary", "in one line" -> exec; "list",
"which queries", "what do I change" -> operator. Offer the other version in one line.

## Wording

| Say | Not |
|---|---|
| "your advertised ASINs" | "your brand" (SQP is not the official Brand view) |
| "below your usual CTR on this query" | "your CTR is X% of the market" |
| "orders lost vs market conversion" | "$ lost" (SQP has no money) |
| "not enough clicks to judge (n = 6)" | a CVR verdict on 6 clicks |
| "no advertised ASIN showed up here" | "0 purchases" for an empty brand column |
| "market demand on these 40 queries fell 12%" | "the category fell 12%" (queries have no category) |
| "the week of Sep 6-12 (SQP is weekly)" | a daily SQP number |

Never state a wrong comparison and add the caveat afterwards; give only the right one.

## Confidence

High: 4+ weeks, query-level rows, gates passed, no caps hit. Medium: one period, export caps,
derived clicks. Low: < 20 clicks on the queries named, missing weeks inside the window, events
not excluded. Say which, in a few words.

## Hand-offs (Diagnose never writes)

| Finding | Hand-off |
|---|---|
| Spend with no orders, or a converting search term to harvest into exact | `sparkx-search-term-diagnosis` (negatives and harvests are not produced here) |
| Searches that deserve more, or cost too much, in one category | Plan mode (`plan-mode.md`) for that category |
| One product behind the leak | `sparkx-asin-deep-dive` |
| Campaign in an AI managed group | the group's target ACOS via `sparkx-edit-ai-group` (Plan mode lists it as a suggestion) |

Listing / price / delivery fixes are written as a short brief per parent ASIN: the queries,
the leak stage, the evidence.
