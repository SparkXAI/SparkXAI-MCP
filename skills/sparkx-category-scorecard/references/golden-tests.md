# Golden tests

69 executable tests in four files, all on synthetic data in the real tool shapes (`scripts/tool_fixtures.py`). Run each
with `python3 scripts/<file>.py`; each prints `N/N passed` and exits non-zero on a failure.

| File | Tests | Covers |
|---|---|---|
| `test_market.py` | 10 (M1-M10) | `get_market_search_perf` rows: market totals once per search x week, rates from sums, own-brand searches out of the generic read, missing weeks named, null counts skipped, coverage of spend, low sample, generic fallback, `meta.truncated`, export fallback |
| `test_scorecard.py` | 25 (S1-S25) | peer or market call refused -> access gap named (S24-S25); truncated market data -> market axis not used, not shown or counted (S20 control, S21-S22); weekly peer rows, latest week (S23); `get_peer_benchmark` rows: node walk via `categoryMetadata`, P25-P75 goals with the tool's ACOS, plays, cost flipped, SB CONSIDERATION on CPC, SP leads, unknown goal not used, `NO_PEER_BENCHMARK`, brand without rows, coverage < 40%, Keep, Hold (stock), plan only before and during an event, orders at stake split, Vendor without SQP, latest period, wide spread |
| `test_budget_room.py` | 25 (B1-B25) | stock known for only some products -> raise held, unknown ASIN named (B25); raise with stock not confirmed (no mapping) held (B21); final TACOS combination judged: shortfall stated (B22), raises that do not help held and "after" recomputed from the ready cuts (B23-B24); raise tiers from `outOfBudgetMinutes`, +50% cap, null usage = not checked, `outOfBudgetPercentage` ignored, flag when capped above goal + 5, lower sizing, AI on / off / unknown, op-log recent change, stock, lifetime budget, SB banner, no metadata, floor, CSV fields for `campaign.updateBudget`, in-event and pre-event holds, peak sizing, same-budget funding, TACOS cap |
| `test_e2e.py` | 9 (E1-E9) | the four scripts chained on tool JSON: market read, Scale held during an event, SB CONSIDERATION goal, unknown goal, empty peer status, null budget usage, AI group campaign, recent change + in-event hold, report renders without removed sections |

Acceptance prompts (judged by reading the report, not executable):

| User says | Expected |
|---|---|
| "How are my categories doing vs peers? Need next month's budget." | Ask card; headline with a number, at most 3 first actions, plays, budget plan, fair goals |
| "What ACOS target is fair for magnesium?" | P25-P75 range with ACOS equivalent, level and period named; no P50 target when the spread is wide |
| Vendor profile | No SQP call; "no market data" said as a coverage gap, not a finding; plays from peers and ACOS |
| Black Friday running | Plan only; every change-list row `ready = no`; promotion budgets pointed to sparkx-promo-monitor |
| A category whose peer row is `NO_PEER_BENCHMARK` | Said with that status; ad cost from account ACOS; no "too few peers" |
| "Why did spend drop on Nov 14?" | Not this skill: sparkx-weekly-ads-report |
| No permission for the profile | Stop and name the profile; no partial guessing |

Red lines: no write calls from this skill; no averaged levels, goals, brands or periods; no console ACOS or single
campaign against peer rows; no 0 for missing data; no threshold on `outOfBudgetPercentage`.
