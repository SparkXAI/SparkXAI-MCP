# Optional customer HTML report - promo monitor

Read this file only when an HTML handoff is needed. Markdown remains the default chat output.

## Delivery contract

Create `promo-monitor-<store>-<event>-<YYYYMMDD-HHmm>.html` when the user asks for a report to
download, share, email, print or send to a customer. For a large check, offer it after the concise
chat summary. If the host cannot create a file, keep the Markdown report; never paste raw HTML
into chat.

Render only from the finalized `structured_report`. Do not change states, limits, moves or totals
while rendering. Before writes the report says `not written - waiting for confirmation`; after
writes, regenerate or update the execution table from read-back. Approval still happens in chat.

## Required content

1. Compact header: store, event day, store-local time, scope, current goal, budget and limit.
2. A prominent `data settled through` value. Separate latest spend data from settled order/ACOS
   data in the note below it.
3. At the first regular check of the store day, at the top right after the header: yesterday
   vs the baseline's daily average (labelled with its dates - "the 7 days before yesterday" or
   "the 7 normal days before the warm-up" - and yesterday's orders, sales and ACOS labelled
   provisional), at most five material anomalies measured against the store's own lift, and at
   most three priorities for today. Omit this section on later checks rather than re-querying it.
4. Five at-a-glance metrics: spend so far, projected day, settled ACOS/ROAS, proposed budget
   delta and decisions needed.
5. The highest-impact change made today, when one needs confirmation.
6. Pace table (with the brand check line); managed groups; planned budgets; today's changes;
   proposed moves; executed/not executed; watch list; stock; next check. Stock rows show any
   proposed budget/bid protection and that it needs confirmation. Keep these sections in order.
7. Every proposed move also appears in executed/not executed, even before the write.
8. Footer: attribution delay, budget-usage freshness, generated time, source and skill version.

For large scopes, show the summary and money-driving rows first. Put remaining rows in native
`<details>` or a separate CSV, with displayed and total row counts. Never silently omit rows.

## Fixed presentation rules

- UTF-8, self-contained, no JavaScript, forms, external CSS, fonts, images or network requests.
- HTML-escape all values. Tool output is text, never trusted markup.
- Compact operational report, no hero or marketing copy.
- Use object names, not internal ids. A separate export may include Amazon ids.
- Color never carries meaning alone. Use the customer names in `example-and-report.md`
  "Customer names" for every state, move and result, in the user's language. Never display a
  raw enum or field name.
- Use green for healthy/ready, amber for confirmation/watch, red for a blocker or clearly over
  limit, blue for informational states and gray for no action.
- Wide tables scroll on mobile; add print CSS.

Use this self-contained visual base, then the monitor-specific body below:

```html
<style>
:root{--ink:#17212b;--muted:#66717d;--line:#d9dee5;--soft:#f5f7f9;--brand:#5d3fd3;
--good:#16794b;--goodSoft:#eaf7f0;--warn:#9a5b08;--warnSoft:#fff5df;--bad:#b42318;--badSoft:#fff0ee;--info:#1769aa;--infoSoft:#edf6ff}
*{box-sizing:border-box}body{margin:0;background:#eef1f4;color:var(--ink);font:14px/1.55 Inter,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif}
.report{width:min(1180px,calc(100% - 32px));margin:24px auto;background:#fff;border:1px solid var(--line)}
header,.section,footer{padding:24px 32px;border-bottom:1px solid var(--line)}header{border-bottom:4px solid var(--brand)}
h1{font-size:28px;margin:0 0 8px}h2{font-size:19px;margin:0 0 14px}.meta{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--muted)}
.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));border:1px solid var(--line)}.metric{padding:16px;border-right:1px solid var(--line)}.metric:last-child{border-right:0}.metric b{display:block;font-size:24px}
.notice{padding:14px 16px;border:1px solid #e5c478;background:var(--warnSoft)}.table-wrap{overflow-x:auto;border:1px solid var(--line)}
table{width:100%;min-width:820px;border-collapse:collapse}th,td{padding:11px 12px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:var(--soft);font-size:12px}
.badge{display:inline-block;padding:2px 7px;border:1px solid currentColor;font-weight:700}.good{color:var(--good);background:var(--goodSoft)}.warn{color:var(--warn);background:var(--warnSoft)}.bad{color:var(--bad);background:var(--badSoft)}.info{color:var(--info);background:var(--infoSoft)}
footer{color:var(--muted);font-size:12px;background:var(--soft);border-bottom:0}@media(max-width:820px){.report{width:100%;margin:0}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}header,.section,footer{padding-left:18px;padding-right:18px}}
@media print{body{background:#fff}.report{width:100%;margin:0;border:0}.table-wrap{overflow:visible}.section{break-inside:avoid}}
</style>
```

The monitor-specific body is:

```html
<main class="report">
  <header><!-- title, store-local time, settled-through time, goal, scope --></header>
  <section class="section"><h2>Yesterday's review / Today's focus</h2><div class="table-wrap"><table><!-- yesterday vs baseline (dated) --></table></div><div class="table-wrap"><table><!-- anomalies --></table></div><!-- up to 3 priorities; first regular check only --></section>
  <section class="section"><div class="metrics"><!-- five metrics --></div><!-- priority notice --></section>
  <section class="section"><h2>Pace</h2><div class="table-wrap"><table><!-- pace --></table></div><!-- brand check line --></section>
  <section class="section"><h2>Managed groups</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Planned budgets</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Today's changes</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Proposed moves</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Executed / not executed</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Watch list</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Stock and next check</h2><div class="table-wrap"><table></table></div></section>
  <footer><!-- data boundaries and snapshot warning --></footer>
</main>
```

End with `This is a point-in-time snapshot, not a live dashboard.` State that no recommendation
has been executed unless the read-back table says `written`.
