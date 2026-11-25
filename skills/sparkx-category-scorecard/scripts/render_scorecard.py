#!/usr/bin/env python3
"""Render the scorecard report (markdown + one-page HTML) from category_scorecard.json, budget_room.json and summary.json.

  python3 render_scorecard.py --in out/category_scorecard.json --budget-room out/budget_room.json --summary summary.json \
      --top 15 --store "<store name>" --period "ads Nov 9-22, 2026 - market Oct 18-Nov 14 - peers week of Nov 1, 2026" \
      --lang en --out out/

summary.json is the only text the model writes, and it is written IN THE USER'S LANGUAGE:
  {"headline": "...one sentence with a number...",
   "do_first": [{"owner": "Ad manager", "action": "...", "why": "..."}, ... at most 3],
   "opportunity": "...", "challenge": "...",
   "actions": [{"owner", "action", "objects", "size", "when", "check", "stop"}],
   "not_checked": "..."}
The script owns layout, tables, the 2x2 chart, legend and checks (headline has a number, at most 3 first actions).

--lang sets the language of everything the SCRIPT writes (headings, table headers, legend, chart
labels): en, zh or ja. It must match the language of summary.json - pass the language the user is
speaking. Values that come from the data (campaign names, categories, peer level names) are never
translated.
"""
import argparse, html, json, os, re

NL = "\n"
PLAY_COLOR = {"Scale": "#1f5eff", "Keep": "#4b5563", "Hold (stock)": "#6b7280", "Fix ad cost": "#b26a00",
              "Fix listing": "#7a3cff", "Fix first": "#c4314b", "No read": "#6b7280"}

