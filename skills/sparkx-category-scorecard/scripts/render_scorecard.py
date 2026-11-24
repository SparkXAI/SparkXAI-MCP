#!/usr/bin/env python3
"""Render the scorecard report (markdown + one-page HTML) from category_scorecard.json, budget_room.json and summary.json.

  python3 render_scorecard.py --in out/category_scorecard.json --budget-room out/budget_room.json --summary summary.json \
      --top 15 --store "<store name>" --period "ads Nov 9-22, 2026 · market Oct 18-Nov 14 · peers week of Nov 1, 2026" --out out/

summary.json is the only text the model writes:
  {"headline": "...one sentence with a number...",
   "do_first": [{"owner": "Ad manager", "action": "...", "why": "..."}, ... at most 3],
   "opportunity": "...", "challenge": "...",
   "actions": [{"owner", "action", "objects", "size", "when", "check", "stop"}],
   "not_checked": "..."}
The script owns layout, tables, the 2x2 chart, legend and checks (headline has a number, at most 3 first actions).
"""
import argparse, html, json, os, re

POS = {"top quarter": "top 25%", "above median": "above median", "below median": "below median", "bottom quarter": "bottom 25%"}
PLAY_COLOR = {"Scale": "#1f5eff", "Keep": "#4b5563", "Hold (stock)": "#6b7280", "Fix ad cost": "#b26a00",
              "Fix listing": "#7a3cff", "Fix first": "#c4314b", "No read": "#6b7280"}
NL = "\n"


def money(v):
    v = v or 0
    return f"${v / 1000:.1f}K" if abs(v) >= 1000 else f"${v:.0f}"


def conv_txt(c):
    v, cov = c.get("converts_vs_market"), c.get("market_data_coverage")
    if v is None:
        return "no market data" + (f" ({c['converts_note']})" if c.get("converts_note") else "")
    if cov is not None and cov < 0.4:
        return "not measured - main products missing from market data (see Fix the data)"
    return f"{v:.2f}x" + (" (partial)" if cov is not None and cov < 0.6 else "")


def peer_txt(c):
    ad = c.get("play_ad_type")
    if not ad:
        base = c.get("peer_note") or "no peer row"
        return base + (f" · ACOS {c['acos_vs_account']:.2f}x account" if c.get("acos_vs_account") is not None else "")
    pr = c["peer_rows"][ad]
    unit = {"roas": "ROAS", "cpc": "cost per click", "cpm": "CPM"}[pr["metric"]]
    return (f"{ad} {pr['goal']} · {unit} {pr['own']:.2f} vs median {pr['p50']:.2f} ({POS[pr['position']]})"
            f" · {pr['level_name']}" + (f", {pr['period']}" if pr.get("period") else ""))


def play_txt(c):
    p = c["play"]
    if c.get("scale_scope"):
        p += " (" + c["scale_scope"].replace("Sponsored Brands", "SB").replace("Sponsored Display", "SD") + ")"
    return p


def rng(v, fmt="{:.2f}"):
    lo, hi = v or (None, None)
    if lo is None or hi is None:
        return "not returned"
    return fmt.format(lo) + " - " + fmt.format(hi)


def goals_rows(cs):
    out = []
    for c in cs:
        for pr in c.get("peer_goals", []):
            gs = pr["goal_set"]
            if pr["goal"] == "conversion":
                fair = f"ROAS {rng(gs['roas_range'])} (ACOS {rng(gs['acos_range'], '{:.1f}%')})"
                you = f"ROAS {pr['own']:.2f}" + (f" (ACOS {gs['own_acos']:.1f}%)" if gs.get("own_acos") else "")
            else:
                m = pr["metric"]
                fair = f"{m.upper()} {rng(gs[m + '_range'])}"
                you = f"{m.upper()} {pr['own']:.2f}"
            fair += " - wide spread: use the range, not the median" if gs.get("wide_spread") else f" · median {pr['p50']:.2f}"
            out.append((c["category"], f"{pr['ad']} · {pr['goal']}", fair, you, POS.get(pr["position"], "-"),
                        pr["level_name"] + (f", {pr['period']}" if pr.get("period") else "")))
    return out


