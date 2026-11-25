#!/usr/bin/env python3
"""Budget direction: which campaign daily budgets go up, which go down, and what money is not placed.

  python3 budget_room.py --campaigns camp14.json --entities campaign_meta.json --ai-groups ai_groups.json \
      --recent-changes oplog.json --acos-goal 25 --budget "+10%" --window-days 14 \
      --stock stock_days.json --campaign-asins campaign_asins.json --daily daily30.json \
      --total-sales-14d 410000 --event "Black Friday to Cyber Monday|2026-11-27|2026-11-30" --today 2026-11-23 --out out/

Inputs (tool field names; references/data-contract.md):
  --campaigns   get_ads_perf factEntity=campaign, 14 days: campaign.campaignId_ (Amazon id), campaign.campaignName_,
                campaign.campaignType_, Spend, Sales.
  --entities    get_entity_metadata entity=campaign with budgetUsageDateStart/End over the same window: campaignId (internal),
                profileId, amazonCampaignId, campaignName, campaignType, campaignState, dailyBudget, budgetType, aiGroupId,
                budgetUsage.{outOfBudgetMinutes, inBudgetMinutes}.
  --ai-groups   get_entity_metadata entity=aiGroup: aiGroupId, aiStatus (1 = AI running).
  --recent-changes  get_operation_log rows (amazonCampaignId) for the last 7 days, or a list of Amazon campaign ids.

Rules (references/rules.md section 7):
  Capped     out of budget on average >= --min-oob-hours (default 3) hours a day over the window, from outOfBudgetMinutes.
             budgetUsage null / minutes null = "not checked" (no move), never 0. outOfBudgetPercentage is never used.
  Raise      ACOS <= goal - 3 and capped. Step by hours capped a day: 3-6 h +20%, 6-12 h +35%, >= 12 h +50%.
             With --daily: at least the de-spiked peak day (2nd highest of 30) x 1.1. Never more than +50% a step;
             rounded up to a whole currency unit; never below --budget-floor (10).
             Extra spend a week = weekly spend x lift (upper bound). Sales = extra x the campaign's ROAS x 0.8.
  Lower      ACOS > goal + 5, >= --min-lower-spend (2,000) in 14 days, usage checked and NOT capped:
             new budget = 80% of today's average daily spend, at least 50% of the old budget and the floor.
  Flag       ACOS > goal + 5 and capped: budget unchanged; "lower bids at keyword level - see sparkx-sqp-insight plan mode".
  SB banner  SB between goal + 5 and goal x 2.0 (x 1.4 for the efficiency goal): kept, listed for a creative / landing check.
  Not in the change list: campaigns in an AI managed group whose AI is on (listed under ai_managed - adjust the group with
             sparkx-edit-ai-group; a group budget change rescales all its campaigns) and groups whose AI status is unknown.
  Held       (in change_list.csv with ready=no) < 30 days of stock, or a raise whose products' stock is not confirmed
             (no --campaign-asins mapping from productAd and no ASIN in the name, or any mapped ASIN without a stock
             figure - the minimum is only taken when every product has one); changed in the last 7 days; lifetime budget
             (campaign.updateBudget covers daily budgets only); no internal campaignId; event window.
  Event      from 7 days before the start through the last day (in progress included): plan only - every row ready=no,
             no lowering; promotions go to sparkx-promo-prep / sparkx-promo-monitor.
  Budget     raises fit the confirmed budget, best ROAS first: same = funded by lowers; +x% adds x% of weekly spend;
             -x% needs the cut from lowers first. What no campaign earns under goal is reported as not placed.
  TACOS      (ad spend + DSP) / all store sales, now and after the ready moves; with --tacos-goal the weekly extra is
             capped, then the final combination is judged: still over the goal -> the shortfall is stated; raises that do
             not improve it are held and "after" is recomputed from the ready cuts.
"""
import argparse, csv, json, math, os, re
from collections import defaultdict
from datetime import date, timedelta