# ---------------------------------------------------------------- i18n
# Every string the script itself writes. Keys are stable; only the values are translated.
L = {
 "en": {
  "title": "Category Scorecard",
  "pgoal": {"conversion": "conversion", "consideration": "consideration", "awareness": "awareness"},
  "nt_no_data_no_peer": "no market data and no peer row",
  "nt_market_unavailable": "market data not accessible ({reason}): judged on peers and ACOS",
  "nt_vendor_no_sqp": "Vendor or no SQP: judged on peers and ACOS",
  "nt_ads_only": "based on ads only (market data missing or not usable)",
  "nt_market_only": "based on market data only (no peer row)",
  "nt_coverage": "market data covers {pct}% of spend",
  "nt_evidence_adtype": "evidence is {ad} only",
  "nt_acos_above_goal": "category ACOS {acos}% is above your {goal:g}% goal: no raise until it is back under",
  "nt_close_to_market": "check the page as you scale (close to market, not ahead)",
  "nt_low_stock": "main product: {days:g} days of stock",
  "nt_roas_bottom": "{ad} ROAS {roas} is in peers bottom 25% (median {median}): check before adding budget",
  "nx_none": "-", "nx_std_no_sqp": "sparkx-search-term-diagnosis (search terms; no SQP)",
  "nx_raises_in_csv": "budget raises in change_list.csv",
  "nx_sqp_plan": "sparkx-sqp-insight plan mode: {goal}",
  "tm_none": "-", "tm_now_page": "now (page work)", "tm_refill_now": "refill now",
  "tm_from_date": "from {date}", "tm_page_now_ads_from": "page now; ad cost from {date}",
  "tm_plan_only_in_progress": "plan only; sparkx-promo-monitor (event in progress)",
  "tm_plan_only_before": "plan only; before {start} via sparkx-promo-prep",
  "goal_Both (listing first)": "Both (listing first)", "goal_Grow": "Grow", "goal_Improve efficiency": "Improve efficiency", "do_first": "Do this first", "opportunity": "Opportunity", "challenge": "Challenge",
  "money": "Where the money goes (budget {mode}, ACOS goal {goal:g}%)",
  "plan_only": "**{name} ({start} to {end}): plan only.** No budget lowering and no writes from this skill until {from_}; promotion budgets go to {skill}.",
  "tacos": "**TACOS check:** (ad spend{dsp}) / all store sales = {now}% now, about {after}% after the ready moves{goal}{nodsp}.",
  "tacos_goal": " (goal {goal:g}%", "tacos_capped": "; extra capped at {v} a week)", "tacos_plain": ")",
  "tacos_dsp": " + DSP", "tacos_nodsp": " - DSP not included",
  "tacos_missed": "**This plan does not reach the TACOS goal:** {after}% against {goal:g}% is {pts:g} points short (cuts alone would leave {cuts}%). Closing the rest takes lower bids or better conversion, not more budget - see {skill}.",
  "rsn_lower": "ACOS {acos:.1f}% > goal {goal:g} + 5, not capped ({hrs} h a day): budget to 80% of the average daily spend.",
  "rsn_noop_cut": "ACOS {acos:.1f}% > goal {goal:g} + 5, but a cut is a no-op: the daily budget is {budget:g} against the {floor:g} floor, and average daily spend is {avg}. Lower bids at keyword level (sparkx-sqp-insight plan mode) or pause the campaign.",
  "rsn_under_gate": "ACOS {acos:.1f}% > goal {goal:g} + 5, but only {spend} spent in {days:g} days - under the {gate} a budget move needs. Lower bids at keyword level (sparkx-sqp-insight plan mode) or pause the campaign.",
  "h_move": "Move", "h_camp_ready": "Campaigns (ready)", "h_spend_chg": "Spend change", "h_sales_chg": "Sales change (estimate)",
  "m_raise": "Raise daily budgets: under goal - 3, capped",
  "m_lower": "Lower daily budgets: over goal + 5, not capped",
  "m_flag": "Flag: over goal + 5 and capped - budget unchanged, keyword-level bids in {skill} plan mode",
  "m_sb": "Keep the SB banner (awareness allowance)", "m_notplaced": "Not placed",
  "m_short": "Cut still needed (lowers do not reach the budget cut)",
  "m_toosmall": "Over goal but too small to act on at campaign level",
  "capped_line": "Capped = {rule}. Not checked (no budget usage): {nc} campaign(s), {ncs} spend in {days:g} days. AI managed (not in the change list): {ai}.",
  "size_gate": "A budget move needs at least {v} of spend in the window (the smaller of the absolute floor and {share:g}% of total ad spend).",
  "no_moves": "**No campaign budget move is possible, and that is the finding.** Of {total} campaigns carrying {spend}, {ai} sit in AI managed groups with AI on ({ais}) and are excluded because a campaign budget edit there is overridden when the group rescales; {nc} returned no budget usage ({ncs}). {rest} campaigns remain. Take the budget question to the managed groups (sparkx-edit-ai-group), not to the campaigns.",
  "h_raise10": "Raise daily budgets (top 10)", "h_lower10": "Lower daily budgets (top 10)",
  "h_toosmall": "Over goal but no campaign-level move (top 10)",
  "t_camp": "Campaign", "t_type": "Type", "t_acos": "ACOS {days:g}d", "t_capped_h": "Capped h/day", "t_budget": "Daily budget",
  "t_extra_sales": "Extra sales/wk", "t_hold": "Hold", "t_spend": "Spend {days:g}d", "t_why": "Why no move",
  "flags_line": "**Flags (budget unchanged):** ",
  "ai_line": "**AI managed - adjust the group, not the campaign ({skill}; a group budget change rescales all its campaigns):** ",
  "group": "group",
  "full_list": "Full list: change_list.csv - only ready = yes rows go to {skill}, after you confirm. Extra sales = extra spend x the campaign's ROAS x 0.8: the next clicks cost more than the average ones.",
  "scorecard": "Scorecard (top {n} categories = {pct:.0f}% of ad spend with a category)", "scorecard_h": "Scorecard",
  "c_cat": "Category", "c_spend_acos": "Ad spend {days:g}d - ACOS", "c_spend": "Ad spend {days:g}d", "c_conv": "Shoppers buy vs market",
  "c_peer": "Ads vs peers (median)", "c_play": "Play", "c_when": "When", "c_next": "Next",
  "lg_conv": "**Shoppers buy vs market**: your purchases per click / the market's, on generic searches. 1.00x = same as the market.",
  "lg_peer": "**Ads vs peers**: your brand's figure vs the median of similar brands in the same browse category, by goal (conversion = ROAS, consideration = cost per click, awareness = CPM). Top 25% = better than three in four peers.",
  "lg_play": "**Play**: Scale = more budget where campaigns are capped under goal; Fix ad cost = keyword-level bids and targeting first; Fix listing = the page loses buyers; Fix first = page, price or product before more spend; Hold (stock) = refill first; Keep = no raise while the category is above your ACOS goal.",
  "actions": "Actions", "a_num": "#", "a_owner": "Owner", "a_action": "Action", "a_cats": "Categories", "a_size": "Size",
  "a_when": "When", "a_check": "How we check", "a_stop": "Stop if",
  "goals": "Fair peer goals (P25 - P75 of similar brands)", "g_adtype": "Ad type - goal", "g_fair": "Fair range",
  "g_you": "You", "g_pos": "Position", "g_level": "Level, period", "g_none": "no usable peer rows in this pull",
  "sp_none": "Sponsored Products: no usable peer rows in this pull; SP goals stay at each category's own {days:g}-day ACOS.",
  "peer_unused": "{n} peer rows not used: ", "fixdata": "Fix the data first", "notes": "Notes",
  "scored": "Scored {pct:.0f}% of ad spend; {n} small categories listed only; {v} spend on products without a category.",
  "not_checked": "Not checked: ", "where_sits": "Where each category sits",
  "bubble": "Bubble size = ad spend. Categories without usable market data or peer rows are in the table only.",
  "ax_x": "Shoppers buy from you vs the market (1.0 = same)",
  "ax_y": "Ads vs peers' median (1.0 = same, higher = better)",
  "no_market": "no market data", "not_measured": "not measured - main products missing from market data (see Fix the data)",
  "partial": " (partial)", "no_peer": "no peer row", "acos_vs_acct": " - ACOS {v:.2f}x account",
  "u_roas": "ROAS", "u_cpc": "cost per click", "u_cpm": "CPM", "median": "median",
  "wide": " - wide spread: use the range, not the median", "not_returned": "not returned",
  "tile_spend": "{days:g}-day ad spend in the top {n} categories",
  "tile_beat": "categories where your ads beat 3 in 4 peers",
  "tile_behind": "categories where shoppers buy from you < 0.80x the market",
  "tile_missing": "big categories missing from market search data",
  "tile_placed": "placed in {n} campaigns under goal (ready to confirm)",
  "tile_sales": "sales from those raises (estimate)",
  "tile_capped": "campaigns under goal that run out of budget",
  "tile_over": "campaigns above your goal + 5 points",
  "tile_ai_share": "of ad spend sits in AI managed groups - not movable at campaign level",
  "tile_toosmall": "campaigns over goal that no campaign budget move can fix",
  "of": "of", "none": "-",
  "pos": {"top quarter": "top 25%", "above median": "above median", "below median": "below median", "bottom quarter": "bottom 25%"},
  "play": {"Scale": "Scale", "Keep": "Keep", "Hold (stock)": "Hold (stock)", "Fix ad cost": "Fix ad cost",
           "Fix listing": "Fix listing", "Fix first": "Fix first", "No read": "No read"},
 },
 "zh": {
  "title": "类目记分卡",
  "pgoal": {"conversion": "转化", "consideration": "考虑", "awareness": "认知"},
  "nt_no_data_no_peer": "既无市场数据也无同行行",
  "nt_market_unavailable": "市场数据不可访问（{reason}）：按同行和 ACOS 判定",
  "nt_vendor_no_sqp": "Vendor 店或无 SQP：按同行和 ACOS 判定",
  "nt_ads_only": "仅依据广告数据（市场数据缺失或不可用）",
  "nt_market_only": "仅依据市场数据（无同行行）",
  "nt_coverage": "市场数据覆盖了 {pct}% 的花费",
  "nt_evidence_adtype": "证据仅来自 {ad}",
  "nt_acos_above_goal": "类目 ACOS {acos}% 高于你设的 {goal:g}% 目标：回到目标以下之前不加预算",
  "nt_close_to_market": "放量的同时要盯住页面（只是接近市场，并未领先）",
  "nt_low_stock": "主力商品可售 {days:g} 天",
  "nt_roas_bottom": "{ad} 的 ROAS {roas} 落在同行后 25%（中位数 {median}）：加预算之前先查清楚",
  "nx_none": "—", "nx_std_no_sqp": "sparkx-search-term-diagnosis（搜索词；无 SQP）",
  "nx_raises_in_csv": "加预算清单见 change_list.csv",
  "nx_sqp_plan": "sparkx-sqp-insight 计划模式：{goal}",
  "tm_none": "—", "tm_now_page": "立即（页面工作）", "tm_refill_now": "立即补货",
  "tm_from_date": "{date} 起", "tm_page_now_ads_from": "页面立即做；广告成本 {date} 起",
  "tm_plan_only_in_progress": "只出计划；大促进行中，交给 sparkx-promo-monitor",
  "tm_plan_only_before": "只出计划；{start} 之前交给 sparkx-promo-prep",
  "goal_Both (listing first)": "两者兼顾（先做 listing）", "goal_Grow": "增长", "goal_Improve efficiency": "提效", "do_first": "先做这三件事", "opportunity": "机会", "challenge": "挑战",
  "money": "钱该怎么走（预算 {mode}，ACOS 目标 {goal:g}%）",
  "plan_only": "**{name}（{start} 至 {end}）：只出计划。** {from_} 之前本 Skill 不降预算、不写入；大促预算归 {skill}。",
  "tacos": "**TACOS 检查：**（广告花费{dsp}）/ 店铺总销售额 = 当前 {now}%，执行可确认的动作后约 {after}%{goal}{nodsp}。",
  "tacos_goal": "（目标 {goal:g}%", "tacos_capped": "；每周增量上限 {v}）", "tacos_plain": "）",
  "tacos_dsp": " + DSP", "tacos_nodsp": " —— 未含 DSP",
  "tacos_missed": "**本计划达不到 TACOS 目标：**{after}% 对 {goal:g}%，差 {pts:g} 个点（只靠缩减只能到 {cuts}%）。剩下的要靠降 bid 或提升转化，不是靠加预算 —— 见 {skill}。",
  "rsn_lower": "ACOS {acos:.1f}% 高于目标 {goal:g} + 5，且未受预算限制（日均断 {hrs} 小时）：预算降到日均实花的 80%。",
  "rsn_noop_cut": "ACOS {acos:.1f}% 高于目标 {goal:g} + 5，但降预算是无效改动：日预算 {budget:g}，而下限是 {floor:g}，日均实花 {avg}。请改走关键词层降 bid（sparkx-sqp-insight 计划模式）或直接暂停该活动。",
  "rsn_under_gate": "ACOS {acos:.1f}% 高于目标 {goal:g} + 5，但 {days:g} 天只花了 {spend}，低于预算动作所需的 {gate}。请改走关键词层降 bid（sparkx-sqp-insight 计划模式）或直接暂停该活动。",
  "h_move": "动作", "h_camp_ready": "活动数（可执行）", "h_spend_chg": "花费变化", "h_sales_chg": "销售额变化（估算）",
  "m_raise": "加日预算：ACOS 低于目标 3 个点以上，且受预算限制",
  "m_lower": "降日预算：ACOS 高于目标 5 个点以上，且未受预算限制",
  "m_flag": "标记：高于目标 5 个点且受预算限制 —— 预算不动，关键词层 bid 交给 {skill} 计划模式",
  "m_sb": "保留 SB 横幅（认知预算额度）", "m_notplaced": "未投放出去的钱",
  "m_short": "仍需缩减（降预算不足以达到目标削减额）",
  "m_toosmall": "超出目标但活动层无法处理",
  "capped_line": "受预算限制 = {rule}。未核查（无预算使用数据）：{nc} 个活动，{days:g} 天花费 {ncs}。AI 托管（不进改动清单）：{ai} 个。",
  "size_gate": "预算动作要求窗口内花费至少 {v}（绝对下限与总广告花费 {share:g}% 两者取小）。",
  "no_moves": "**活动层没有任何预算动作可做，这本身就是结论。** {total} 个活动共花费 {spend}，其中 {ai} 个在 AI 已开启的托管组里（{ais}），按规则排除 —— 在那里改活动预算会被组重算覆盖；另有 {nc} 个没有返回预算使用数据（{ncs}）。剩下 {rest} 个活动。预算的事要去改托管组（sparkx-edit-ai-group），不是改活动。",
  "h_raise10": "加日预算（前 10）", "h_lower10": "降日预算（前 10）",
  "h_toosmall": "超出目标但活动层无动作可做（前 10）",
  "t_camp": "活动", "t_type": "类型", "t_acos": "{days:g} 天 ACOS", "t_capped_h": "日均断预算小时", "t_budget": "日预算",
  "t_extra_sales": "每周增量销售额", "t_hold": "暂缓原因", "t_spend": "{days:g} 天花费", "t_why": "为什么不动",
  "flags_line": "**标记（预算不动）：**",
  "ai_line": "**AI 托管 —— 改组，不要改活动（{skill}；改组预算会按比例重算组内所有活动）：**",
  "group": "组",
  "full_list": "完整清单见 change_list.csv —— 只有 ready = yes 的行才会在你确认后交给 {skill}。增量销售额 = 增量花费 × 该活动 ROAS × 0.8：后面买到的点击比平均点击贵。",
  "scorecard": "记分卡（前 {n} 个类目 = 有类目归属广告花费的 {pct:.0f}%）", "scorecard_h": "记分卡",
  "c_cat": "类目", "c_spend_acos": "{days:g} 天花费 · ACOS", "c_spend": "{days:g} 天花费", "c_conv": "买家转化 vs 市场",
  "c_peer": "广告 vs 同行（中位数）", "c_play": "打法", "c_when": "何时", "c_next": "下一步",
  "lg_conv": "**买家转化 vs 市场**：你的每次点击购买数 ÷ 市场的每次点击购买数，口径为泛词搜索。1.00 倍 = 与市场持平。",
  "lg_peer": "**广告 vs 同行**：你的品牌数值 vs 同一浏览类目下同类品牌的中位数，按投放目的（转化 = ROAS，考虑 = 单次点击成本，认知 = CPM）。前 25% = 好过四分之三的同行。",
  "lg_play": "**打法**：放量 = 给未超目标但受预算限制的活动加预算；降广告成本 = 先动关键词层的 bid 和定向；改 listing = 页面在丢买家；先修基本面 = 加钱之前先解决页面、价格或产品；库存暂缓 = 先补货；维持 = 类目 ACOS 高于目标时不加预算。",
  "actions": "行动项", "a_num": "#", "a_owner": "负责人", "a_action": "动作", "a_cats": "对象", "a_size": "量级",
  "a_when": "何时", "a_check": "怎么验证", "a_stop": "什么情况下停",
  "goals": "合理的同行目标（同类品牌的 P25 - P75）", "g_adtype": "广告类型 · 投放目的", "g_fair": "合理区间",
  "g_you": "你", "g_pos": "位置", "g_level": "类目层级、周期", "g_none": "本次取数没有可用的同行行",
  "sp_none": "Sponsored Products：本次取数没有可用的同行行；SP 的目标沿用各类目自身的 {days:g} 天 ACOS。",
  "peer_unused": "{n} 条同行行未使用：", "fixdata": "先修数据", "notes": "说明",
  "scored": "已评分的广告花费占比 {pct:.0f}%；{n} 个小类目仅列出；无类目归属的商品花费 {v}。",
  "not_checked": "未核查：", "where_sits": "各类目的位置",
  "bubble": "气泡大小 = 广告花费。没有可用市场数据或同行行的类目只出现在表格里。",
  "ax_x": "买家在你这里的转化 vs 市场（1.0 = 持平）",
  "ax_y": "广告 vs 同行中位数（1.0 = 持平，越高越好）",
  "no_market": "无市场数据", "not_measured": "无法测算 —— 主力商品不在市场数据里（见「先修数据」）",
  "partial": "（部分）", "no_peer": "无同行行", "acos_vs_acct": " —— ACOS 为账户的 {v:.2f} 倍",
  "u_roas": "ROAS", "u_cpc": "单次点击成本", "u_cpm": "CPM", "median": "中位数",
  "wide": " —— 区间很宽：看区间，不要只看中位数", "not_returned": "未返回",
  "tile_spend": "前 {n} 个类目的 {days:g} 天广告花费",
  "tile_beat": "个类目的广告好过四分之三同行",
  "tile_behind": "个类目的买家转化低于市场的 0.80 倍",
  "tile_missing": "个大类目缺市场搜索数据",
  "tile_placed": "投入到 {n} 个未超目标的活动（待确认）",
  "tile_sales": "这些加预算带来的销售额（估算）",
  "tile_capped": "个未超目标但受预算限制的活动",
  "tile_over": "个超出目标 5 个点以上的活动",
  "tile_ai_share": "的广告花费在 AI 托管组里 —— 活动层动不了",
  "tile_toosmall": "个超标活动无法用活动预算解决",
  "of": "/", "none": "—",
  "pos": {"top quarter": "前 25%", "above median": "高于中位数", "below median": "低于中位数", "bottom quarter": "后 25%"},
  "play": {"Scale": "放量", "Keep": "维持", "Hold (stock)": "库存暂缓", "Fix ad cost": "降广告成本",
           "Fix listing": "改 listing", "Fix first": "先修基本面", "No read": "无法判定"},
 },
 "ja": {
  "title": "カテゴリースコアカード",
  "pgoal": {"conversion": "コンバージョン", "consideration": "比較検討", "awareness": "認知"},
  "nt_no_data_no_peer": "市場データも同業データもありません",
  "nt_market_unavailable": "市場データにアクセスできません（{reason}）：同業とACOSで判定",
  "nt_vendor_no_sqp": "VendorまたはSQPなし：同業とACOSで判定",
  "nt_ads_only": "広告データのみに基づく判定（市場データが欠落または利用不可）",
  "nt_market_only": "市場データのみに基づく判定（同業データなし）",
  "nt_coverage": "市場データは費用の {pct}% をカバー",
  "nt_evidence_adtype": "根拠は {ad} のみ",
  "nt_acos_above_goal": "カテゴリーACOS {acos}% が目標 {goal:g}% を超過：目標以下に戻るまで増額しません",
  "nt_close_to_market": "拡大しつつ商品ページも確認（市場と同等であり、上回ってはいません）",
  "nt_low_stock": "主要商品の在庫は {days:g} 日分",
  "nt_roas_bottom": "{ad} のROAS {roas} は同業の下位25%（中央値 {median}）：増額前に要確認",
  "nx_none": "—", "nx_std_no_sqp": "sparkx-search-term-diagnosis（検索クエリ、SQPなし）",
  "nx_raises_in_csv": "増額リストは change_list.csv",
  "nx_sqp_plan": "sparkx-sqp-insight プランモード：{goal}",
  "tm_none": "—", "tm_now_page": "すぐに（商品ページ対応）", "tm_refill_now": "すぐに補充",
  "tm_from_date": "{date} から", "tm_page_now_ads_from": "商品ページはすぐに、広告コストは {date} から",
  "tm_plan_only_in_progress": "計画のみ。セール期間中は sparkx-promo-monitor へ",
  "tm_plan_only_before": "計画のみ。{start} までは sparkx-promo-prep へ",
  "goal_Both (listing first)": "両立（商品ページを優先）", "goal_Grow": "拡大", "goal_Improve efficiency": "効率改善", "do_first": "まず着手する3件", "opportunity": "機会", "challenge": "課題",
  "money": "予算の配分先（予算 {mode}、ACOS目標 {goal:g}%）",
  "plan_only": "**{name}（{start}～{end}）：計画のみ。** {from_} まで本Skillは予算の引き下げも書き込みも行いません。セール期間の予算は {skill} が担当します。",
  "tacos": "**TACOSチェック：**（広告費{dsp}）/ ストア総売上 = 現在 {now}%、実行可能な変更後は約 {after}%{goal}{nodsp}。",
  "tacos_goal": "（目標 {goal:g}%", "tacos_capped": "、週あたり増額上限 {v}）", "tacos_plain": "）",
  "tacos_dsp": " + DSP", "tacos_nodsp": " ※DSPは含みません",
  "tacos_missed": "**本計画はTACOS目標に届きません：**{after}% に対し {goal:g}%、{pts:g}ポイント不足（削減のみでは {cuts}%）。残りは入札の引き下げか転換率の改善が必要で、増額では解決しません（{skill} を参照）。",
  "rsn_lower": "ACOS {acos:.1f}% が目標 {goal:g}+5 を超過し、予算上限には未到達（1日あたり {hrs} 時間）：予算を平均日次消化額の80%に設定。",
  "rsn_noop_cut": "ACOS {acos:.1f}% が目標 {goal:g}+5 を超過。ただし減額は無意味です：日予算 {budget:g} に対し下限は {floor:g}、平均日次消化額は {avg}。キーワード単位で入札を下げる（sparkx-sqp-insight プランモード）か、キャンペーンを停止してください。",
  "rsn_under_gate": "ACOS {acos:.1f}% が目標 {goal:g}+5 を超過。ただし {days:g} 日間の消化は {spend} のみで、予算変更に必要な {gate} を下回ります。キーワード単位で入札を下げる（sparkx-sqp-insight プランモード）か、キャンペーンを停止してください。",
  "h_move": "アクション", "h_camp_ready": "キャンペーン数（実行可）", "h_spend_chg": "費用の変化", "h_sales_chg": "売上の変化（推定）",
  "m_raise": "日予算の増額：目標−3%以下かつ予算上限に到達",
  "m_lower": "日予算の減額：目標+5%超かつ予算上限に未到達",
  "m_flag": "要注意：目標+5%超かつ予算上限に到達 —— 予算は変更せず、キーワード単位の入札は {skill} のプランモードへ",
  "m_sb": "SBバナーを維持（認知枠）", "m_notplaced": "配分されなかった額",
  "m_short": "削減がなお不足（減額だけでは目標削減額に届かない）",
  "m_toosmall": "目標超過だがキャンペーン単位では対処不可",
  "capped_line": "予算上限到達 = {rule}。未確認（予算消化データなし）：{nc}件、{days:g}日間の費用 {ncs}。AI管理（変更リスト対象外）：{ai}件。",
  "size_gate": "予算の変更には期間内で最低 {v} の費用が必要です（絶対下限と総広告費の {share:g}% のうち小さい方）。",
  "no_moves": "**キャンペーン単位で可能な予算変更はありません。これ自体が結論です。** {total}件のキャンペーンが {spend} を消化し、うち {ai} 件はAIが有効な管理グループ内（{ais}）のため除外されます（グループ側の再配分で上書きされるため）。さらに {nc} 件は予算消化データが返りませんでした（{ncs}）。残りは {rest} 件です。予算は管理グループ側（sparkx-edit-ai-group）で調整してください。",
  "h_raise10": "日予算の増額（上位10件）", "h_lower10": "日予算の減額（上位10件）",
  "h_toosmall": "目標超過だがキャンペーン単位で対処不可（上位10件）",
  "t_camp": "キャンペーン", "t_type": "種別", "t_acos": "{days:g}日 ACOS", "t_capped_h": "1日あたり予算切れ時間", "t_budget": "日予算",
  "t_extra_sales": "増加売上/週", "t_hold": "保留理由", "t_spend": "{days:g}日 費用", "t_why": "変更しない理由",
  "flags_line": "**要注意（予算は変更なし）：**",
  "ai_line": "**AI管理 —— キャンペーンではなくグループを調整（{skill}；グループ予算の変更は配下の全キャンペーンに再配分されます）：**",
  "group": "グループ",
  "full_list": "全件は change_list.csv を参照。ready = yes の行のみ、確認後に {skill} へ渡されます。増加売上 = 増加費用 × 当該キャンペーンのROAS × 0.8（追加のクリックは平均より割高なため）。",
  "scorecard": "スコアカード（上位 {n} カテゴリー = カテゴリー判明分の広告費の {pct:.0f}%）", "scorecard_h": "スコアカード",
  "c_cat": "カテゴリー", "c_spend_acos": "{days:g}日 費用・ACOS", "c_spend": "{days:g}日 費用", "c_conv": "購入転換 vs 市場",
  "c_peer": "広告 vs 同業（中央値）", "c_play": "方針", "c_when": "時期", "c_next": "次のステップ",
  "lg_conv": "**購入転換 vs 市場**：自社のクリックあたり購入数 ÷ 市場のクリックあたり購入数（一般キーワード）。1.00倍 = 市場と同等。",
  "lg_peer": "**広告 vs 同業**：同一ブラウズカテゴリーの同種ブランドの中央値との比較（目的別：転換 = ROAS、比較検討 = クリック単価、認知 = CPM）。上位25% = 同業の4社中3社より良い。",
  "lg_play": "**方針**：拡大 = 目標未満かつ予算上限に達したキャンペーンに増額／広告コスト改善 = まずキーワード単位の入札とターゲティング／商品ページ改善 = ページで購入者を失っている／基礎課題の優先対応 = 増額の前にページ・価格・商品／在庫保留 = まず補充／維持 = カテゴリーACOSが目標超過の間は増額しない。",
  "actions": "アクション", "a_num": "#", "a_owner": "担当", "a_action": "アクション", "a_cats": "対象", "a_size": "規模",
  "a_when": "時期", "a_check": "確認方法", "a_stop": "中止条件",
  "goals": "同業に基づく妥当な目標（同種ブランドの P25 - P75）", "g_adtype": "広告タイプ・目的", "g_fair": "妥当なレンジ",
  "g_you": "自社", "g_pos": "位置", "g_level": "階層・期間", "g_none": "今回の取得に利用可能な同業データがありません",
  "sp_none": "Sponsored Products：今回の取得に利用可能な同業データがないため、SPの目標は各カテゴリー自身の{days:g}日ACOSを用います。",
  "peer_unused": "{n} 件の同業データは未使用：", "fixdata": "先にデータを修正", "notes": "注記",
  "scored": "広告費の {pct:.0f}% を評価。小規模カテゴリー {n} 件は掲載のみ。カテゴリー不明の商品の費用 {v}。",
  "not_checked": "未確認：", "where_sits": "各カテゴリーの位置",
  "bubble": "バブルの大きさ = 広告費。市場データまたは同業データが利用できないカテゴリーは表のみに掲載。",
  "ax_x": "自社の購入転換 vs 市場（1.0 = 同等）",
  "ax_y": "広告 vs 同業中央値（1.0 = 同等、高いほど良い）",
  "no_market": "市場データなし", "not_measured": "測定不可 —— 主要商品が市場データに含まれません（「先にデータを修正」参照）",
  "partial": "（一部）", "no_peer": "同業データなし", "acos_vs_acct": " —— ACOSはアカウントの {v:.2f} 倍",
  "u_roas": "ROAS", "u_cpc": "クリック単価", "u_cpm": "CPM", "median": "中央値",
  "wide": " —— ばらつきが大きいため中央値ではなくレンジで判断", "not_returned": "未返却",
  "tile_spend": "上位 {n} カテゴリーの{days:g}日広告費",
  "tile_beat": "カテゴリーで広告が同業の4社中3社を上回る",
  "tile_behind": "カテゴリーで購入転換が市場の0.80倍未満",
  "tile_missing": "件の主要カテゴリーで市場検索データが欠落",
  "tile_placed": "目標未満の {n} 件のキャンペーンに配分（要確認）",
  "tile_sales": "増額による売上（推定）",
  "tile_capped": "件が目標未満かつ予算切れ",
  "tile_over": "件が目標+5ポイント超",
  "tile_ai_share": "の広告費がAI管理グループ内 —— キャンペーン単位では動かせません",
  "tile_toosmall": "件の目標超過キャンペーンは予算変更では解決不可",
  "of": "/", "none": "—",
  "pos": {"top quarter": "上位25%", "above median": "中央値超", "below median": "中央値未満", "bottom quarter": "下位25%"},
  "play": {"Scale": "拡大", "Keep": "維持", "Hold (stock)": "在庫保留", "Fix ad cost": "広告コスト改善",
           "Fix listing": "商品ページ改善", "Fix first": "基礎課題の優先対応", "No read": "判定不可"},
 },
}
T = L["en"]
WD = 14.0          # budgetUsage window, for the capped rule
SD = 14.0          # spend window behind the ACOS / spend columns - a different window
SKILL_SQP = "sparkx-sqp-insight"
SKILL_EDIT = "sparkx-edit-ads"
SKILL_GROUP = "sparkx-edit-ai-group"


