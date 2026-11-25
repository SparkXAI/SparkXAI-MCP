# Reports

`scripts/sqp_report.py` writes both deliverables from the same numbers.

## Delivery contract

Same split as every other report Skill (`sparkx-weekly-ads-report`, `sparkx-monthly-ads-report`,
`sparkx-product-diagnosis`, `sparkx-promo-reset`): **the markdown is written by the model in the
user's language, the HTML is produced by the script.**

| Deliverable | Who writes it | When |
|---|---|---|
| The markdown report | **You**, in the user's language, with every figure copied from `sqp_summary.json` | **Always** - it is the answer |
| `sqp_report.html` | `sqp_report.py --lang` | When the user wants something to present, share, send or print ("make a report", "something I can show my client", "one-pager", "for the meeting") |

`--out <dir>` also writes `sqp_report.md`. That file is the script's own rendering of the same
numbers: use it to check your markdown against, or hand it over when the user wants the file
rather than the answer. It is not a substitute for writing the answer.

Both carry the same figures in the same order: verdict, where the store stands, where the orders
go, searches by group, actions, limits. The HTML adds the charts, the tab bar, the glossary and
the language switch; it is self-contained, readable on a phone and prints to PDF.

Name the file for the customer when handing one over:
`sqp-<store>-<period>-<YYYYMMDD-HHmm>.html`, matching `sparkx-promo-reset`. Never paste raw HTML
into chat.

## Template

One template, `health` (an SQP audit page): where the store stands in the market, where orders
leak, where it can grow. Needs one period (search-level rows; own-ASIN rows add the product
drill-down). For other shapes (share change, fix-first list) answer in chat.

## How to build one

1. Run `sqp_calc.py` (see SKILL.md Step 3). Never type numbers into the report yourself.
2. Write `narrative.json` (schema at the top of `sqp_report.py`). **The top level is English and
   `i18n` holds `zh` and `ja`** - that is what the script reads, so do not write another language
   at the top level. When the user speaks Chinese or Japanese, write the English top level AND the
   matching `i18n` block, then pass `--lang zh` / `--lang ja`: the report is written and opens in
   that language, with the other two still in the switcher. A language with no `i18n` block falls
   back to the English narrative under translated labels, which reads as a half-translated page -
   so either fill it or do not offer that language. Keys:
   - `headline`: the verdict in one sentence with its two or three key numbers, taken from
     `sqp_summary.json`. It must survive being read alone on a slide.
   - `subline`: one sentence of "why", no new numbers.
   - `takeaways`: one sentence per chart, saying what to see in it.
   - `actions`: 3-5 rows. Each names the searches, the evidence number, the owner (Ads,
     Listing, Creative, Ops, Pricing) and what is at stake (orders from the summary, or market
     purchases as room). Bids and budgets: direction only. Every action also carries:
     - `where`: the product(s) and ASIN(s) that carry those searches (`top_asin` + names).
     - `measure`: what to check after 2 SQP weeks, as a number on the page moving to a target
       (conversion index, click share vs impression share, purchase share, ACOS).
     Read the levers in this order: price vs market (SQP median prices), then ad cost (CPC,
     ACOS vs store), then listing and creative. A product priced under the market that
     converts above it with weak ROAS is an ad-cost problem, not a listing problem.
   - `group_picks`: up to 4 searches per group (`scale_candidates`, `fix_listing`,
     `fix_or_cut`) for "Where to start in each group". Drop off-category or generic searches
     ("supplements", "cafe"); leave it out to take the top rows that have a product.
   - `takeaways.groups`: one sentence on that table (usually what price explains).
   - `limits`: anything the reader must know (period not confirmed, derived clicks, caps).
     The script adds the export cap and the standard SQP limits itself.
   - `store`, `period`: the period comes from the user or the tool, never guessed; if unknown
     write "weeks to confirm" and ask.