def money_plan_md(br):
    p = br["plan"]; md = []
    md.append(f"## Where the money goes (budget {p['budget_mode']}, ACOS goal {p['acos_goal']:g}%){NL}")
    ev = p.get("event") or {}
    if ev.get("plan_only"):
        md.append(f"**{ev['name']} ({ev['start']} to {ev['end']}): plan only.** No budget lowering and no writes from this skill "
                  f"until {ev['moves_from']}; promotion budgets go to "
                  + ("sparkx-promo-monitor" if ev["in_progress"] else "sparkx-promo-prep") + f".{NL}")
    if p.get("tacos"):
        t = p["tacos"]
        goal = ""
        if t.get("goal"):
            goal = f" (goal {t['goal']:g}%" + (f"; extra capped at {money(t['capped_extra_per_week'])} a week)"
                                               if t.get("capped_extra_per_week") is not None else ")")
        md.append("**TACOS check:** (ad spend" + (" + DSP" if t.get("dsp_included") else "") + f") / all store sales = {t['now']}% now, "
                  f"about {t['after']}% after the ready moves{goal}" + ("" if t.get("dsp_included") else " - DSP not included") + f".{NL}")
        if t.get("goal_missed"):
            md.append(f"**This plan does not reach the TACOS goal:** {t['after']}% against {t['goal']:g}% is "
                      f"{t['shortfall_pts']:g} points short (cuts alone would leave {t['after_cuts_only']}%). "
                      "Closing the rest takes lower bids or better conversion, not more budget - see "
                      f"sparkx-sqp-insight.{NL}")
    md.append("| Move | Campaigns (ready) | Spend change | Sales change (estimate) |")
    md.append("|---|---|---|---|")
    md.append(f"| Raise daily budgets: under goal - 3, capped | {p['raise_campaigns']} ({p['raise_ready']}) | "
              f"+{money(p['raise_extra_per_week'])}/wk | +{money(p['raise_sales_per_week'])}/wk |")
    md.append(f"| Lower daily budgets: over goal + 5, not capped | {p['lower_campaigns']} ({p['lower_ready']}) | "
              f"-{money(p['savings_per_week'])}/wk | -{money(p['lower_sales_at_risk_per_week'])}/wk |")
    md.append(f"| Flag: over goal + 5 and capped - budget unchanged, keyword-level bids in sparkx-sqp-insight plan mode | {p['flag_campaigns']} | - | - |")
    if p.get("sb_kept_banner"):
        md.append(f"| Keep the SB banner (awareness allowance) | {p['sb_kept_banner']} | - | - |")
    md.append(f"| Not placed | - | {money(p['not_placed_per_week'])}/wk | - |")
    if p.get("cut_shortfall_per_week"):
        md.append(f"| Cut still needed (lowers do not reach the budget cut) | - | {money(p['cut_shortfall_per_week'])}/wk | - |")
    md.append("")
    md.append(f"Capped = {p['capped_rule']}. Not checked (no budget usage): {p['not_checked_campaigns']} campaign(s), "
              f"{money(p['not_checked_spend_14d'])} spend in 14 days. AI managed (not in the change list): {p['ai_managed_campaigns']}.{NL}")
    md.append(f"### Raise daily budgets (top 10){NL}")
    md.append("| Campaign | Type | ACOS 14d | Capped h/day | Daily budget | Extra sales/wk | Hold |")
    md.append("|---|---|---|---|---|---|---|")
    for r in br["raises"][:10]:
        md.append(f"| {r['campaign'][:58]} | {r['type']} | {r['acos']}% | {r['out_of_budget_hours_per_day']} | "
                  f"{r['daily_budget']:g} -> {r['new_daily_budget']:g} | +{money(r['sales_per_week'])} | {'; '.join(r['hold']) or '-'} |")
    md.append(f"{NL}### Lower daily budgets (top 10){NL}")
    md.append("| Campaign | Type | ACOS 14d | Spend 14d | Daily budget | Hold |")
    md.append("|---|---|---|---|---|---|")
    for r in br["lowers"][:10]:
        md.append(f"| {r['campaign'][:58]} | {r['type']} | {r['acos']}% | {money(r['spend_14d'])} | "
                  f"{r['daily_budget']:g} -> {r['new_daily_budget']:g} | {'; '.join(r['hold']) or '-'} |")
    if br.get("flags"):
        md.append(f"{NL}**Flags (budget unchanged):** " + "; ".join(f"{r['campaign'][:45]} (ACOS {r['acos']}%)" for r in br["flags"][:10]))
    if br.get("ai_managed"):
        md.append(f"{NL}**AI managed - adjust the group, not the campaign (sparkx-edit-ai-group; a group budget change rescales all its "
                  "campaigns):** " + "; ".join(f"{r['campaign'][:45]} (group {r.get('aiGroupName') or r.get('aiGroupId')})"
                                              for r in br["ai_managed"][:10]))
    md.append(f"{NL}Full list: change_list.csv - only ready = yes rows go to sparkx-edit-ads, after you confirm. "
              f"Extra sales = extra spend x the campaign's ROAS x 0.8: the next clicks cost more than the average ones.{NL}")
    return md