def cell(v):
    """Markdown table cell: campaign names routinely contain '|', which would split the row."""
    return str(v).replace("|", "\\|")


def reason_txt(r):
    """Localise a row's reason from its code; fall back to the English string the script stored."""
    code, ar = r.get("reason_code"), r.get("reason_args") or {}
    key = "rsn_" + code if code else None
    if key and key in T:
        try:
            return T[key].format(**{k: ("-" if v is None else v) for k, v in ar.items()})
        except (KeyError, ValueError):
            pass
    return r.get("reason", "-")


CUR = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "JPY": "\u00a5", "CAD": "CA$",
       "AUD": "A$", "MXN": "MX$", "BRL": "R$", "SEK": "SEK ", "PLN": "PLN ", "TRY": "\u20ba",
       "AED": "AED ", "SAR": "SAR ", "INR": "\u20b9", "SGD": "S$"}
SYM = "$"          # set from the data in main(); a single-profile pull is in local currency


def money(v):
    v = v or 0
    return f"{SYM}{v / 1000:.1f}K" if abs(v) >= 1000 else f"{SYM}{v:.0f}"


def coded(c, prefix, default="-"):
    """Phrase a {code, args} object in the report language; fall back to the English string."""
    if not c:
        return default
    key = prefix + c.get("code", "")
    s = T.get(key)
    if s is None:
        return default
    args = {k: v for k, v in c.items() if k != "code"}
    if "goal" in args and prefix == "nx_":
        args["goal"] = T.get("goal_" + str(args["goal"]), args["goal"])
    try:
        return s.format(**args)
    except (KeyError, ValueError, IndexError):
        return s


