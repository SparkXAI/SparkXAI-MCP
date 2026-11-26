# The customer's own stock source

The platform's stock fields are refreshed **once a day**, and only for Seller profiles with
SP-API authorisation (vendors have none). Many sellers keep a more current figure in their own
ERP, warehouse or inventory system. On a promotion that difference matters most: on an event
day the daily figure does not show what sold since the refresh.

So **invite the customer to bring their own stock source**, once, together with the other
questions:

> "库存用的是每天从亚马逊同步的数据（截至 {日期}）。大促期间卖得快，如果你的 ERP 或库存表里有
> 更新的数，发给我，我会一起算进去，判断会更准。"

**How to say it.** Present the daily figure as what it is - the stock synced each day, with the
date it is from when the data shows it - and the customer's own source as a way to sharpen the
call. Never describe it as a shortcoming ("not live", "does not include today's sales", "only
updates once a day"). Say it once per conversation, when stock first matters, not in every
check or every stock row. On an event day the same applies to the part already sold today:
take it off in the calculation (monitor `pace-and-states.md` section 8) and show the result,
not a caveat.

## What counts as a source

| Source | How to read it |
|---|---|
| A file the customer attaches (Excel, CSV, a sheet export, a PDF, a screenshot) | Read it like any attached table; confirm what was read (below) |
| Another tool connected in this session (an ERP / inventory / spreadsheet connector) | Use it read-only, only if the customer points to it; never write to it |
| Numbers the customer types ("B0xx 还剩 800 件，18 号到 2,000 件") | Use as given |

Never search for or connect a source on your own; the customer names it.

## Reading it

Match columns by meaning, in any language:

| What | Common headers |
|---|---|
| ASIN / SKU | ASIN, SKU, Child ASIN, 子ASIN, 商品编码 |
| Available now | Available, Fulfillable, On hand, 可售, 可售库存, 库存(件) |
| Inbound and when it becomes sellable | Inbound, In transit, ETA, Arrival, 在途, 入库中, 预计到货 |
| Daily units sold | Units/day, Avg daily sales, 日均销量 |
| As of | Date, Updated, 更新时间 |

Confirm in one short table: which columns were used, how many ASINs were matched to the
advertised ASINs, which could not be matched, and **the time the figures are from**. If the
file has no time, ask.

## Using it

- **The customer's source comes first** for every ASIN it covers; the platform's daily figure
  fills the rest. Say which source each flag came from.
- **Inbound with an arrival date counts** from the day it becomes sellable (the platform's
  `inbound` has no date and never counts on its own).
- **Days of cover**: the customer's available stock / their daily units. Without daily units,
  take the platform's pace for the same ASIN - daily units ≈ (`asinFbaQuantity` + reserved) /
  `asinDayAvailability30` - and say so.
- **When the two disagree a lot** (more than about 20%), show both and ask which is right -
  never average them.
- On event days, ask whether the figure is still current before relying on it; a morning
  export is out of date by the evening peak.