def money_plan_html(br, e):
    out, table = [], []

    def flush():
        if table:
            hdr = [c.strip() for c in table[0].strip("|").split("|")]
            body = "".join("<tr>" + "".join(f"<td>{e(c.strip())}</td>" for c in r.strip("|").split("|")) + "</tr>" for r in table[2:])
            out.append("<div class=tw><table><tr>" + "".join(f"<th>{e(h)}</th>" for h in hdr) + "</tr>" + body + "</table></div>")
            table.clear()
    for line in money_plan_md(br):
        for part in line.split(NL):
            if part.startswith("|"):
                table.append(part); continue
            flush()
            t = part.strip()
            if not t:
                continue
            if t.startswith("### "):
                out.append(f"<h3>{e(t[4:])}</h3>")
            elif t.startswith("## "):
                out.append(f"<h2>{e(t[3:])}</h2>")
            else:
                out.append("<p>" + e(t.replace("**", "")) + "</p>")
    flush()
    return "".join(out)


def check_summary(s):
    errs = []
    if not re.search(r"\d", s.get("headline", "")):
        errs.append("headline has no number")
    if len(s.get("do_first", [])) > 3:
        errs.append("more than 3 first actions")
    for d in s.get("do_first", []):
        if not re.search(r"\d", d.get("action", "") + d.get("why", "")):
            errs.append(f"first action without a number: {d.get('action', '')[:40]}")
    return errs