def notes_txt(card):
    cs = card.get("play_note_codes")
    if cs:
        out = [coded(c, "nt_", "") for c in cs]
        out = [x for x in out if x]
        if out:
            return "; ".join(out)
    return card.get("play_note") or ""


def timing_txt(card):
    return coded(card.get("timing_code"), "tm_", card.get("timing") or "-")


def next_txt(card):
    return coded(card.get("next_code"), "nx_", card.get("next") or "-")


def conv_txt(c):
    v, cov = c.get("converts_vs_market"), c.get("market_data_coverage")
    if v is None:
        return T["no_market"] + (f" ({c['converts_note']})" if c.get("converts_note") else "")
    if cov is not None and cov < 0.4:
        return T["not_measured"]
    return f"{v:.2f}x" + (T["partial"] if cov is not None and cov < 0.6 else "")


def peer_txt(c):
    ad = c.get("play_ad_type")
    if not ad:
        base = c.get("peer_note") or T["no_peer"]
        return base + (T["acos_vs_acct"].format(v=c["acos_vs_account"]) if c.get("acos_vs_account") is not None else "")
    pr = c["peer_rows"][ad]
    unit = {"roas": T["u_roas"], "cpc": T["u_cpc"], "cpm": T["u_cpm"]}[pr["metric"]]
    goal = T["pgoal"].get(pr["goal"], pr["goal"])
    return (f"{ad} {goal} - {unit} {pr['own']:.2f} vs {T['median']} {pr['p50']:.2f} ({T['pos'][pr['position']]})"
            f" - {pr['level_name']}" + (f", {pr['period']}" if pr.get("period") else ""))


