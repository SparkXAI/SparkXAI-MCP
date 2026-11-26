# Time Aggregation (Weekly/Monthly/Quarterly) and Splitting Windows >90 Days

Weekly spend/sales/ACOS trend for June (within the 90-day single-call limit):

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-06-01",
  "dateEnd": "2026-06-30",
  "metrics": ["Spend", "Sales", "ACOS"],
  "select": ["toMonday(parseDateTime32BestEffort(date)) as week"],
  "orderBy": [{"field": "week", "direction": "ASC"}],
  "userContext": "Weekly ad spend trend for June"
}
```

**If the user asks for a window longer than 90 days** (e.g. "monthly trend for the last year"), aggregation alone does not let you do this in one call — calendar quarters do **not** reliably fit under 90 days either (Q2 is 91 days, Q3/Q4 are 92 days, and even Q1 is 91 days in a leap year), so don't assume "one call per quarter" is safe. Instead split the year into contiguous, non-overlapping ≤90-day windows, computed directly, not by calendar quarter. A full leap year (366 days, e.g. 2024) needs **5** such calls:

**Window 1 (90 days):**
```json
{"dateStart": "2024-01-01", "dateEnd": "2024-03-30", "select": ["toStartOfMonth(parseDateTime32BestEffort(date)) as month"], "metrics": ["Spend", "Sales", "ACOS"], "factEntity": "campaign", "profileIds": [4404871489220462], "userContext": "Monthly trend for the year, window 1 of 5"}
```
**Window 2 (90 days):**
```json
{"dateStart": "2024-03-31", "dateEnd": "2024-06-28", "select": ["toStartOfMonth(parseDateTime32BestEffort(date)) as month"], "metrics": ["Spend", "Sales", "ACOS"], "factEntity": "campaign", "profileIds": [4404871489220462], "userContext": "Monthly trend for the year, window 2 of 5"}
```
**Window 3 (90 days):**
```json
{"dateStart": "2024-06-29", "dateEnd": "2024-09-26", "select": ["toStartOfMonth(parseDateTime32BestEffort(date)) as month"], "metrics": ["Spend", "Sales", "ACOS"], "factEntity": "campaign", "profileIds": [4404871489220462], "userContext": "Monthly trend for the year, window 3 of 5"}
```
**Window 4 (90 days):**
```json
{"dateStart": "2024-09-27", "dateEnd": "2024-12-25", "select": ["toStartOfMonth(parseDateTime32BestEffort(date)) as month"], "metrics": ["Spend", "Sales", "ACOS"], "factEntity": "campaign", "profileIds": [4404871489220462], "userContext": "Monthly trend for the year, window 4 of 5"}
```
**Window 5 (6 days — the remainder):**
```json
{"dateStart": "2024-12-26", "dateEnd": "2024-12-31", "select": ["toStartOfMonth(parseDateTime32BestEffort(date)) as month"], "metrics": ["Spend", "Sales", "ACOS"], "factEntity": "campaign", "profileIds": [4404871489220462], "userContext": "Monthly trend for the year, window 5 of 5"}
```

Each window starts the day immediately after the previous window's end (no gap, no overlap) and is ≤90 days: 90 + 90 + 90 + 90 + 6 = 366, matching the full leap year exactly. For a non-leap 365-day year, the same method applies — the last window is just 5 days instead of 6.

**General algorithm** (don't hardcode quarter boundaries, and don't assume "4 calls"): starting from the range's actual `dateStart`, repeatedly take a window of `min(90 days, days remaining)`, then set the next window's `dateStart` to `(previous window's dateEnd) + 1 day`. Stop once the windows collectively reach the original `dateEnd`. A full year needs **5** such calls (see above), not 4.

### ⚠️ Merging results across windows — do not just concatenate

This applies to **whatever time-aggregation grain you used in `select`** — `week`, `month`, `quarter`, or `year` — not just month. A 90-day window boundary can fall inside any of these periods, not only inside a month: a week can be split across two windows, a quarter can be split, even a year boundary could in principle be split for a long enough combined range. The example below uses `month` for concreteness, but the same issue and the same fix apply if you aggregated by `week`/`quarter`/`year` instead.

Because each window boundary falls **inside** a calendar month in this example (window 1 ends `2024-03-30`, window 2 starts `2024-03-31`), a month that straddles a boundary comes back as **two separate partial rows** — one from each window (e.g. "March" appears once in window 1's results covering Mar 1–30, and again in window 2's results covering only Mar 31). Simply concatenating the 5 result sets would show March twice, and averaging the two rows' `ACOS` values would be **mathematically wrong** (a plain average ignores each partial row's weight, i.e. how much Spend/Sales it actually represents).

Correct merge procedure (generalized to any grain):
1. Concatenate all window result sets into one list of rows.
2. **Group by the time key you aggregated on** — `month` in this example, but the same applies to `week`/`quarter`/`year` if that's what `select` used. A period split across two windows now has 2+ rows sharing the same time-key value.
3. For each time-key value, **sum** the base metrics across its rows: total `Spend` = sum of `Spend` from all rows with that key, likewise for `Sales`, `Clicks`, `Conversions`, etc.
4. **Recompute** derived ratio metrics from the summed base metrics — `ACOS = total Spend / total Sales × 100`, not an average of the partial rows' own `ACOS` values. Same for `CTR`, `CVR`, `ROAS`, etc: always recompute from summed numerators/denominators, never average pre-computed ratios.
5. Present one row per period (week/month/quarter/year) after this merge — not one row per (window, period) pair.

**Note on illustrative dates**: the concrete dates above (2024, 2026) are for format illustration — always substitute real dates that satisfy the tool's actual constraints (dateEnd ≥ dateStart, span ≤90 days, dateStart no more than 15 months before today) at call time.