AD = {"sponsoredProducts": "SP", "sponsoredBrands": "SB", "sponsoredDisplay": "SD"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rows_of(obj):
    if isinstance(obj, dict) and isinstance(obj.get("data"), (dict, list)):
        obj = obj["data"]
    if isinstance(obj, list):
        return obj
    return obj.get("rows") or obj.get("list") or obj.get("records") or []


def g(r, *names):
    for n in names:
        if r.get(n) not in (None, ""):
            return r[n]
    return None


def fnum(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaigns", required=True); ap.add_argument("--entities", required=True)
    ap.add_argument("--ai-groups"); ap.add_argument("--recent-changes")
    ap.add_argument("--acos-goal", type=float, required=True); ap.add_argument("--budget", default="same", help="same / +10%% / -10%%")
    ap.add_argument("--goal", default="sales", choices=["sales", "efficiency", "traffic"])
    ap.add_argument("--window-days", type=float, default=14, help="length of the budgetUsage window in days")
    # The spend in --campaigns comes from its own get_ads_perf window, which is 14 days by the data
    # contract and is NOT the budgetUsage window. Keep the two apart: dividing spend by
    # --window-days doubles the average daily spend whenever the usage window is shorter.
    ap.add_argument("--spend-days", type=float, default=14,
                    help="length of the --campaigns spend window in days (default 14; independent of --window-days)")
    ap.add_argument("--min-oob-hours", type=float, default=3.0, help="capped = out of budget at least this many hours a day on average")
    ap.add_argument("--max-lift", type=float, default=0.5); ap.add_argument("--budget-floor", type=float, default=10.0)
    # C3: an absolute floor alone never fires on a small account, so the gate is the SMALLER of
    # --min-lower-spend and --min-lower-share of the window's total ad spend. --min-lower-spend 0
    # turns the absolute floor off; --min-lower-share 0 keeps the old absolute-only behaviour.
    ap.add_argument("--min-lower-spend", type=float, default=2000)
    ap.add_argument("--min-lower-share", type=float, default=0.01,
                    help="a campaign is big enough to act on at this share of the window's total ad spend (default 1%%)")
    ap.add_argument("--stock", help="{asin or parent: days of stock}"); ap.add_argument("--campaign-asins", help="{campaign id: [asins]}")
    ap.add_argument("--daily", help="[{campaign.campaignId_, date, Spend}] 30 days")
    ap.add_argument("--total-spend-14d", type=float, help="base for the +x%% budget (default: sum of --campaigns)")
    ap.add_argument("--total-sales-14d", type=float, help="all store sales, 14 days (TotalSalesAmount) - for TACOS")
    ap.add_argument("--ad-spend-all-14d", type=float); ap.add_argument("--dsp-spend-14d", type=float, default=0.0)
    ap.add_argument("--tacos-goal", type=float)
    ap.add_argument("--event"); ap.add_argument("--today")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    G = a.acos_goal
    today = date.fromisoformat(a.today) if a.today else date.today()
    camps = rows_of(load(a.campaigns))
    ents = {str(g(e, "amazonCampaignId")): e for e in rows_of(load(a.entities)) if g(e, "amazonCampaignId")}
    ai = {str(x.get("aiGroupId")): x for x in (rows_of(load(a.ai_groups)) if a.ai_groups else [])}
    recent = set()
    if a.recent_changes:
        rc = load(a.recent_changes)
        for x in (rc if isinstance(rc, list) else rows_of(rc)):
            recent.add(str(x.get("amazonCampaignId")) if isinstance(x, dict) else str(x))
    stock = load(a.stock) if a.stock else {}
    casins = {str(k): v for k, v in (load(a.campaign_asins) if a.campaign_asins else {}).items()}
    peaks = {}
    if a.daily:
        dd = defaultdict(list)
        for x in rows_of(load(a.daily)):
            dd[str(g(x, "campaign.campaignId_", "campaignId_", "campaignId"))].append(fnum(x.get("Spend")) or 0)
        peaks = {k: (sorted(v, reverse=True)[1] if len(v) > 1 else v[0]) for k, v in dd.items() if v}
    ev = None
    if a.event:
        n, s, e = a.event.split("|")
        s, e = date.fromisoformat(s), date.fromisoformat(e)
        ev = {"name": n, "start": s, "end": e, "reset": e + timedelta(days=1), "days": (s - today).days}
        ev["plan_only"] = ev["days"] <= 7 and today <= e          # in progress (days < 0) is held too
        ev["in_progress"] = ev["days"] <= 0 and today <= e
    fd = lambda d: d.strftime("%b ") + str(d.day)
    min_oob_min = a.min_oob_hours * 60 * a.window_days

    # Two different totals, which must not share a variable:
    #   win_spend  - ad spend over the --campaigns window (--spend-days). Base for the +x% budget
    #                and for the --min-lower-share size gate.
    #   acct_14d   - the account's ad spend over 14 days, the denominator TACOS needs.
    # They coincide only when the campaigns pull is itself 14 days.
    win_spend = a.total_spend_14d or sum(fnum(g(c, "Spend")) or 0 for c in camps)
    acct_14d = a.ad_spend_all_14d
    if acct_14d is None and a.spend_days == 14:
        acct_14d = win_spend
    pct = 0.0 if a.budget.strip().lower() == "same" else float(a.budget.replace("%", "")) / 100
    # Weekly figures come from the SPEND window, which is --spend-days and not always 14.
    # Dividing by 2 silently assumed 14 and halved every weekly number on a 7-day pull.
    per_week = lambda v: (v or 0) * 7.0 / a.spend_days
    extra_allowed = per_week(pct * win_spend)  # a week
    # C3: the smaller of the absolute floor and a share of the window's spend, so the gate scales
    # with the account. 0 on either side turns that side off; both 0 means no size gate at all.
    _gates = [x for x in (a.min_lower_spend, a.min_lower_share * win_spend) if x > 0]
    min_lower = min(_gates) if _gates else 0.0

    raises, lowers, flags, kept_sb, ai_managed, not_checked, held = [], [], [], [], [], [], []
    too_small = []   # C2: over goal, but no campaign-level budget move is possible
    for c in camps:
        aid = str(g(c, "campaign.campaignId_", "campaignId_", "amazonCampaignId", "campaignId"))  # get_ads_perf ids are Amazon ids
        e = ents.get(aid) or {}
        name = g(c, "campaign.campaignName_", "campaignName_", "campaignName") or e.get("campaignName") or ""
        ctype = g(c, "campaign.campaignType_", "campaignType_", "campaignType") or e.get("campaignType")
        spend, sales = fnum(c.get("Spend")) or 0, fnum(c.get("Sales")) or 0
        acos = spend / sales * 100 if sales else None
        old = fnum(e.get("dailyBudget"))
        row = {"campaign": name, "amazonCampaignId": aid, "campaignId": e.get("campaignId"), "profileId": e.get("profileId"),
               "campaignType": ctype, "type": AD.get(ctype, "-"), "budgetType": e.get("budgetType") or "daily",
               "spend_14d": round(spend), "sales_14d": round(sales), "acos": round(acos, 1) if acos is not None else None,
               "daily_budget": old, "aiGroupId": e.get("aiGroupId")}
        if e.get("aiGroupId"):
            grp = ai.get(str(e["aiGroupId"]))
            st = grp.get("aiStatus") if grp else None
            if st is None or int(st) == 1:
                row["note"] = ("AI managed group with AI on" if st is not None else "in an AI managed group; AI status not checked") + \
                              " - adjust the group (sparkx-edit-ai-group); a group budget change rescales all its campaigns"
                row["aiGroupName"] = (grp or {}).get("aiGroupName")
                ai_managed.append(row); continue
        u = e.get("budgetUsage") if e else None
        oob = fnum((u or {}).get("outOfBudgetMinutes"))
        if not e or u is None or oob is None:
            row["reason"] = "budget usage not checked" if e else "no campaign metadata matched (no internal campaignId)"
            not_checked.append(row); continue
        hrs = oob / 60 / a.window_days
        row["out_of_budget_hours_per_day"] = round(hrs, 1)
        capped = oob >= min_oob_min
        ids = casins.get(aid) or casins.get(str(e.get("campaignId"))) or re.findall(r"B0[0-9A-Z]{8}", name)
        known = {x: fnum(stock.get(x)) for x in ids}
        row["stock_unknown_asins"] = [x for x, v in known.items() if v is None]
        # every product the campaign advertises needs a stock figure: one unknown product could be the one running out
        row["stock_days"] = min(known.values()) if known and not row["stock_unknown_asins"] else None
        row["stock_days_known_min"] = min((v for v in known.values() if v is not None), default=None)
        weekly = per_week(spend)
        roas = sales / spend if spend else 0
        if acos is not None and acos <= G - 3 and capped and old:
            lift = 0.2 if hrs < 6 else (0.35 if hrs < 12 else 0.5)
            lift = min(lift, a.max_lift)
            nb = math.ceil(old * (1 + lift)); basis = f"capped {hrs:.1f} h a day"
            pk = peaks.get(aid)
            if pk and pk * 1.1 > nb:
                nb = min(math.ceil(pk * 1.1), math.ceil(old * (1 + a.max_lift))); basis = "de-spiked 30-day peak day x 1.1"
            nb = max(nb, math.ceil(a.budget_floor))
            lift = nb / old - 1
            row.update({"move": "raise", "new_daily_budget": nb, "lift": round(lift, 2), "sizing": basis,
                        "extra_per_week": round(weekly * lift), "sales_per_week": round(weekly * lift * roas * 0.8),
                        "reason": f"ACOS {acos:.1f}% <= goal {G:g} - 3 and out of budget about {hrs:.1f} h a day"})
            raises.append(row)
        elif acos is not None and acos > G + 5 and capped:
            row.update({"move": "flag", "reason": f"ACOS {acos:.1f}% above goal + 5 and out of budget about {hrs:.1f} h a day: "
                        "budget unchanged; lower bids at keyword level - see sparkx-sqp-insight plan mode"})
            flags.append(row)
        elif row["type"] == "SB" and acos is not None and G + 5 < acos <= G * (1.4 if a.goal == "efficiency" else 2.0) \
                and spend >= min_lower:
            row["note"] = "SB banner inside the awareness allowance: kept; check creative and landing"
            kept_sb.append(row)
        elif (acos is not None and acos > G + 5 or (acos is None and spend >= min_lower)) and spend >= min_lower and old:
            avg_daily = spend / a.spend_days
            nb = max(math.ceil(min(old, avg_daily) * 0.8), math.ceil(old * 0.5), math.ceil(a.budget_floor))
            if nb < old and nb < avg_daily:   # a cut that stays above the daily spend changes nothing
                saving = max(min(old, avg_daily) - nb, 0) * 7
                row.update({"move": "lower", "new_daily_budget": nb, "lift": round(nb / old - 1, 2),
                            "saving_per_week": round(saving), "sales_at_risk_per_week": round(saving * roas * 0.8),
                            "reason_code": "lower", "reason_args": {"acos": acos, "goal": G, "hrs": round(hrs, 1)},
                            "reason": (f"ACOS {acos:.1f}% > goal {G:g} + 5" if acos is not None else "spend with no sales")
                            + f", not capped ({hrs:.1f} h a day): budget to 80% of the average daily spend"})
                lowers.append(row)
            else:
                # C2: the cut would be a no-op (budget already at or under the floor, or under the
                # average daily spend). Never drop the row - this is real waste the reader must see.
                row.update({"move": "too small to act on", "new_daily_budget": None,
                            "reason_code": "noop_cut",
                            "reason_args": {"acos": acos, "goal": G, "budget": old,
                                            "floor": a.budget_floor, "avg": round(avg_daily, 2)},
                            "reason": (f"ACOS {acos:.1f}% > goal {G:g} + 5" if acos is not None else "spend with no sales")
                            + f": a cut is a no-op - daily budget {old:g} against the {a.budget_floor:g} floor and"
                            + f" {avg_daily:.2f} average daily spend. Lower bids at keyword level"
                            + " (sparkx-sqp-insight plan mode) or pause the campaign."})
                too_small.append(row)
        elif acos is not None and acos > G + 5 and old:
            # C2: over goal but under the size gate - listed, never dropped
            row.update({"move": "too small to act on", "new_daily_budget": None,
                        "reason_code": "under_gate",
                        "reason_args": {"acos": acos, "goal": G, "spend": round(spend),
                                        "days": a.spend_days, "gate": round(min_lower)},
                        "reason": f"ACOS {acos:.1f}% > goal {G:g} + 5 but only {spend:.0f} spent in"
                                  f" {a.spend_days:g} days, under the {min_lower:.0f} a budget move needs:"
                                  " lower bids at keyword level (sparkx-sqp-insight plan mode) or pause the campaign."})
            too_small.append(row)

    # holds that keep a row in the CSV but not ready
    def hold(r):
        hs = []
        if r["move"] == "raise" and r.get("stock_unknown_asins"):
            hs.append("stock unknown for " + ", ".join(r["stock_unknown_asins"][:5])
                      + (f" (+{len(r['stock_unknown_asins']) - 5} more)" if len(r["stock_unknown_asins"]) > 5 else "")
                      + ": every advertised product needs a stock figure before a raise")
        elif r["move"] == "raise" and r.get("stock_days") is None:
            hs.append("stock not confirmed for this campaign's products"
                      + ("" if stock else " (no --stock data)") + ": pass --campaign-asins or check by hand")
        elif r["move"] == "raise" and r["stock_days"] < 30:
            hs.append(f"{r['stock_days']:g} days of stock: refill first")
        if r["amazonCampaignId"] in recent:
            hs.append("budget changed in the last 7 days")
        if r["budgetType"] == "lifetime":
            hs.append("lifetime budget: campaign.updateBudget covers daily budgets only")
        if not r.get("campaignId") or not r.get("profileId"):
            hs.append("no internal campaignId / profileId")
        if ev and ev["plan_only"]:
            hs.append(f"{ev['name']} window: plan only (" + ("in progress - sparkx-promo-monitor" if ev["in_progress"]
                                                            else f"before it - sparkx-promo-prep") + ")")
        return hs

    for r in raises + lowers:
        r["hold"] = hold(r)
        r["when"] = (f"from {fd(ev['reset'])}" if ev and ev["plan_only"] else "after confirmation")
    ready_raises = [r for r in raises if not r["hold"]]
    ready_lowers = [r for r in lowers if not r["hold"]]

    tacos = None
    tacos_skipped = None
    if a.total_sales_14d and acct_14d is None:
        # A non-14-day campaigns window with no 14-day account figure: any TACOS here would divide
        # a shorter window of spend by 14 days of sales. Say why instead of printing a wrong number.
        tacos_skipped = (f"TACOS not shown: --campaigns covers {a.spend_days:g} days, and no 14-day "
                         "account ad spend was given. Pass --ad-spend-all-14d to get it.")
    if a.total_sales_14d and acct_14d is not None:
        spend_all = acct_14d + a.dsp_spend_14d
        tacos = {"now": round(spend_all / a.total_sales_14d * 100, 2), "goal": a.tacos_goal, "dsp_included": a.dsp_spend_14d > 0}
        if a.tacos_goal:
            ex = sum(r["extra_per_week"] for r in ready_raises) or 1
            r_est = sum(r["sales_per_week"] for r in ready_raises) / ex
            gg = a.tacos_goal / 100
            cap = max((gg * a.total_sales_14d - spend_all) / (2 * (1 - gg * r_est)), 0) if gg * r_est < 1 else None
            if cap is not None and cap < max(extra_allowed, 0) + sum(r["saving_per_week"] for r in ready_lowers):
                tacos["capped_extra_per_week"] = round(cap)
    savings = sum(r["saving_per_week"] for r in ready_lowers)
    room = extra_allowed + savings
    if tacos and tacos.get("capped_extra_per_week") is not None:
        room = min(room, tacos["capped_extra_per_week"] + savings)
    used = 0
    for r in sorted(ready_raises, key=lambda r: -(r["sales_14d"] / max(r["spend_14d"], 1))):
        r["fits_budget"] = used + r["extra_per_week"] <= room
        if r["fits_budget"]:
            used += r["extra_per_week"]
        else:
            r["hold"].append("does not fit the confirmed budget")

    # the cap above bounds the NET extra, so cuts can fund raises back to it; that still misses the goal
    # when today's TACOS is already past it. Check the final combination, not the allowance.
    if tacos and a.tacos_goal:
        placed = [r for r in ready_raises if r["fits_budget"]]
        cut_sales = sum(r["sales_at_risk_per_week"] for r in ready_lowers)
        base_spend = acct_14d + a.dsp_spend_14d
        proj = lambda ex, sl: (base_spend + (ex - savings) * 2) / (a.total_sales_14d + (sl - cut_sales) * 2) * 100
        after = proj(used, sum(r["sales_per_week"] for r in placed))
        cuts_only = proj(0, 0)
        tacos["after"] = round(after, 2)
        if after > a.tacos_goal:
            # the cap bounds the NET extra, so cuts fund raises back up to it; past the goal the cap is 0 and
            # the cuts alone decide. Judge the final combination, and only hold raises that do not help it.
            tacos["after_cuts_only"] = round(cuts_only, 2)
            tacos["shortfall_pts"] = round(after - a.tacos_goal, 2)
            tacos["goal_missed"] = True
            if after >= cuts_only - 0.01:
                for r in placed:
                    r["hold"].append(f"projected TACOS {after:.1f}% stays above the {a.tacos_goal:g}% goal and the raise "
                                     f"does not improve it (cuts alone: {cuts_only:.1f}%): cut first")
                    r["fits_budget"] = False
                used = 0
                # the raises are now held: "after" is what the ready moves (the cuts) give
                tacos["after"] = round(cuts_only, 2)
                tacos["shortfall_pts"] = round(max(cuts_only - a.tacos_goal, 0), 2)
                tacos["goal_missed"] = cuts_only > a.tacos_goal
            else:
                for r in placed:
                    r["tacos_note"] = (f"plan still ends at {after:.1f}% TACOS vs the {a.tacos_goal:g}% goal "
                                       f"({tacos['shortfall_pts']:g} pts short); this raise lowers it, cuts alone would "
                                       f"leave {cuts_only:.1f}%")
    elif tacos:
        add = (used - savings) * 2
        add_sales = (sum(r["sales_per_week"] for r in ready_raises if r["fits_budget"])
                     - sum(r["sales_at_risk_per_week"] for r in ready_lowers)) * 2
        tacos["after"] = round((acct_14d + a.dsp_spend_14d + add)
                               / (a.total_sales_14d + add_sales) * 100, 2)
    plan = {"acos_goal": G, "budget_mode": a.budget, "window_days": a.window_days,
            "spend_days": a.spend_days,
            "capped_rule": f"out of budget >= {a.min_oob_hours:g} h a day on average (>= {round(min_oob_min):,} min in {a.window_days:g} days)",
            "extra_allowed_per_week": round(extra_allowed), "savings_per_week": round(savings),
            "raise_campaigns": len(raises), "raise_ready": sum(1 for r in raises if not r["hold"]),
            "raise_extra_per_week": round(sum(r["extra_per_week"] for r in raises if not r["hold"])),
            "raise_sales_per_week": round(sum(r["sales_per_week"] for r in raises if not r["hold"])),
            "lower_campaigns": len(lowers), "lower_ready": len(ready_lowers),
            "lower_spend_now_per_week": round(per_week(sum(r["spend_14d"] for r in lowers))),
            "lower_sales_at_risk_per_week": round(sum(r["sales_at_risk_per_week"] for r in ready_lowers)),
            "flag_campaigns": len(flags), "sb_kept_banner": len(kept_sb), "ai_managed_campaigns": len(ai_managed),
            "too_small_campaigns": len(too_small), "too_small_spend": round(sum(r["spend_14d"] for r in too_small)),
            "min_lower_used": round(min_lower), "min_lower_share": a.min_lower_share,
            "total_spend_window": round(win_spend),
            "account_spend_14d": round(acct_14d) if acct_14d is not None else None,
            "ai_managed_spend": round(sum(r["spend_14d"] for r in ai_managed)),
            "total_campaigns": len(camps),
            "candidate_campaigns": len(camps) - len(ai_managed) - len(not_checked),
            "not_checked_campaigns": len(not_checked), "not_checked_spend_14d": round(sum(r["spend_14d"] for r in not_checked)),
            "fits_extra_per_week": round(used)}
    plan["not_placed_per_week"] = round(max(room - used, 0))
    plan["cut_shortfall_per_week"] = round(max(-room, 0)) if pct < 0 else 0
    plan["under_floor"] = sum(1 for e in ents.values() if fnum(e.get("dailyBudget")) and fnum(e.get("dailyBudget")) < a.budget_floor)
    if tacos:
        plan["tacos"] = tacos
    if tacos_skipped:
        plan["tacos_skipped"] = tacos_skipped
    if ev:
        plan["event"] = {"name": ev["name"], "start": ev["start"].isoformat(), "end": ev["end"].isoformat(),
                         "plan_only": ev["plan_only"], "in_progress": ev["in_progress"], "moves_from": fd(ev["reset"])}
    out = {"plan": plan, "raises": sorted(raises, key=lambda r: -r["extra_per_week"]), "lowers": sorted(lowers, key=lambda r: -r["spend_14d"]),
           "flags": flags, "sb_kept": kept_sb, "ai_managed": ai_managed, "not_checked": not_checked,
           "too_small": sorted(too_small, key=lambda r: -r["spend_14d"])}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "budget_room.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    cols = ["ready", "move", "profileId", "campaignId", "amazonCampaignId", "campaignName", "campaignType", "budgetType",
            "dailyBudget_old", "dailyBudget_new", "budget.type", "budget.amount", "acos_14d", "spend_14d",
            "out_of_budget_hours_per_day", "extra_spend_week", "extra_sales_week", "when", "reason", "hold"]
    with open(os.path.join(a.out, "change_list.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in out["raises"] + out["lowers"]:
            ready = "yes" if not r["hold"] else "no"
            w.writerow([ready, r["move"], r["profileId"], r["campaignId"], r["amazonCampaignId"], r["campaign"], r["campaignType"],
                        r["budgetType"], r["daily_budget"], r["new_daily_budget"], "setTo", r["new_daily_budget"], r["acos"], r["spend_14d"],
                        r.get("out_of_budget_hours_per_day"), r.get("extra_per_week", -r.get("saving_per_week", 0)),
                        r.get("sales_per_week", -r.get("sales_at_risk_per_week", 0)), r["when"], r["reason"], "; ".join(r["hold"])])
        for r in flags:
            w.writerow(["no", "flag", r["profileId"], r["campaignId"], r["amazonCampaignId"], r["campaign"], r["campaignType"],
                        r["budgetType"], r["daily_budget"], "", "", "", r["acos"], r["spend_14d"], r.get("out_of_budget_hours_per_day"),
                        "", "", "", r["reason"], "budget unchanged"])
    return out


if __name__ == "__main__":
    print(json.dumps(main()["plan"], indent=1, default=str))
