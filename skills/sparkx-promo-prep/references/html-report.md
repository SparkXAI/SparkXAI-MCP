# Optional customer HTML report - promo prep

Read this file only when an HTML handoff is needed. Markdown remains the default chat output.

## Delivery contract

Create `promo-prep-<store>-<event>-<YYYYMMDD-HHmm>.html` when the user asks for a report to
download, share, email, print or send to a customer. For a large plan, offer the same file after
the concise chat summary. If the host cannot create a file, keep the Markdown report; never paste
raw HTML into chat.

Render from the finalized `structured_report` in `example-and-report.md`. Rendering must not
change a threshold, recompute a value or add an action. The chat still carries open questions,
the write preview and confirmation. The HTML is a snapshot, not an approval surface.

## Required content

1. Compact header: store, event dates, timezone, generated time and data freshness. Show
   `dataAsOf` as a customer label such as "数据截至", never as the field name.
2. At-a-glance metrics: normal day, event-day budget, multiplier, push tier and scope.
3. Blockers / decisions first: stock, portfolio and store ceilings, bid/placement guardrails,
   brand-negative protection, ended or paused delivery, schedule conflicts and unanswered
   questions. A guardrail that was not exposed is labelled "platform check needed", not passed.
4. Customer answers and assumptions.
5. Health check and sizing evidence.
6. Day-role table.
7. Separate action tables for schedules (show head/defensive/other, Group-30 ACOS and the
   confirmed multiplier), group totals and group settings, campaign budgets,
   bids, placements and portfolio ceilings. Every row shows current -> proposed, timing, reason
   and status. Then what is not raised (`notRaised`, grouped by reason) and the headroom left
   per day (`headroom`).
8. Product-line allocation and timeline.
9. Data notes, generation time, data source and skill version.

When a table is very large, keep the summary and money-driving rows first, then put the remaining
rows in a native `<details>` section or a separate CSV. State the displayed and total row counts;
never silently omit rows.

## Fixed presentation rules

- UTF-8, one self-contained file, no JavaScript, forms, remote fonts, images or external assets.
- Escape every customer value before inserting it into HTML. Never render tool output as markup.
- Use semantic `header`, `main`, `section`, `table` and `footer` elements.
- Compact operational layout: no hero, marketing copy, decorative gradients or nested cards.
- Object names are visible; internal ids are not. A separate export may include Amazon ids.
- Status uses text plus color, with the customer names in `example-and-report.md` "Status
  values and their customer names" (`blocked`, `needsYes`, `ready`, `scheduled`, `written`,
  `needsReadBack`, `failed`, `skipped`). Never display the raw status enum.
- Wide tables live in `.table-wrap { overflow-x:auto }`; do not shrink text until unreadable.
- Add print CSS; avoid splitting a summary or a short table across pages.

Use this visual base and translate visible labels to the user's language:

```html
<style>
:root{--ink:#17212b;--muted:#66717d;--line:#d9dee5;--soft:#f5f7f9;
--brand:#5d3fd3;--brandSoft:#f0edff;--good:#16794b;--goodSoft:#eaf7f0;
--warn:#9a5b08;--warnSoft:#fff5df;--bad:#b42318;--badSoft:#fff0ee}
*{box-sizing:border-box}body{margin:0;background:#eef1f4;color:var(--ink);
font:14px/1.55 Inter,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif}
.report{width:min(1180px,calc(100% - 32px));margin:24px auto;background:#fff;border:1px solid var(--line)}
header,.section,footer{padding:24px 32px;border-bottom:1px solid var(--line)}
header{border-bottom:4px solid var(--brand)}h1{font-size:28px;margin:0 0 8px}h2{font-size:19px;margin:0 0 14px}
.meta{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--muted)}
.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));border:1px solid var(--line)}
.metric{padding:16px;border-right:1px solid var(--line)}.metric:last-child{border-right:0}
.metric b{display:block;font-size:24px}.table-wrap{overflow-x:auto;border:1px solid var(--line)}
table{width:100%;min-width:820px;border-collapse:collapse}th,td{padding:11px 12px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--soft);font-size:12px}.badge{display:inline-block;padding:2px 7px;border:1px solid currentColor;font-weight:700}
.ready{color:var(--good);background:var(--goodSoft)}.decision{color:var(--warn);background:var(--warnSoft)}.blocker{color:var(--bad);background:var(--badSoft)}
footer{color:var(--muted);font-size:12px;background:var(--soft);border-bottom:0}
@media(max-width:820px){.report{width:100%;margin:0}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}header,.section,footer{padding-left:18px;padding-right:18px}}
@media print{body{background:#fff}.report{width:100%;margin:0;border:0}.table-wrap{overflow:visible}.section{break-inside:avoid}}
</style>
```

End with: generated time, store timezone, the owning skill's brand-appropriate MCP data source,
skill name/version, and "This report is a point-in-time snapshot; no change is executed unless
confirmed in chat."