3. Pull the ad view for the same Sun-Sat weeks (it turns "convert below market" into a
   decision):
   - `get_ads_perf` `factEntity: "searchTerm"`, `select: ["query_"]`, `filters: {"query_": [<the
     5 top leak searches + 3 top scale searches>]}`, metrics `Spend`, `Sales`, `ROAS` -> save as
     `ads.json`.
   - Store ROAS for the same weeks and ad type (`factEntity: "campaign"`, filter
     `campaign.campaignType_: sponsoredProducts`, no select) -> `--baseline-roas`.
   - Products: `get_ads_perf` `factEntity: "asin"`, `select: ["asin.parent_asin_"]`, filter the
     top 6 parents from `asin_view`, metrics `TotalSalesAmount`, `ROAS`; short names from
     `get_entity_metadata` asin titles (shorten to the product name) -> `products.json`
     (`parent_asin`, `name`, `TotalSalesAmount`, `ROAS`).
   - Operator columns: for **every search the page shows** (leak and scale picks, protect,
     coverage gaps) pull `Impressions, Clicks, Spend, Sales, Conversions, CPC, ACOS, ROAS` in the
     same call, so "No ads" means no ad clicks in those weeks, not "not pulled".
   - Store Sponsored Products `Sales` and `Conversions` for the same weeks -> `store_ads.json`
     (ad sales per ad order turns orders within reach into a dollar ceiling).
   - Product names and prices: `get_entity_metadata` `entity: asin` for the `top_asin` values in
     the summary (`asin, parentAsin, asinTitle, asinBrand, asinPrice`) -> `names.json`
     (`{asin: {name, price}}`, names shortened to product + pack). Children of the product
     parents -> `children` in `products.json`.
   - Store brands: `asinBrand` values. Scan the protect and bid-up lists for any other brand's
     name and rerun `sqp_calc.py --competitor-terms "<names>" --brand-terms "<own brands>"`.
   - Brand, competitor and generic searches: rerun `sqp_calc.py` with
     `--brand-terms @own_brands.txt --competitor-terms @competitor_brands.txt` (a list the user confirmed),
     then pull the three search-term ad totals described in `rules.md` 3d -> `segment_ads.json`
     (`{own_brand|competitor_brand|generic: {Clicks, Spend, Sales, Conversions, CPC, ROAS, SalesPerOrder}}`)
     and render with `--segment-ads`. Narrative keys `takeaways.brand` and
     `takeaways.competitors`; add a brand-building action when own-brand CPC is clearly below
     generic CPC.
   - Event check: ad sales per Sun-Sat week across the window (one call per week). A week
     well above the others is an event week: label it, or move the window.
   Skip any part whose data is missing; the page drops that section.
4. Render: `python sqp_report.py --summary sqp_summary.json --narrative narrative.json
   --template health --lang en|zh|ja [--ads ads.json --baseline-roas 5.07] [--products products.json]
   [--store-ads store_ads.json] [--names names.json] [--actions-csv sqp_actions.csv] [--plan plan.json]
   --out out/`. `--out` is a directory and writes `sqp_report.md` + `sqp_report.html`; a path ending
   in `.md` or `.html` writes only that one file. `--lang` must match the narrative language you
   wrote. A worked narrative is in `example-narrative-health.json` (synthetic numbers; replace
   `{store}` with the store name)
5. Check before handing over: confirm every number in the headline, takeaways and actions
   appears in `sqp_summary.json`. For the HTML, open it (or screenshot it) and check that it opens
   in the right language and no chart label is cut off.
6. Deliver. Markdown by default; the HTML as well when the user wants something to show. In chat,
   one line on what it says and one on what to do with it.

## Design