def chart_svg(cards):
    """2x2: x = converts vs market (0.3-1.3), y = ads vs peers' median (cost-adjusted; >1 better), bubbles by spend"""
    W, H, L, B = 640, 360, 56, 40
    pts = []
    for c in cards:
        ad = c.get("play_ad_type"); cv = c.get("converts_vs_market")
        cov = c.get("market_data_coverage")
        if not ad or cv is None or (cov is not None and cov < 0.4):
            continue
        pr = c["peer_rows"][ad]
        if not pr["own"] or not pr["p50"]:
            continue
        y = (pr["p50"] / pr["own"]) if pr["metric"] in ("cpc", "cpm") else (pr["own"] / pr["p50"])
        pts.append((c, max(0.3, min(1.3, cv)), max(0.3, min(3.0, y))))
    if not pts:
        return ""
    fx = lambda v: L + (v - 0.3) / 1.0 * (W - L - 16)
    fy = lambda v: H - B - (v - 0.3) / 2.7 * (H - B - 16)
    mx = max(c["ad_spend_14d"] for c, _, _ in pts) or 1
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Categories by shopper conversion and ad cost vs peers">',
           f'<rect x="{fx(0.8)}" y="{fy(3.0)}" width="{fx(1.3) - fx(0.8)}" height="{fy(1.0) - fy(3.0)}" fill="#eef3ff"/>',
           f'<line x1="{fx(0.8)}" y1="{fy(0.3)}" x2="{fx(0.8)}" y2="{fy(3.0)}" stroke="#c9ced6" stroke-dasharray="4 4"/>',
           f'<line x1="{fx(0.3)}" y1="{fy(1.0)}" x2="{fx(1.3)}" y2="{fy(1.0)}" stroke="#c9ced6" stroke-dasharray="4 4"/>',
           f'<text x="{fx(1.28)}" y="{fy(2.9)}" text-anchor="end" class="q">Scale</text>',
           f'<text x="{fx(0.32)}" y="{fy(2.9)}" class="q">Fix listing</text>',
           f'<text x="{fx(1.28)}" y="{fy(0.38)}" text-anchor="end" class="q">Fix ad cost</text>',
           f'<text x="{fx(0.32)}" y="{fy(0.38)}" class="q">Fix first</text>',
           f'<text x="{(L + W) / 2}" y="{H - 6}" text-anchor="middle" class="ax">Shoppers buy from you vs the market (1.0 = same)</text>',
           f'<text x="14" y="{(H - B) / 2}" transform="rotate(-90 14 {(H - B) / 2})" text-anchor="middle" class="ax">Ads vs peers\' median (1.0 = same, higher = better)</text>']
    for c, x, y in pts:
        r = 6 + 14 * (c["ad_spend_14d"] / mx) ** 0.5
        out.append(f'<circle cx="{fx(x):.0f}" cy="{fy(y):.0f}" r="{r:.0f}" fill="{PLAY_COLOR.get(c["play"], "#1f5eff")}" fill-opacity="0.75"/>')
        out.append(f'<text x="{fx(x) + r + 3:.0f}" y="{fy(y) + 4:.0f}" class="lb">{html.escape(c["category"])}</text>')
    out.append("</svg>")
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--summary")
    ap.add_argument("--top", type=int, default=15); ap.add_argument("--store", default=""); ap.add_argument("--period", default="")
    ap.add_argument("--budget-room"); ap.add_argument("--out", default=".")
    a = ap.parse_args(argv)

    def rd(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    br = rd(a.budget_room) if a.budget_room else None
    d = rd(a.inp); cs = d["categories"][: a.top]
    s = rd(a.summary) if a.summary else {}
    errs = check_summary(s) if s else []
    for x in errs:
        print("CHECK:", x)

    # ---------- markdown ----------
    md = [f"# Category Scorecard · {a.store}{NL}{NL}{a.period}{NL}"]
    if s:
        md.append(f"**{s['headline']}**{NL}")
        md.append(f"## Do this first{NL}")
        for i, x in enumerate(s["do_first"], 1):
            md.append(f"{i}. **{x['owner']}** · {x['action']} - {x['why']}")
        md.append(f"{NL}**Opportunity:** {s['opportunity']}{NL}{NL}**Challenge:** {s['challenge']}{NL}")
    if br:
        md += money_plan_md(br)
    md.append(f"## Scorecard (top {len(cs)} categories = {sum(c['share_of_ad_spend'] for c in cs) * 100:.0f}% of ad spend with a category){NL}")
    md.append("| Category | Ad spend 14d · ACOS | Shoppers buy vs market | Ads vs peers (median) | Play | When | Next |")
    md.append("|---|---|---|---|---|---|---|")
    for c in cs:
        md.append(f"| {c['category']} | {money(c['ad_spend_14d'])} · {c['acos_14d']}% | {conv_txt(c)} | {peer_txt(c)} | **{play_txt(c)}**"
                  + (f"<br>{c['play_note']}" if c.get("play_note") else "") + f" | {c.get('timing') or '-'} | {c.get('next') or '-'} |")
    md.append(f"{NL}- **Shoppers buy vs market**: your purchases per click / the market's, on generic searches. 1.00x = same as the market.")
    md.append("- **Ads vs peers**: your brand's figure vs the median of similar brands in the same browse category, by goal "
              "(conversion = ROAS, consideration = cost per click, awareness = CPM). Top 25% = better than three in four peers.")
    md.append("- **Play**: Scale = more budget where campaigns are capped under goal; Fix ad cost = keyword-level bids and targeting first; "
              "Fix listing = the page loses buyers; Fix first = page, price or product before more spend; Hold (stock) = refill first; "
              f"Keep = no raise while the category is above your ACOS goal.{NL}")
    if s.get("actions"):
        md.append(f"## Actions{NL}")
        md.append("| # | Owner | Action | Categories | Size | When | How we check | Stop if |")
        md.append("|---|---|---|---|---|---|---|---|")
        for i, x in enumerate(s["actions"], 1):
            md.append(f"| {i} | {x['owner']} | {x['action']} | {x['objects']} | {x['size']} | {x['when']} | {x['check']} | {x.get('stop', '-')} |")
        md.append("")
    gr = goals_rows(cs)
    md.append(f"## Fair peer goals (P25 - P75 of similar brands){NL}")
    md.append("| Category | Ad type · goal | Fair range | You | Position | Level, period |")
    md.append("|---|---|---|---|---|---|")
    for r in gr:
        md.append("| " + " | ".join(r) + " |")
    if not gr:
        md.append("| - | - | no usable peer rows in this pull | - | - | - |")
    if not d.get("sp_peer_rows"):
        md.append(f"{NL}Sponsored Products: no usable peer rows in this pull; SP goals stay at each category's own 14-day ACOS.")
    if d.get("unusable_peer_rows"):
        md.append(f"{NL}{len(d['unusable_peer_rows'])} peer rows not used: "
                  + "; ".join(sorted({u['reason'] for u in d['unusable_peer_rows']})) + ".")
    if d.get("data_fixes"):
        md.append(f"{NL}## Fix the data first{NL}")
        for f in d["data_fixes"]:
            md.append(f"- {f['category']} ({money(f['ad_spend_14d'])}): {f['fix']}")
    md.append(f"{NL}## Notes{NL}")
    for n in d["notes"] + d.get("market_notes", []):
        md.append(f"- {n}")
    md.append(f"- Scored {d['scored_share_of_ad_spend'] * 100:.0f}% of ad spend; {d['not_scored_small_count']} small categories listed only; "
              f"{money(d['unmapped_ad_spend'])} spend on products without a category.")
    if s.get("not_checked"):
        md.append(f"- Not checked: {s['not_checked']}")
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "report.md"), "w", encoding="utf-8") as f:
        f.write(NL.join(md) + NL)

    # ---------- html ----------
    e = html.escape
    rows = "".join(
        f"<tr><td><b>{e(c['category'])}</b></td><td>{money(c['ad_spend_14d'])}<br><span class=m>ACOS {c['acos_14d']}%</span></td>"
        f"<td>{e(conv_txt(c))}</td><td>{e(peer_txt(c))}</td>"
        f"<td><span class=pill style='background:{PLAY_COLOR.get(c['play'], '#6b7280')}'>{e(play_txt(c))}</span>"
        + (f"<div class=m>{e(c['play_note'])}</div>" if c.get("play_note") else "")
        + f"</td><td>{e(c.get('timing') or '-')}</td><td class=m>{e(c.get('next') or '-')}</td></tr>" for c in cs)
    acts = "".join(f"<tr><td>{i}</td><td>{e(x['owner'])}</td><td>{e(x['action'])}<div class=m>{e(x['objects'])}</div></td><td>{e(x['size'])}</td>"
                   f"<td>{e(x['when'])}</td><td>{e(x['check'])}</td><td>{e(x.get('stop', '-'))}</td></tr>"
                   for i, x in enumerate(s.get("actions", []), 1))
    goals_html = ("".join("<tr>" + "".join(f"<td>{e(v)}</td>" for v in r) + "</tr>" for r in gr)
                  or "<tr><td colspan=6>no usable peer rows in this pull</td></tr>")
    ps = d["peer_summary"]
    tiles = [(money(sum(c["ad_spend_14d"] for c in cs)), f"14-day ad spend in the top {len(cs)} categories"),
             (f"{ps['top quarter']} of {ps['categories_with_peer_row']}", "categories where your ads beat 3 in 4 peers"),
             (f"{d['converts_summary']['behind']} of {sum(d['converts_summary'].values())}", "categories where shoppers buy from you < 0.80x the market"),
             (str(len(d.get("data_fixes", []))), "big categories missing from market search data")]
    if br:
        P = br["plan"]
        tiles = [(f"+{money(P['fits_extra_per_week'])}/wk", f"placed in {P['raise_ready']} campaigns under goal (ready to confirm)"),
                 (f"+{money(P['raise_sales_per_week'])}/wk", "sales from those raises (estimate)"),
                 (f"{P['raise_campaigns']}", "campaigns under goal that run out of budget"),
                 (f"{P['lower_campaigns'] + P['flag_campaigns']}", "campaigns above your goal + 5 points")]
    fixes = ""
    if d.get("data_fixes"):
        fixes = ("<h2>Fix the data first</h2><ul class=legend>"
                 + "".join(f"<li>{e(f['category'])} ({money(f['ad_spend_14d'])}): {e(f['fix'])}</li>" for f in d["data_fixes"]) + "</ul>")
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Category Scorecard · {e(a.store)}</title><style>
body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#111827;background:#fff;margin:0}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px}} h1{{font-size:22px;margin:0}} h2{{font-size:17px;margin:28px 0 10px}} h3{{font-size:15px;margin:18px 0 8px}}
.sub{{color:#6b7280;font-size:13px}} .head{{font-size:20px;font-weight:650;margin:18px 0;color:#0b1b4d}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}} .tile{{background:#f4f6f9;border-radius:10px;padding:12px}}
.tile b{{font-size:22px;display:block}} .tile span{{font-size:12.5px;color:#4b5563}}
ol.first li{{margin:6px 0}} .oc{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .oc div{{background:#f4f6f9;border-radius:10px;padding:10px 12px}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13.5px}} th,td{{text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;vertical-align:top}}
th{{color:#4b5563;font-weight:600;background:#fafbfc}} .m{{color:#6b7280;font-size:12px;margin-top:3px}}
.pill{{color:#fff;border-radius:999px;padding:2px 9px;font-size:12px;white-space:nowrap}} .legend li{{margin:3px 0;font-size:13px;color:#374151}}
svg .q{{font:600 13px sans-serif;fill:#9aa3af}} svg .ax{{font:12px sans-serif;fill:#4b5563}} svg .lb{{font:11px sans-serif;fill:#111827}}
@media(max-width:600px){{.oc{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>Category Scorecard · {e(a.store)}</h1><div class=sub>{e(a.period)}</div>
<div class=head>{e(s.get('headline', ''))}</div>
<div class=tiles>{''.join(f'<div class=tile><b>{e(v)}</b><span>{e(t)}</span></div>' for v, t in tiles)}</div>
<h2>Do this first</h2><ol class=first>{''.join(f"<li><b>{e(x['owner'])}</b> · {e(x['action'])} <span class=m>- {e(x['why'])}</span></li>" for x in s.get('do_first', []))}</ol>
<div class=oc><div><b>Opportunity</b><br>{e(s.get('opportunity', ''))}</div><div><b>Challenge</b><br>{e(s.get('challenge', ''))}</div></div>
{money_plan_html(br, e) if br else ''}
<h2>Where each category sits</h2>{chart_svg(cs)}
<div class=m>Bubble size = ad spend. Categories without usable market data or peer rows are in the table only.</div>
<h2>Scorecard</h2><div class=tw><table><tr><th>Category</th><th>Ad spend 14d</th><th>Shoppers buy vs market</th><th>Ads vs peers (median)</th><th>Play</th><th>When</th><th>Next</th></tr>{rows}</table></div>
<ul class=legend><li><b>Shoppers buy vs market</b>: your purchases per click / the market's on generic searches; 1.00x = same.</li>
<li><b>Ads vs peers</b>: your brand's figure vs the median of similar brands in the same browse category, by goal (conversion = ROAS, consideration = cost per click, awareness = CPM).</li>
<li><b>Play</b>: Scale = more budget where capped under goal · Fix ad cost = keyword-level bids and targeting · Fix listing = the page loses buyers · Fix first = page or price before spend · Hold = refill stock · Keep = no raise above your ACOS goal.</li></ul>
{('<h2>Actions</h2><div class=tw><table><tr><th>#</th><th>Owner</th><th>Action</th><th>Size</th><th>When</th><th>How we check</th><th>Stop if</th></tr>' + acts + '</table></div>') if acts else ''}
<h2>Fair peer goals (P25 - P75 of similar brands)</h2><div class=tw><table><tr><th>Category</th><th>Ad type · goal</th><th>Fair range</th><th>You</th><th>Position</th><th>Level, period</th></tr>{goals_html}</table></div>
{fixes}
<h2>Notes</h2><ul class=legend>{''.join(f'<li>{e(n)}</li>' for n in d['notes'] + d.get('market_notes', []))}{('<li>Not checked: ' + e(s['not_checked']) + '</li>') if s.get('not_checked') else ''}</ul>
</main></body></html>"""
    with open(os.path.join(a.out, "report.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote report.md, report.html" + (f" - {len(errs)} check(s) failed" if errs else ""))
    return errs


if __name__ == "__main__":
    main()