def play_txt(c):
    p = T["play"].get(c["play"], c["play"])
    if c.get("scale_scope"):
        p += " (" + c["scale_scope"].replace("Sponsored Brands", "SB").replace("Sponsored Display", "SD") + ")"
    return p


def rng(v, fmt="{:.2f}"):
    lo, hi = v or (None, None)
    if lo is None or hi is None:
        return T["not_returned"]
    return fmt.format(lo) + " - " + fmt.format(hi)


def goals_rows(cs):
    out = []
    for c in cs:
        for pr in c.get("peer_goals", []):
            gs = pr["goal_set"]
            if pr["goal"] == "conversion":
                fair = f"{T['u_roas']} {rng(gs['roas_range'])} (ACOS {rng(gs['acos_range'], '{:.1f}%')})"
                you = f"{T['u_roas']} {pr['own']:.2f}" + (f" (ACOS {gs['own_acos']:.1f}%)" if gs.get("own_acos") else "")
            else:
                m = pr["metric"]
                fair = f"{m.upper()} {rng(gs[m + '_range'])}"
                you = f"{m.upper()} {pr['own']:.2f}"
            fair += T["wide"] if gs.get("wide_spread") else f" - {T['median']} {pr['p50']:.2f}"
            out.append((c["category"], f"{pr['ad']} - {T['pgoal'].get(pr['goal'], pr['goal'])}", fair, you,
                        T["pos"].get(pr["position"], "-"),
                        pr["level_name"] + (f", {pr['period']}" if pr.get("period") else "")))
    return out