The page uses the SparkX report design: ink #050713 on white, one highlight blue #003BF9
(dark mode #4EB4FE), the blue-violet glow behind the hero, Sora for display and Inter for
text, grey cards, thin ink bars, tables with an ink top rule, tabs as screens (Overview,
Funnel, Searches, Ads and products, Actions, Notes), a light/dark toggle and Print / PDF
(prints every tab in order). Tabs with no data are dropped. Do not restyle it per report;
change the CSS tokens in `sqp_report.py` only when the brand changes.

**Languages.** Every report carries an English / Chinese / Japanese switch in the top bar and always opens
in English. Interface labels are built in (`UI` in `sqp_report.py`). Write the narrative in
English at the top level and add `i18n.zh` and `i18n.ja` with the same keys (title, store,
period, headline, subline, takeaways, actions, limits). Translate meaning, not word for word;
keep search terms, ASINs and product names as shoppers see them on Amazon; keep every number
identical. A missing language falls back to the English narrative with translated labels -
say so if you skip one. Use Simplified Chinese for the Chinese narrative.

**Tooltips for readers new to SQP.** Built in (`scripts/sqp_tips.py`), all three languages:
an (i) next to each section title, KPI card and key table column says what the measure is,
how to read it and how to use it; every bar shows its numbers on hover (tap on a phone);
the Notes tab carries the same text as a glossary, so the printed PDF keeps it. When you add
a new measure to a template, add its entry to `TIPS` in all three languages first. Tooltip
text explains; it never carries a finding or a number that is not on the page.

The headline renders at display size: keep it to one sentence of 20 words or fewer. Put the
"why" in `subline`.

## What a PPC manager needs on the page (operator layer)

The page is built for the owner and the ad manager at once. These are not optional when the
data exists:

- Each search row names **the product that carries it** (ASIN) and **its price vs the market
  median** on that search. Price is per listing: say "show value per serving / test a smaller
  pack", never "cut the price" on that evidence alone.
- The ad table shows **price, conversion vs market, within reach or room, spend, CPC, ACOS,
  ROAS** - enough to tell a listing problem from an ad-cost problem.
- **Group counts come with names**: "Where to start in each group" plus the CSV download of
  every judged search (`sqp_actions.csv`, embedded in the page).
- **Coverage gaps are head terms**: never call them cheap. Show whether ads already run there
  and at what ROAS; suggest a capped exact-match test where ads already return the store
  average.
- **Protect** shows ad spend and ROAS per search; another brand's name is listed apart as
  conquest.
- **Orders within reach** also shows a dollar ceiling (orders x ad sales per ad order),
  labelled "a ceiling, not a forecast".
- Products show their **main searches** with conversion index, or say the ASIN detail export
  is needed.
- Notes state: event check result, the share of purchases on searches too small to judge, the
  dollar method, the price caveat and that ad conversion (7-day, halo) is not SQP conversion.

## Changes to confirm (Plan mode only)

When the report follows a Plan-mode run, render with `--plan plan.json` (from `sqp_plan.py`):
the Actions tab lists the numbered rows (change, campaign, now -> new, why) and the rows that
will not be written. The page never executes; confirmation always happens in chat. A Diagnose
report has no plan block.

## PPC review checklist (the page must pass all before it is shared)

- One "orders within reach" number per search everywhere (after + before the click).
- The low-share, below-market group is labelled "Fix before more spend", never "cut", because
  it holds big profitable searches; cutting is only for searches the product does not fit.
- Every action has `impact` (orders + the dollar ceiling at ad sales per ad order, or market
  purchases as room), `when` (This week / This month / Next 4 weeks / Ongoing), `where` and
  `measure`. Rank actions by speed and size, ads quick wins included.
- Protect: say how many protect searches run below the store ROAS; where share is already
  25%+, suggest a small bid-cut test watched on purchase share (an incrementality check).
- Other brands' names: quote the ad spend and ROAS there and cap it when below the store.
- Brand-building actions are measured on branded search volume (monthly branded SQP pull) and
  brand names' share of keyword ad sales, not on ad clicks alone.
- Product rows: show the searches losing the most orders; if those convert fine, say the gap
  is spread over many smaller searches.
- Notes say when there is no prior period (no trend) and that conversion vs market on the
  store's own brand names says little (the market there is mostly the store).

## Wording rules for the page

- SQP brand numbers are organic + paid. Never "your searches" or "your own searches" (in any
  language); write "purchase share across N searches".

- Tone: neutral to positive. Lead with where the store stands and what is within reach, then
  the gap. Never alarmist, never hide the gap.
- The insight to look for when ads are joined: searches with healthy ad ROAS that still convert
  below the market (only SQP shows it), and searches that are strong in the market but weak in
  ads (tune before scaling).
- Product-level "conversion vs market" is weighted by the searches that product appears in; a very low
  index with strong ad ROAS usually means it shows on broad searches - say "check which
  searches drive it", not "the listing is bad".
- Written for the store owner or their client. Plain words: "shoppers", "searches", "after
  the click"; no "SQP impressions", "ASIN-level CVR index".
- Never compare brand CTR with market CTR. Share of clicks vs share of impressions is fine
  (both are shares of the same shoppers).
- Every claim in the headline and takeaways must be checkable against a chart or KPI on the
  same page. Counting words ("a fifth", "most") are checked against the numbers.
- Orders, not money. Dollar figures only when ad data supplies them, labelled as ad data and
  as a ceiling.
- Never call a head term (100K+ searches) a cheap test. Never put another brand's name on the
  protect list.
- Counting words are checked against the rows shown ("all eight", "five of the eight", "most").

## Branding

Default `--brand sparkx` (SparkX wordmark in the header, "via SparkX" in the source line).
If the user asks for no branding, their own name, or a white-label version, use `--brand none`:
the header shows the store name and the source line drops "via SparkX".
