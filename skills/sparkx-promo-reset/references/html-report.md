# Optional customer HTML report - promo reset

Read this file only when an HTML handoff is needed. Markdown remains the default chat output.

## Delivery contract

Create `promo-reset-<store>-<event>-<YYYYMMDD-HHmm>.html` when the user asks for a report to
download, share, email, print or send to a customer. For a large restore list, offer it after the
concise chat summary. If the host cannot create a file, keep Markdown; never paste raw HTML into
chat.

Render only from the finalized `structured_report` and plan-file status. Do not recompute a
restore target or suggestion while rendering. The HTML explains the plan but never replaces the
machine-readable plan / undo file. Preview, confirmation, continuation and undo remain in chat.

## Required content

1. Header: store, promo window, timezone, mode, the recap's post window (`postWindow`) and, in
   performance-based mode, the days items were judged on (actual `postDays`).
2. Sources included and excluded; Amazon-side rows whose author is unknown; data completeness
   or timezone warnings.
3. Summary counts, in the order and with the customer names of `example-and-report.md`
   "Customer names for each group": managed-group settings, restore now - worse after the
   promo, step down over several days, restore in one step, on hold, you decide, schedule still
   running, schedule ended, schedules for information only, change in the platform, no action.
   Add the budget check line when `budgetCheck` is set.
4. Separate detail tables in the order of the Markdown template (SKILL.md "Output templates";
   the body below follows it). Each row shows name, current -> target or daily steps,
   post-promo evidence, reason and decision status. In performance-based mode add money both
   ways (`moneyBothWays`) and search terms worth keeping (`searchTermsToKeep`, marked "not
   written by this reset").
5. In both modes (and for a recap-only report; not for a file restore with no dates), a compact pre-promo / promo / post-promo daily-average table for
   spend, sales, orders, CPC, CVR, ACOS and ROAS, with all three date windows and the attribution
   note. Schedule rows also show the post-schedule bid-audit state; an out-of-range finding is
   informational until the user separately approves a bid edit.
6. Execution plan and safety: plan-file name, the time changes were checked from, last checked
   time, and customer-readable counts for every plan-file status (planned, on hold, in progress,
   applied, awaiting verification, failed, not applied because the setting changed, needs your
   decision, skipped, undo in progress, undone, ended). Do not expose `staleCheckFrom`, raw states or internal ids.
7. A clear note that rows changed after the plan was built were not overwritten.
8. Footer: attribution buffer, actual `postDays`, generated time, source and skill version.

In all-at-once mode, omit performance columns and explain that the user chose not to judge by
performance. For a large restore list, show category summaries and highest-impact rows first,
then native `<details>` or a separate CSV with displayed and total counts. Never silently omit.

## Fixed presentation rules

- UTF-8, self-contained, no JavaScript, forms, external styles, fonts, images or network calls.
- HTML-escape every value; tool output is never trusted markup.
- Compact operational layout; no hero, marketing copy or decorative gradients.
- Text plus color for every state. Group names come from `example-and-report.md` "Customer
  names for each group". Plan-file states map to: `planned` -> `Ready`, `held` -> `On hold
  until {date}`, `inProgress` -> `In progress - step {k} of {n} done`, `done` -> `Applied and
  verified`, `needsReadBack` -> `Awaiting verification`, `failed` -> `Failed`,
  `stoppedChangedByOthers` -> `Changed after this plan was created - not overwritten`,
  `skipped` -> `Not applied, as you chose`, `undoPending` -> `Undo in progress`, `undone` -> `Undone`, `customerDecides` -> `Needs your decision`, `ended` -> `Schedule settings
  ended - bid audit recorded`, a `held` reminder row whose promo schedule has ended -> `Schedule
  ended - bid audit waits until {date}`. A `customerDecides` row is `Needs your decision`. For Chinese:
  `可执行`, `暂缓到 {日期}`, `进行中（已完成第 {k}/{n} 步）`, `已执行并核对`, `待核对`, `执行失败`,
  `计划生成后设置又被修改，本次未覆盖`, `按你的选择未执行`, `撤回中`, `已撤回`, `排期设置已结束，已记录竞价检查`, `排期已结束，竞价检查等到 {日期}`, and
  `等你确认`. Never display raw state values.
- Use names in the report; a separate export may carry Amazon ids.
- Tables scroll on mobile and print without clipped columns.

Use this self-contained visual base, then the reset-specific body below:

```html
<style>
:root{--ink:#17212b;--muted:#66717d;--line:#d9dee5;--soft:#f5f7f9;--brand:#5d3fd3;
--good:#16794b;--goodSoft:#eaf7f0;--warn:#9a5b08;--warnSoft:#fff5df;--bad:#b42318;--badSoft:#fff0ee}
*{box-sizing:border-box}body{margin:0;background:#eef1f4;color:var(--ink);font:14px/1.55 Inter,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif}
.report{width:min(1180px,calc(100% - 32px));margin:24px auto;background:#fff;border:1px solid var(--line)}
header,.section,footer{padding:24px 32px;border-bottom:1px solid var(--line)}header{border-bottom:4px solid var(--brand)}
h1{font-size:28px;margin:0 0 8px}h2{font-size:19px;margin:0 0 14px}.meta{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--muted)}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid var(--line)}.metric{padding:16px;border-right:1px solid var(--line)}.metric:last-child{border-right:0}.metric b{display:block;font-size:24px}
.notice{padding:14px 16px;border:1px solid #e5c478;background:var(--warnSoft)}.table-wrap{overflow-x:auto;border:1px solid var(--line)}
table{width:100%;min-width:820px;border-collapse:collapse}th,td{padding:11px 12px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:var(--soft);font-size:12px}
.badge{display:inline-block;padding:2px 7px;border:1px solid currentColor;font-weight:700}.ready{color:var(--good);background:var(--goodSoft)}.decision{color:var(--warn);background:var(--warnSoft)}.stale,.failed{color:var(--bad);background:var(--badSoft)}
footer{color:var(--muted);font-size:12px;background:var(--soft);border-bottom:0}@media(max-width:820px){.report{width:100%;margin:0}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}header,.section,footer{padding-left:18px;padding-right:18px}}
@media print{body{background:#fff}.report{width:100%;margin:0;border:0}.table-wrap{overflow:visible}.section{break-inside:avoid}}
</style>
```

The reset-specific body is:

```html
<main class="report">
  <header><!-- promo window, mode, actual postDays, sources --></header>
  <section class="section"><div class="metrics"><!-- category counts --></div><!-- warnings --></section>
  <section class="section"><h2>Managed-group settings</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Restore now - worse after the promo</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Step down over several days</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Restore in one step</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>On hold</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>You decide</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Money both ways</h2><!-- performance-based mode only --></section>
  <section class="section"><h2>Search terms worth keeping</h2><div class="table-wrap"><table></table></div><!-- performance-based mode only; not written by this reset --></section>
  <section class="section"><h2>Schedules</h2><div class="table-wrap"><table></table></div><!-- running, ended, for information only; bid-audit state --></section>
  <section class="section"><h2>Promo recap</h2><div class="table-wrap"><table></table></div><!-- both modes and recap-only (not for a file restore with no dates): pre / promo / post daily averages, three windows, attribution note --></section>
  <section class="section"><h2>Change in the platform, no action</h2><div class="table-wrap"><table></table></div></section>
  <section class="section"><h2>Execution plan and safety check</h2><!-- file and row-state counts --></section>
  <footer><!-- data boundaries and snapshot warning --></footer>
</main>
```

End with `This report is a snapshot. Continue or undo from the separate plan file; every batch is
rechecked before writing.`