def no_moves(p):
    """C1: the plan is empty. Say why, with the exclusion chain, instead of showing four bare zeros."""
    return (p.get("raise_campaigns", 0) + p.get("lower_campaigns", 0) + p.get("flag_campaigns", 0)) == 0


def money_plan_md(br):
    p = br["plan"]; md = []
    md.append(T["money"].format(mode=p["budget_mode"], goal=p["acos_goal"]))
    md[-1] = f"## {md[-1]}{NL}"
    ev = p.get("event") or {}
    if ev.get("plan_only"):
        md.append(T["plan_only"].format(name=ev["name"], start=ev["start"], end=ev["end"], from_=ev["moves_from"],
                                        skill="sparkx-promo-monitor" if ev["in_progress"] else "sparkx-promo-prep") + NL)
    if p.get("tacos"):
        t = p["tacos"]
        goal = ""
        if t.get("goal"):
            goal = T["tacos_goal"].format(goal=t["goal"]) + (T["tacos_capped"].format(v=money(t["capped_extra_per_week"]))
                                                             if t.get("capped_extra_per_week") is not None else T["tacos_plain"])
        md.append(T["tacos"].format(dsp=T["tacos_dsp"] if t.get("dsp_included") else "", now=t["now"], after=t["after"],
                                    goal=goal, nodsp="" if t.get("dsp_included") else T["tacos_nodsp"]) + NL)
        if t.get("goal_missed"):
            md.append(T["tacos_missed"].format(after=t["after"], goal=t["goal"], pts=t["shortfall_pts"],
                                               cuts=t["after_cuts_only"], skill=SKILL_SQP) + NL)
    if no_moves(p):
        md.append(T["no_moves"].format(
            total=p.get("total_campaigns", "-"), spend=money(p.get("total_spend_window") or 0),
            ai=p["ai_managed_campaigns"], ais=money(p.get("ai_managed_spend") or 0),
            nc=p["not_checked_campaigns"], ncs=money(p["not_checked_spend_14d"]),
            rest=p.get("candidate_campaigns", "-")) + NL)
    md.append(f"| {T['h_move']} | {T['h_camp_ready']} | {T['h_spend_chg']} | {T['h_sales_chg']} |")
    md.append("|---|---|---|---|")
    md.append(f"| {T['m_raise']} | {p['raise_campaigns']} ({p['raise_ready']}) | "
              f"+{money(p['raise_extra_per_week'])}/wk | +{money(p['raise_sales_per_week'])}/wk |")
    md.append(f"| {T['m_lower']} | {p['lower_campaigns']} ({p['lower_ready']}) | "
              f"-{money(p['savings_per_week'])}/wk | -{money(p['lower_sales_at_risk_per_week'])}/wk |")
    md.append(f"| {T['m_flag'].format(skill=SKILL_SQP)} | {p['flag_campaigns']} | - | - |")
    if p.get("too_small_campaigns"):
        md.append(f"| {T['m_toosmall']} | {p['too_small_campaigns']} | {money(p.get('too_small_spend') or 0)} | - |")
    if p.get("sb_kept_banner"):
        md.append(f"| {T['m_sb']} | {p['sb_kept_banner']} | - | - |")
    md.append(f"| {T['m_notplaced']} | - | {money(p['not_placed_per_week'])}/wk | - |")
    if p.get("cut_shortfall_per_week"):
        md.append(f"| {T['m_short']} | - | {money(p['cut_shortfall_per_week'])}/wk | - |")
    md.append("")
    md.append(T["capped_line"].format(rule=p["capped_rule"], nc=p["not_checked_campaigns"],
                                      ncs=money(p["not_checked_spend_14d"]), days=WD, ai=p["ai_managed_campaigns"]) + NL)
    if p.get("min_lower_used") is not None:
        md.append(T["size_gate"].format(v=money(p["min_lower_used"]), share=(p.get("min_lower_share") or 0.01) * 100) + NL)
    md.append(f"### {T['h_raise10']}{NL}")
    md.append(f"| {T['t_camp']} | {T['t_type']} | {T['t_acos'].format(days=SD)} | {T['t_capped_h']} | {T['t_budget']} | {T['t_extra_sales']} | {T['t_hold']} |")
    md.append("|---|---|---|---|---|---|---|")
    for r in br["raises"][:10]:
        md.append(f"| {cell(r['campaign'][:58])} | {r['type']} | {r['acos']}% | {r['out_of_budget_hours_per_day']} | "
                  f"{r['daily_budget']:g} -> {r['new_daily_budget']:g} | +{money(r['sales_per_week'])} | {cell('; '.join(r['hold']) or '-')} |")
    md.append(f"{NL}### {T['h_lower10']}{NL}")
    md.append(f"| {T['t_camp']} | {T['t_type']} | {T['t_acos'].format(days=SD)} | {T['t_spend'].format(days=SD)} | {T['t_budget']} | {T['t_hold']} |")
    md.append("|---|---|---|---|---|---|")
    for r in br["lowers"][:10]:
        md.append(f"| {cell(r['campaign'][:58])} | {r['type']} | {r['acos']}% | {money(r['spend_14d'])} | "
                  f"{r['daily_budget']:g} -> {r['new_daily_budget']:g} | {cell('; '.join(r['hold']) or '-')} |")
    if br.get("too_small"):
        md.append(f"{NL}### {T['h_toosmall']}{NL}")
        md.append(f"| {T['t_camp']} | {T['t_type']} | {T['t_acos'].format(days=SD)} | {T['t_spend'].format(days=SD)} | {T['t_budget']} | {T['t_why']} |")
        md.append("|---|---|---|---|---|---|")
        for r in br["too_small"][:10]:
            md.append(f"| {cell(r['campaign'][:58])} | {r['type']} | "
                      f"{str(r['acos']) + '%' if r['acos'] is not None else T['none']} | "
                      f"{money(r['spend_14d'])} | {r['daily_budget'] if r['daily_budget'] is not None else T['none']} | "
                      f"{cell(reason_txt(r))} |")
    if br.get("flags"):
        md.append(NL + T["flags_line"] + "; ".join(f"{cell(r['campaign'][:45])} (ACOS {r['acos']}%)" for r in br["flags"][:10]))
    if br.get("ai_managed"):
        md.append(NL + T["ai_line"].format(skill=SKILL_GROUP)
                  + "; ".join(f"{cell(r['campaign'][:45])} ({T['group']} {cell(r.get('aiGroupName') or r.get('aiGroupId'))})"
                              for r in br["ai_managed"][:10]))
    md.append(NL + T["full_list"].format(skill=SKILL_EDIT) + NL)
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
                cls = " class=callout" if t.startswith("**") and "no_moves" not in t else ""
                out.append(f"<p{cls}>" + e(t.replace("**", "")) + "</p>")
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
    W, H, Lf, B = 640, 360, 56, 40
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
    fx = lambda v: Lf + (v - 0.3) / 1.0 * (W - Lf - 16)
    fy = lambda v: H - B - (v - 0.3) / 2.7 * (H - B - 16)
    mx = max(c["ad_spend_14d"] for c, _, _ in pts) or 1
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{html.escape(T["where_sits"])}">',
           f'<rect x="{fx(0.8)}" y="{fy(3.0)}" width="{fx(1.3) - fx(0.8)}" height="{fy(1.0) - fy(3.0)}" fill="#eef3ff"/>',
           f'<line x1="{fx(0.8)}" y1="{fy(0.3)}" x2="{fx(0.8)}" y2="{fy(3.0)}" stroke="#c9ced6" stroke-dasharray="4 4"/>',
           f'<line x1="{fx(0.3)}" y1="{fy(1.0)}" x2="{fx(1.3)}" y2="{fy(1.0)}" stroke="#c9ced6" stroke-dasharray="4 4"/>',
           f'<text x="{fx(1.28)}" y="{fy(2.9)}" text-anchor="end" class="q">{html.escape(T["play"]["Scale"])}</text>',
           f'<text x="{fx(0.32)}" y="{fy(2.9)}" class="q">{html.escape(T["play"]["Fix listing"])}</text>',
           f'<text x="{fx(1.28)}" y="{fy(0.38)}" text-anchor="end" class="q">{html.escape(T["play"]["Fix ad cost"])}</text>',
           f'<text x="{fx(0.32)}" y="{fy(0.38)}" class="q">{html.escape(T["play"]["Fix first"])}</text>',
           f'<text x="{(Lf + W) / 2}" y="{H - 6}" text-anchor="middle" class="ax">{html.escape(T["ax_x"])}</text>',
           f'<text x="14" y="{(H - B) / 2}" transform="rotate(-90 14 {(H - B) / 2})" text-anchor="middle" class="ax">{html.escape(T["ax_y"])}</text>']
    for c, x, y in pts:
        r = 6 + 14 * (c["ad_spend_14d"] / mx) ** 0.5
        out.append(f'<circle cx="{fx(x):.0f}" cy="{fy(y):.0f}" r="{r:.0f}" fill="{PLAY_COLOR.get(c["play"], "#1f5eff")}" fill-opacity="0.75"/>')
        out.append(f'<text x="{fx(x) + r + 3:.0f}" y="{fy(y) + 4:.0f}" class="lb">{html.escape(c["category"])}</text>')
    out.append("</svg>")
    return "".join(out)


