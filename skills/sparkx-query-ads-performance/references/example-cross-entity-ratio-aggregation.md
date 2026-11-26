# Cross-Entity Ratio Aggregation (ACOS/CTR/CVR/ROAS/CPC)

## The rule

**Never average pre-computed ratio metrics across rows.** When aggregating ACOS, CTR, CVR, ROAS, CPC, or any other derived ratio across multiple entities (campaigns, ad groups, keywords, etc.), you must sum the numerator and denominator separately, then recompute the ratio from the totals.

This applies to:
- Summarizing N campaigns into one "total" figure
- Rolling up ad-group rows to a campaign-level number
- Combining rows from multiple stores
- Any scenario where you have per-row ratio values and need a single combined number

## Why arithmetic mean is wrong

ACOS = Spend / Sales × 100. If campaign A has ACOS 10% (Spend $100, Sales $1000) and campaign B has ACOS 50% (Spend $50, Sales $100), the naive average is (10+50)/2 = 30%. But the actual combined ACOS is ($100+$50) / ($1000+$100) × 100 = **13.6%** — campaign A dominates because it has far more spend and sales.

The same logic applies to all derived ratios:

| Metric | Correct aggregation |
|--------|-------------------|
| ACOS | sum(Spend) / sum(Sales) × 100 |
| CTR | sum(Clicks) / sum(Impressions) × 100 |
| CVR | sum(Conversions) / sum(Clicks) × 100 |
| CPC | sum(Spend) / sum(Clicks) |
| CPA | sum(Spend) / sum(Conversions) |
| ROAS | sum(Sales) / sum(Spend) |

## Practical approach

### Option 1: Let the tool do it (preferred when possible)

If you need a single combined figure across all campaigns, omit `select` entirely (global aggregation) or group at a coarser level. The tool computes ratio metrics from the grouped totals server-side:

```json
{
  "profileIds": [4404871489220462],
  "factEntity": "campaign",
  "dateStart": "2026-07-01",
  "dateEnd": "2026-07-20",
  "metrics": ["Spend", "Sales", "ACOS", "Clicks", "Impressions", "CTR"],
  "filters": {"campaign.campaignType_": "sponsoredProducts"},
  "userContext": "Overall SP ACOS and CTR for this month"
}
```

No `select` → one row with the correct weighted ACOS/CTR across all SP campaigns.

### Option 2: Client-side recomputation (when you already have per-entity rows)

If the user asks "what's the overall ACOS for these 5 campaigns?" and you already fetched per-campaign rows (e.g. to show a table), recompute from the base metrics in those rows:

1. Sum `Spend` across the 5 rows → total Spend
2. Sum `Sales` across the 5 rows → total Sales
3. ACOS = total Spend / total Sales × 100

**Do not** take the 5 ACOS values and average them.

### Option 3: Grouped query still needs care

If the user asks "ACOS by campaign type" and you group by `campaign.campaignType_`, the tool gives you one row per type with correctly weighted ACOS within each type. But if you then need to further roll up two of those types into a combined number (e.g. "SP + SB combined"), apply the same rule — sum the base metrics from those two rows, then recompute.

## When arithmetic mean IS appropriate

Simple (non-ratio) metrics like Spend, Sales, Clicks, Impressions, Conversions can be summed directly. And if the user explicitly asks for "the average ACOS across campaigns" (meaning they want each campaign weighted equally regardless of size), that's a deliberate statistical choice — honor it, but clarify in your response that this is an unweighted average, not the actual overall ACOS.