def build_tiles(d, cs, br):
    """C1: with a real budget plan the tiles carry it; with an empty plan they carry the diagnosis instead,
    so four zeros never stand alone on the page."""
    ps = d["peer_summary"]
    diag = [(money(sum(c["ad_spend_14d"] for c in cs)), T["tile_spend"].format(days=SD, n=len(cs))),
            (f"{ps['top quarter']} {T['of']} {ps['categories_with_peer_row']}", T["tile_beat"]),
            (f"{d['converts_summary']['behind']} {T['of']} {sum(d['converts_summary'].values())}", T["tile_behind"]),
            (str(len(d.get("data_fixes", []))), T["tile_missing"])]
    if not br:
        return diag
    P = br["plan"]
    if no_moves(P):
        ai_share = None
        if P.get("ai_managed_spend") and P.get("total_spend_window"):
            ai_share = P["ai_managed_spend"] / P["total_spend_window"]
        tiles = [diag[0], diag[2]]
        tiles.append((f"{ai_share * 100:.0f}%" if ai_share is not None else str(P["ai_managed_campaigns"]),
                      T["tile_ai_share"]))
        tiles.append((str(P.get("too_small_campaigns", 0)), T["tile_toosmall"]))
        return tiles
    return [(f"+{money(P['fits_extra_per_week'])}/wk", T["tile_placed"].format(n=P["raise_ready"])),
            (f"+{money(P['raise_sales_per_week'])}/wk", T["tile_sales"]),
            (f"{P['raise_campaigns']}", T["tile_capped"]),
            (f"{P['lower_campaigns'] + P['flag_campaigns']}", T["tile_over"])]


def main(argv=None):
    global T, WD, SD, SYM
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--summary")
    ap.add_argument("--top", type=int, default=15); ap.add_argument("--store", default=""); ap.add_argument("--period", default="")
    ap.add_argument("--budget-room"); ap.add_argument("--out", default=".")
    ap.add_argument("--currency", help="ISO code for amounts (default: taken from the peer rows; "
                                       "a single-profile pull is in the store's local currency)")
    ap.add_argument("--lang", default="en", choices=sorted(L),
                    help="language of everything the script writes; must match summary.json (default en)")
    a = ap.parse_args(argv)
    T = L[a.lang]

    def rd(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    br = rd(a.budget_room) if a.budget_room else None
    if br:
        WD = br["plan"].get("window_days") or 14.0
        SD = br["plan"].get("spend_days") or 14.0
    d = rd(a.inp); cs = d["categories"][: a.top]
    # Currency: a single-profile pull is in the store's local currency and the peer rows carry the
    # code. Never print "$" for a EUR store (platform-notes.md, Currency Rules).
    global SYM
    _cur = a.currency or next((pr.get("currency") for c in cs for pr in (c.get("peer_rows") or {}).values()
                               if pr.get("currency")), None)
    SYM = CUR.get((_cur or "").upper(), (_cur + " ") if _cur else "$")
    s = rd(a.summary) if a.summary else {}
    errs = check_summary(s) if s else []
    for x in errs:
        print("CHECK:", x)

    # ---------- markdown ----------
    md = [f"# {T['title']} · {a.store}{NL}{NL}{a.period}{NL}"]
    if s:
        md.append(f"**{s['headline']}**{NL}")
        md.append(f"## {T['do_first']}{NL}")
        for i, x in enumerate(s["do_first"], 1):
            md.append(f"{i}. **{x['owner']}** · {x['action']} - {x['why']}")
        md.append(f"{NL}**{T['opportunity']}:** {s['opportunity']}{NL}{NL}**{T['challenge']}:** {s['challenge']}{NL}")
    if br:
        md += money_plan_md(br)
    md.append(f"## {T['scorecard'].format(n=len(cs), pct=sum(c['share_of_ad_spend'] for c in cs) * 100)}{NL}")
    md.append(f"| {T['c_cat']} | {T['c_spend_acos'].format(days=SD)} | {T['c_conv']} | {T['c_peer']} | {T['c_play']} | {T['c_when']} | {T['c_next']} |")
    md.append("|---|---|---|---|---|---|---|")
    for c in cs:
        _n = notes_txt(c)
        md.append(f"| {cell(c['category'])} | {money(c['ad_spend_14d'])} · {c['acos_14d']}% | {cell(conv_txt(c))} | {cell(peer_txt(c))} | **{cell(play_txt(c))}**"
                  + (f"<br>{cell(_n)}" if _n else "") + f" | {cell(timing_txt(c))} | {cell(next_txt(c))} |")
    md.append(NL + "- " + T["lg_conv"])
    md.append("- " + T["lg_peer"])
    md.append("- " + T["lg_play"] + NL)
    if s.get("actions"):
        md.append(f"## {T['actions']}{NL}")
        md.append(f"| {T['a_num']} | {T['a_owner']} | {T['a_action']} | {T['a_cats']} | {T['a_size']} | {T['a_when']} | {T['a_check']} | {T['a_stop']} |")
        md.append("|---|---|---|---|---|---|---|---|")
        for i, x in enumerate(s["actions"], 1):
            md.append(f"| {i} | {x['owner']} | {x['action']} | {x['objects']} | {x['size']} | {x['when']} | {x['check']} | {x.get('stop', '-')} |")
        md.append("")
    gr = goals_rows(cs)
    md.append(f"## {T['goals']}{NL}")
    md.append(f"| {T['c_cat']} | {T['g_adtype']} | {T['g_fair']} | {T['g_you']} | {T['g_pos']} | {T['g_level']} |")
    md.append("|---|---|---|---|---|---|")
    for r in gr:
        md.append("| " + " | ".join(cell(x) for x in r) + " |")
    if not gr:
        md.append(f"| - | - | {T['g_none']} | - | - | - |")
    if not d.get("sp_peer_rows"):
        md.append(NL + T["sp_none"].format(days=SD))
    if d.get("unusable_peer_rows"):
        md.append(NL + T["peer_unused"].format(n=len(d["unusable_peer_rows"]))
                  + "; ".join(sorted({u["reason"] for u in d["unusable_peer_rows"]})) + ".")
    if d.get("data_fixes"):
        md.append(f"{NL}## {T['fixdata']}{NL}")
        for f in d["data_fixes"]:
            md.append(f"- {f['category']} ({money(f['ad_spend_14d'])}): {f['fix']}")
    md.append(f"{NL}## {T['notes']}{NL}")
    for n in d["notes"] + d.get("market_notes", []):
        md.append(f"- {n}")
    md.append("- " + T["scored"].format(pct=d["scored_share_of_ad_spend"] * 100, n=d["not_scored_small_count"],
                                        v=money(d["unmapped_ad_spend"])))
    if s.get("not_checked"):
        md.append("- " + T["not_checked"] + s["not_checked"])
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "report.md"), "w", encoding="utf-8") as f:
        f.write(NL.join(md) + NL)

    # ---------- html ----------
    e = html.escape
    rows = "".join(
        f"<tr><td><b>{e(c['category'])}</b></td><td>{money(c['ad_spend_14d'])}<br><span class=m>ACOS {c['acos_14d']}%</span></td>"
        f"<td>{e(conv_txt(c))}</td><td>{e(peer_txt(c))}</td>"
        f"<td><span class=pill style='background:{PLAY_COLOR.get(c['play'], '#6b7280')}'>{e(play_txt(c))}</span>"
        + (f"<div class=m>{e(notes_txt(c))}</div>" if notes_txt(c) else "")
        + f"</td><td>{e(timing_txt(c))}</td><td class=m>{e(next_txt(c))}</td></tr>" for c in cs)
    acts = "".join(f"<tr><td>{i}</td><td>{e(x['owner'])}</td><td>{e(x['action'])}<div class=m>{e(x['objects'])}</div></td><td>{e(x['size'])}</td>"
                   f"<td>{e(x['when'])}</td><td>{e(x['check'])}</td><td>{e(x.get('stop', '-'))}</td></tr>"
                   for i, x in enumerate(s.get("actions", []), 1))
    goals_html = ("".join("<tr>" + "".join(f"<td>{e(v)}</td>" for v in r) + "</tr>" for r in gr)
                  or f"<tr><td colspan=6>{e(T['g_none'])}</td></tr>")
    tiles = build_tiles(d, cs, br)
    fixes = ""
    if d.get("data_fixes"):
        fixes = (f"<h2>{e(T['fixdata'])}</h2><ul class=legend>"
                 + "".join(f"<li>{e(f['category'])} ({money(f['ad_spend_14d'])}): {e(f['fix'])}</li>" for f in d["data_fixes"]) + "</ul>")
    page = f"""<!DOCTYPE html><html lang="{a.lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(T['title'])} · {e(a.store)}</title><style>
body{{font:15px/1.6 -apple-system,"Segoe UI","PingFang SC","Hiragino Sans","Microsoft YaHei",Roboto,sans-serif;color:#111827;background:#fff;margin:0}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px}} h1{{font-size:22px;margin:0}} h2{{font-size:17px;margin:28px 0 10px}} h3{{font-size:15px;margin:18px 0 8px}}
.sub{{color:#6b7280;font-size:13px}} .head{{font-size:20px;font-weight:650;margin:18px 0;color:#0b1b4d}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}} .tile{{background:#f4f6f9;border-radius:10px;padding:12px}}
.tile b{{font-size:22px;display:block}} .tile span{{font-size:12.5px;color:#4b5563}}
ol.first li{{margin:6px 0}} .oc{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .oc div{{background:#f4f6f9;border-radius:10px;padding:10px 12px}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13.5px}} th,td{{text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;vertical-align:top}}
th{{color:#4b5563;font-weight:600;background:#fafbfc}} .m{{color:#6b7280;font-size:12px;margin-top:3px}}
.callout{{background:#fffbeb;border-left:3px solid #b45309;border-radius:0 8px 8px 0;padding:10px 14px}}
.pill{{color:#fff;border-radius:999px;padding:2px 9px;font-size:12px;white-space:nowrap}} .legend li{{margin:3px 0;font-size:13px;color:#374151}}
svg .q{{font:600 13px sans-serif;fill:#9aa3af}} svg .ax{{font:12px sans-serif;fill:#4b5563}} svg .lb{{font:11px sans-serif;fill:#111827}}
@media(max-width:600px){{.oc{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>{e(T['title'])} · {e(a.store)}</h1><div class=sub>{e(a.period)}</div>
<div class=head>{e(s.get('headline', ''))}</div>
<div class=tiles>{''.join(f'<div class=tile><b>{e(v)}</b><span>{e(t)}</span></div>' for v, t in tiles)}</div>
<h2>{e(T['do_first'])}</h2><ol class=first>{''.join(f"<li><b>{e(x['owner'])}</b> · {e(x['action'])} <span class=m>- {e(x['why'])}</span></li>" for x in s.get('do_first', []))}</ol>
<div class=oc><div><b>{e(T['opportunity'])}</b><br>{e(s.get('opportunity', ''))}</div><div><b>{e(T['challenge'])}</b><br>{e(s.get('challenge', ''))}</div></div>
{money_plan_html(br, e) if br else ''}
<h2>{e(T['where_sits'])}</h2>{chart_svg(cs)}
<div class=m>{e(T['bubble'])}</div>
<h2>{e(T['scorecard_h'])}</h2><div class=tw><table><tr><th>{e(T['c_cat'])}</th><th>{e(T['c_spend'].format(days=SD))}</th><th>{e(T['c_conv'])}</th><th>{e(T['c_peer'])}</th><th>{e(T['c_play'])}</th><th>{e(T['c_when'])}</th><th>{e(T['c_next'])}</th></tr>{rows}</table></div>
<ul class=legend><li>{e(T['lg_conv'].replace('**', ''))}</li>
<li>{e(T['lg_peer'].replace('**', ''))}</li>
<li>{e(T['lg_play'].replace('**', ''))}</li></ul>
{(f'<h2>{e(T["actions"])}</h2><div class=tw><table><tr><th>{e(T["a_num"])}</th><th>{e(T["a_owner"])}</th><th>{e(T["a_action"])}</th><th>{e(T["a_size"])}</th><th>{e(T["a_when"])}</th><th>{e(T["a_check"])}</th><th>{e(T["a_stop"])}</th></tr>' + acts + '</table></div>') if acts else ''}
<h2>{e(T['goals'])}</h2><div class=tw><table><tr><th>{e(T['c_cat'])}</th><th>{e(T['g_adtype'])}</th><th>{e(T['g_fair'])}</th><th>{e(T['g_you'])}</th><th>{e(T['g_pos'])}</th><th>{e(T['g_level'])}</th></tr>{goals_html}</table></div>
{fixes}
<h2>{e(T['notes'])}</h2><ul class=legend>{''.join(f'<li>{e(n)}</li>' for n in d['notes'] + d.get('market_notes', []))}{('<li>' + e(T['not_checked']) + e(s['not_checked']) + '</li>') if s.get('not_checked') else ''}</ul>
</main></body></html>"""
    with open(os.path.join(a.out, "report.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote report.md, report.html" + (f" - {len(errs)} check(s) failed" if errs else ""))
    return errs


if __name__ == "__main__":
    main()
