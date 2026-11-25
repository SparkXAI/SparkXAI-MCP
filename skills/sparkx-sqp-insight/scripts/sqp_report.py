#!/usr/bin/env python3
"""
sqp_report.py - render a shareable, self-contained HTML report from sqp_calc.py output,
in the SparkX report design (ink on white, Sora / Inter, blue-violet glow, tabs as screens,
light and dark themes, EN / 中文 / 日本語 switch that always opens in English, prints every
tab in order).

Numbers come ONLY from sqp_summary.json (and the optional ad / product files pulled through
MCP), so they are identical in every language. Words come from a narrative JSON written for
the user; translations sit under "i18n".

Usage:
  python3 sqp_report.py --summary sqp_summary.json --narrative narrative.json \
      --template health --out report.html [--brand sparkx|none] \
      [--ads ads.json --baseline-roas 5.07] [--products products.json] [--store-ads store_ads.json]
      [--names names.json] [--actions-csv sqp_actions.csv] [--plan plan.json]

narrative.json (English at the top level; "i18n" holds the same keys for zh and ja):
{
  "title": "SQP Audit", "store": "<store name> · <marketplace>", "period": "4 weeks · Oct 11 - Nov 7, 2026",
  "headline": "One sentence, 20 words or fewer, with its number.",
  "subline": "One supporting sentence.",
  "takeaways": {"funnel": "", "leaks": "", "portfolio": "", "concentration": "", "ads": "", "products": "",
                "gaps": "", "protect": ""},
  "actions": [{"action": "", "why": "", "owner": "Ads", "impact": "~380 orders",
               "where": "Product (ASIN) carrying the searches", "measure": "What to check after 2 SQP weeks"}],
  "group_picks": {"scale_candidates": [...], "fix_listing": [...], "fix_or_cut": [...]},
  "products_names": {"B0XXXX": "Short product name"},
  "ads_queries": ["query", ...],
  "limits": ["..."],
  "i18n": {"zh": {"title": "", "headline": "", "subline": "", "takeaways": {...}, "actions": [...],
                  "limits": [...], "period": "", "store": "", "products_names": {...}},
           "ja": {...}}
}
A language missing from "i18n" falls back to the English narrative with translated labels.
"""
import argparse, csv, io, json, html, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqp_tips import TIPS, LABELS

_L = {"lang": "en"}


def info(key):
    """A small (i) button that shows what a measure is and how to use it."""
    t = TIPS[_L["lang"]].get(key)
    if not t:
        return ""
    how = LABELS[_L["lang"]]["how"]
    return (f'<button class="info" type="button" data-tip-t="{esc(t[0])}" data-tip-b="{esc(t[1])}" '
            f'data-tip-h="{esc(how)}: {esc(t[2])}" aria-label="{esc(t[0])}: {esc(t[1])} {esc(t[2])}">i</button>')


def tipattr(title, body):
    return f' data-tip-t="{esc(title)}" data-tip-b="{esc(body)}" tabindex="0"'

LANGS = [("en", "EN"), ("zh", "中文"), ("ja", "日本語")]

UI = {
 "en": {
  "overview": "Overview", "funnel": "Funnel", "searches": "Searches", "ads": "Ads and products", "actions": "Actions", "notes": "Notes",
  "at_glance": "At a glance", "look_next": "Where to look next", "open": "Open",
  "s_purch": "purchase share · <b>{a}</b> of {b} purchases across {c} searches",
  "s_click": "of clicks · versus <b>{a}</b> of impressions",
  "s_cvr": "your conversion versus the market · <b>{a}</b> vs {b} of clicks",
  "s_lost": "orders within reach · <b>{a}</b> after the click, {b} before",
  "n_actions": "{n} actions, each with an owner and what is at stake.",
  "built_on": "Built on {src}{ads}. Notes explains how to read it.",
  "plus_ads": " and SparkX ad data for the same weeks",
  "src": "Amazon Search Query Performance (Brand Analytics)", "src_x": ", read through SparkX",
  "f_eyebrow": "Funnel", "f_h": "Where you win, and where orders slip away",
  "f_share": "Your share at each step", "f_slip": "Where orders slip away",
  "impr": "Impressions", "clicks": "Clicks", "purch": "Purchases",
  "lg_after": "After the click: converts below market", "lg_before": "Before the click: below your usual click-through",
  "s_eyebrow": "Searches", "s_h": "Which searches to defend, grow or fix",
  "s_quad": "Your searches by share and conversion", "s_conc": "How concentrated your sales are",
  "c_top_you": "Top 10 searches · your purchases", "c_top_mkt": "Top 10 searches · market purchases", "c_next": "Next 20 searches · market purchases",
  "c_note": "Your purchase share on the next 20 searches averages {a}.",
  "q_defend": "Defend", "q_scale": "Scale", "q_fix": "Fix the listing", "q_cut": "Fix before more spend",
  "q_defend_d": "High share, at or above market conversion", "q_scale_d": "Low share, converts above market",
  "q_fix_d": "High share, below market conversion", "q_cut_d": "Low share, below market conversion",
  "q_note": "Plus {a} searches converting at market with low share, and {b} with fewer than 20 clicks, too few to judge.",
  "p_title": "Searches to protect", "p_note": "You win 20% or more of purchases on these. Keep them covered by exact-match ads.",
  "h_search": "Search", "h_vol": "Searches", "h_pshare": "Your purchase share", "h_pbrand": "Your purchases",
  "g_title": "Big searches where you are barely visible", "h_ishare": "Your impression share", "h_mcvr": "Market conversion", "h_today": "Today",
  "a_few": "A few sales", "no_sales": "No sales yet", "g_note": "{n} searches in your categories where you get under 1% of impressions.",
  "a_eyebrow": "Ads and products", "a_h": "What the ad report shows, and what it misses", "a_res": "Ad results on the same searches",
  "h_view": "SQP view", "h_cvx": "Conversion vs market", "h_spend": "Ad spend", "h_roas": "Ad ROAS", "h_store_avg": " (store avg {a})",
  "r_reach": "Within reach · {a} orders", "r_room": "Room · {a} share",
  "pr_title": "Products with the most orders within reach", "h_prod": "Product", "h_reach": "Orders within reach", "h_sales": "Total sales",
  "x_eyebrow": "Next steps", "x_h": "What to do next", "n_eyebrow": "Notes", "n_h": "How to read this report",
  "l_ads": "Ad results use 7-14 day ad attribution and include other products bought; SQP counts purchases within 24 hours. They sit side by side and are never subtracted.",
  "l_cap": "The search-term export stopped at its 10,000-row cap, so totals are a floor.",
  "l_sqp": "SQP counts orders, not revenue, and has no campaigns, spend or competitor names.",
  "s_value": "≈ <b>{v}</b> at {aov} of ad sales per ad order · a ceiling, not a forecast",
  "h_price": "Your price vs market",
  "h_clicks": "Ad clicks",
  "h_cpc": "CPC",
  "h_acos": "ACOS",
  "h_reach_room": "Within reach / room",
  "h_ads_today": "Ads today",
  "h_group": "Group",
  "h_yprod": "Your product",
  "no_ads": "No ads",
  "check_fit": "Check product fit",
  "head": "Head term",
  "h_main": "Main searches",
  "need_detail": "Needs the ASIN detail export",
  "start_title": "Where to start in each group",
  "start_note": "The first searches to work on in each group, with the product that carries them and its price against the market.",
  "csv_btn": "Download all {n} searches (CSV)",
  "csv_note": "Every search with 20+ clicks: group, shares, conversion vs market, orders within reach, your product and its price. Open it in Excel or Sheets to filter.",
  "conquest": "{q} is another brand's name. {store} wins {s} of its purchases, but it is a conquest term, not one to protect, so it is listed apart.",
  "act_where": "Where",
  "act_check": "Check in 2 SQP weeks",
  "room_mp": "Room · {a} market purchases",
  "l_price": "Price vs market compares your listing's median click price with the market's on the same search. Pack sizes differ, so read a large gap as 'show value per serving', not 'cut the price'.",
  "l_insuf": "{a} searches have fewer than 20 clicks. Together they hold {b} of your purchases and are not judged here.",
  "l_value": "The dollar figure multiplies orders within reach by the store's ad sales per ad order ({aov}, Sponsored Products, same weeks). It assumes every search reaches the market's conversion and usual click-through: a ceiling, not a forecast.",
  "l_adcvr": "Ad clicks, CPC and ACOS come from SparkX ad data for the same weeks. Ad conversion counts 7-day orders including other products, so it runs higher than SQP conversion; compare each only with its own kind.",
  "b_title": "Brand, competitor and generic searches",
  "h_mktp": "Market purchases",
  "c_names": "Biggest of them: {q}.",
  "spread": "Main searches convert fine: the gap is spread over many smaller searches (see the CSV).",
  "b_type": "Search type",
  "seg_own": "Your brand names",
  "seg_comp": "Other brands' names",
  "seg_gen": "Generic (no brand)",
  "h_mcvr2": "Market conversion",
  "h_clickp": "Shoppers click at",
  "h_buyp": "Shoppers buy at",
  "h_step": "Buy vs click price",
  "h_adcpc": "Ad CPC",
  "h_adroas": "Ad ROAS",
  "h_aov": "Ad sales per order",
  "lg_click": "Median price of what shoppers click",
  "lg_buy": "Median price of what they buy",
  "b_comp_title": "Other brands shoppers search for",
  "h_brand": "Brand",
  "b_gap": "Your brand names appear in only {a} searches in this export, while ads on your brand names drew {b} clicks in the same weeks: the export misses most branded searches. Size branded demand from the ad report or a branded SQP pull; the rates and prices above still hold.",
  "data": "Data", "print": "Print / PDF", "dark": "☾ Dark", "light": "☀ Light", "lang_label": "Language",
  "aba_eyebrow": "Market demand", "aba_h": "How much the market wanted these searches",
  "aba_band": "ABA rank band", "aba_q": "Searches", "aba_mcvr": "Market conversion",
  "aba_impr": "Your impressions", "aba_clk": "Your clicks", "aba_pur": "Your orders",
  "aba_cvr": "Your conversion", "aba_share": "Your purchase share",
  "aba_trend": "Demand direction: {up} rising, {down} falling, {stable} flat (a rank getting smaller means the search got more popular).",
  "aba_conc": "Median top-3 click share {v}% - {n} of {q} searches are more than half owned by three listings.",
  "aba_own": "ABA top-3 ASINs seen: {n}. They are the most-clicked listings on the search, not automatically competitors{own}.",
  "aba_own_unverified": " - no own-ASIN list was passed, so none has been checked against your own catalogue",
  "aba_none": "No ABA in this pull. ABA is attached to weekly marketSearchQuery rows only; marketAsinQuery rows and aggregated rows never carry it.",
  "aba_cov": "ABA covers {r} of {t} weekly market rows ({q} searches, {w} weeks).",
  "aba_band_t": "By ABA rank band", "aba_asin_t": "Most-clicked ASINs on these searches",
  "h_aba_asin": "ASIN", "h_aba_nq": "Searches", "h_aba_cs": "Top click share", "h_aba_own": "Yours?",
  "aba_own_yes": "yours", "aba_own_no": "not yours", "aba_own_unknown": "unverified",
 },
 "zh": {
  "overview": "总览", "funnel": "漏斗", "searches": "搜索词", "ads": "广告与产品", "actions": "行动", "notes": "说明",
  "aba_eyebrow": "市场需求", "aba_h": "市场对这些搜索词的需求有多大",
  "aba_band": "ABA 排名区间", "aba_q": "词数", "aba_mcvr": "市场转化率",
  "aba_impr": "我方曝光", "aba_clk": "我方点击", "aba_pur": "我方订单",
  "aba_cvr": "我方转化率", "aba_share": "我方购买份额",
  "aba_trend": "需求方向：{up} 个上升，{down} 个下降，{stable} 个持平（排名数字变小 = 这个词更热门了）。",
  "aba_conc": "Top3 点击份额中位数 {v}%——{q} 个词里有 {n} 个被三个 listing 占去一半以上。",
  "aba_own": "ABA Top3 里共出现 {n} 个 ASIN。它们只是该词上点击最多的 listing，不自动等于竞品{own}。",
  "aba_own_unverified": "——本次没有传入自家 ASIN 清单，所以没有任何一个与自家商品做过比对",
  "aba_none": "本次取数没有 ABA。ABA 只挂在周粒度的 marketSearchQuery 行上；marketAsinQuery 行和按周合并的行都不带。",
  "aba_cov": "ABA 覆盖 {t} 行周度市场数据中的 {r} 行（{q} 个搜索词，{w} 周）。",
  "aba_band_t": "按 ABA 排名区间", "aba_asin_t": "这些词上点击最多的 ASIN",
  "h_aba_asin": "ASIN", "h_aba_nq": "出现词数", "h_aba_cs": "最高点击份额", "h_aba_own": "是自家吗",
  "aba_own_yes": "自家", "aba_own_no": "非自家", "aba_own_unknown": "未核实",
  "at_glance": "一眼看懂", "look_next": "接下来看哪里", "open": "打开",
  "s_purch": "购买份额 · {c} 个搜索词共 {b} 笔购买中占 <b>{a}</b>",
  "s_click": "点击份额 · 曝光份额为 <b>{a}</b>",
  "s_cvr": "你的转化率 vs 市场 · <b>{a}</b> vs {b}（按点击）",
  "s_lost": "可争取的订单 · 点击后 <b>{a}</b>，点击前 {b}",
  "n_actions": "{n} 项行动，每项都有负责人和可争取的量。",
  "built_on": "数据来自 {src}{ads}。读法见「说明」。",
  "plus_ads": "，以及同期 SparkX 广告数据",
  "src": "Amazon 搜索词表现（Brand Analytics）", "src_x": "，经 SparkX 整理",
  "f_eyebrow": "漏斗", "f_h": "你在哪里赢，订单在哪里流失",
  "f_share": "每一步的份额", "f_slip": "订单在哪里流失",
  "impr": "曝光", "clicks": "点击", "purch": "购买",
  "lg_after": "点击后：转化低于市场", "lg_before": "点击前：低于你平时的点击率",
  "s_eyebrow": "搜索词", "s_h": "哪些词该守、该扩、该修",
  "s_quad": "按份额与转化分组的搜索词", "s_conc": "销售有多集中",
  "c_top_you": "前 10 个搜索词 · 占你的购买", "c_top_mkt": "前 10 个搜索词 · 占市场购买", "c_next": "接下来 20 个搜索词 · 占市场购买",
  "c_note": "你在接下来 20 个搜索词上的平均购买份额为 {a}。",
  "q_defend": "守住", "q_scale": "扩量", "q_fix": "修 listing", "q_cut": "先修再加投",
  "q_defend_d": "份额高，转化不低于市场", "q_scale_d": "份额低，转化高于市场",
  "q_fix_d": "份额高，转化低于市场", "q_cut_d": "份额低，转化低于市场",
  "q_note": "另有 {a} 个词转化与市场持平但份额低，{b} 个词点击不足 20 次，样本太少无法判断。",
  "p_title": "要守住的搜索词", "p_note": "你在这些词上拿下 20% 以上的购买，请保持精准匹配广告覆盖。",
  "h_search": "搜索词", "h_vol": "搜索量", "h_pshare": "你的购买份额", "h_pbrand": "你的购买数",
  "g_title": "搜索量大但你几乎没曝光的词", "h_ishare": "你的曝光份额", "h_mcvr": "市场转化率", "h_today": "现状",
  "a_few": "有少量销售", "no_sales": "尚无销售", "g_note": "你的品类里有 {n} 个搜索词，你的曝光份额不到 1%。",
  "a_eyebrow": "广告与产品", "a_h": "广告报表看得到什么、看不到什么", "a_res": "同一批搜索词的广告表现",
  "h_view": "SQP 视角", "h_cvx": "转化 vs 市场", "h_spend": "广告花费", "h_roas": "广告 ROAS", "h_store_avg": "（店铺平均 {a}）",
  "r_reach": "可争取 · {a} 单", "r_room": "有空间 · 份额 {a}",
  "pr_title": "可争取订单最多的产品", "h_prod": "产品", "h_reach": "可争取订单", "h_sales": "总销售额",
  "x_eyebrow": "下一步", "x_h": "接下来做什么", "n_eyebrow": "说明", "n_h": "如何阅读这份报告",
  "l_ads": "广告数据采用 7–14 天归因，并包含连带购买的其他商品；SQP 只计点击后 24 小时内的购买。两者并列展示，绝不相减。",
  "l_cap": "搜索词导出达到 10,000 行上限，合计数为下限。",
  "l_sqp": "SQP 统计的是订单数而非销售额，也没有广告活动、花费或竞品名称。",
  "s_value": "≈ <b>{v}</b>（按每笔广告订单 {aov} 广告销售额估算）· 是上限，不是预测",
  "h_price": "你的价格 vs 市场",
  "h_clicks": "广告点击",
  "h_cpc": "CPC",
  "h_acos": "ACOS",
  "h_reach_room": "可争取 / 空间",
  "h_ads_today": "目前广告",
  "h_group": "分组",
  "h_yprod": "你的产品",
  "no_ads": "无广告",
  "check_fit": "先确认产品是否匹配",
  "head": "大词",
  "h_main": "主要搜索词",
  "need_detail": "需要 ASIN 明细导出",
  "start_title": "每组先从哪里做",
  "start_note": "每组最先要处理的搜索词，以及承接它的产品和该产品相对市场的价格。",
  "csv_btn": "下载全部 {n} 个搜索词（CSV）",
  "csv_note": "所有点击 20 次以上的搜索词：分组、份额、转化 vs 市场、可争取订单、承接产品及其价格。可在 Excel 或表格中筛选。",
  "conquest": "{q} 是其他品牌的品牌词。{store} 拿下了其中 {s} 的购买，但它属于抢占词而不是要守的词，因此单独列出。",
  "act_where": "位置",
  "act_check": "2 个 SQP 周后检查",
  "room_mp": "空间 · 市场购买 {a}",
  "l_price": "价格 vs 市场：比较你的 listing 与市场在同一搜索词上的点击价格中位数。包装规格不同，差距大时应理解为「展示每份价格的优势」，而不是「降价」。",
  "l_insuf": "有 {a} 个搜索词点击不足 20 次，合计占你购买的 {b}，本报告不对它们下结论。",
  "l_value": "金额 = 可争取订单 × 店铺每笔广告订单的广告销售额（{aov}，Sponsored Products，同期）。假设每个搜索词都达到市场转化率和你平时的点击率，因此是上限，不是预测。",
  "l_adcvr": "广告点击、CPC 和 ACOS 来自同期 SparkX 广告数据。广告转化按 7 天订单计算并包含其他商品，所以高于 SQP 转化率；两者只能各自比较。",
  "b_title": "品牌词、竞品品牌词与通用词",
  "h_mktp": "市场购买",
  "c_names": "其中最大的：{q}。",
  "spread": "主要搜索词转化正常：差距分散在许多小词上（见 CSV）。",
  "b_type": "搜索词类型",
  "seg_own": "你的品牌词",
  "seg_comp": "其他品牌词",
  "seg_gen": "通用词（无品牌）",
  "h_mcvr2": "市场转化率",
  "h_clickp": "买家点击价格",
  "h_buyp": "买家购买价格",
  "h_step": "购买价 vs 点击价",
  "h_adcpc": "广告 CPC",
  "h_adroas": "广告 ROAS",
  "h_aov": "每单广告销售额",
  "lg_click": "买家点击商品的价格中位数",
  "lg_buy": "买家购买商品的价格中位数",
  "b_comp_title": "买家搜索的其他品牌",
  "h_brand": "品牌",
  "b_gap": "本导出中只有 {a} 次搜索包含你的品牌词，而同期你的品牌词广告点击有 {b} 次：导出漏掉了大部分品牌搜索。品牌需求规模请看广告报表或单独拉品牌词的 SQP；上面的比率和价格仍然成立。",
  "data": "数据", "print": "打印 / PDF", "dark": "☾ 深色", "light": "☀ 浅色", "lang_label": "语言",
 },
 "ja": {
  "overview": "概要", "funnel": "ファネル", "searches": "検索語", "ads": "広告と商品", "actions": "アクション", "notes": "注記",
  "aba_eyebrow": "市場需要", "aba_h": "これらの検索クエリに対する市場の需要",
  "aba_band": "ABA順位帯", "aba_q": "クエリ数", "aba_mcvr": "市場転換率",
  "aba_impr": "自社インプレッション", "aba_clk": "自社クリック", "aba_pur": "自社注文",
  "aba_cvr": "自社転換率", "aba_share": "自社購入シェア",
  "aba_trend": "需要の方向：上昇 {up}、下降 {down}、横ばい {stable}（順位の数値が小さいほど検索が増えています）。",
  "aba_conc": "上位3商品のクリックシェア中央値 {v}% —— {q} クエリ中 {n} 件は3商品で半分以上を占有。",
  "aba_own": "ABA上位3に登場したASINは {n} 件。これらは当該クエリで最もクリックされた商品であり、自動的に競合とは限りません{own}。",
  "aba_own_unverified": "（自社ASINリストが渡されていないため、自社商品との照合は行われていません）",
  "aba_none": "今回の取得にABAはありません。ABAは週次のmarketSearchQuery行にのみ付与されます。",
  "aba_cov": "ABAは週次市場データ {t} 行のうち {r} 行（{q} クエリ、{w} 週）をカバー。",
  "aba_band_t": "ABA順位帯別", "aba_asin_t": "これらのクエリで最もクリックされたASIN",
  "h_aba_asin": "ASIN", "h_aba_nq": "出現クエリ数", "h_aba_cs": "最高クリックシェア", "h_aba_own": "自社商品か",
  "aba_own_yes": "自社", "aba_own_no": "自社以外", "aba_own_unknown": "未確認",
  "at_glance": "ひと目でわかるポイント", "look_next": "次に見るところ", "open": "開く",
  "s_purch": "購入シェア · {c} 検索語の購入 {b} 件のうち <b>{a}</b>",
  "s_click": "クリックシェア · インプレッションシェアは <b>{a}</b>",
  "s_cvr": "市場と比べたコンバージョン · <b>{a}</b> vs {b}（クリックあたり）",
  "s_lost": "獲得可能な注文 · クリック後 <b>{a}</b>、クリック前 {b}",
  "n_actions": "{n} 件のアクション。それぞれ担当と見込み効果つき。",
  "built_on": "{src}{ads}をもとに作成。数値はすべてストア自身のデータです。読み方は「注記」をご覧ください。",
  "plus_ads": "および同期間の SparkX 広告データ",
  "src": "Amazon 検索クエリパフォーマンス（ブランド分析）", "src_x": "（SparkX 経由）",
  "f_eyebrow": "ファネル", "f_h": "勝っているところ、注文が逃げているところ",
  "f_share": "各ステップのシェア", "f_slip": "注文が逃げているところ",
  "impr": "インプレッション", "clicks": "クリック", "purch": "購入",
  "lg_after": "クリック後：市場よりコンバージョンが低い", "lg_before": "クリック前：普段のクリック率を下回る",
  "s_eyebrow": "検索語", "s_h": "守る・伸ばす・直す検索語",
  "s_quad": "シェアとコンバージョンで見た検索語", "s_conc": "売上の集中度",
  "c_top_you": "上位 10 検索語 · 自社購入に占める割合", "c_top_mkt": "上位 10 検索語 · 市場購入に占める割合", "c_next": "次の 20 検索語 · 市場購入に占める割合",
  "c_note": "次の 20 検索語での平均購入シェアは {a} です。",
  "q_defend": "守る", "q_scale": "伸ばす", "q_fix": "商品ページを直す", "q_cut": "広告を増やす前に直す",
  "q_defend_d": "シェア高・コンバージョンは市場並み以上", "q_scale_d": "シェア低・コンバージョンは市場以上",
  "q_fix_d": "シェア高・コンバージョンは市場未満", "q_cut_d": "シェア低・コンバージョンは市場未満",
  "q_note": "ほかに市場並みでシェアの低い検索語が {a} 件、クリック 20 未満で判断できない検索語が {b} 件あります。",
  "p_title": "守るべき検索語", "p_note": "購入の 20% 以上を獲得している検索語です。完全一致広告でのカバーを続けてください。",
  "h_search": "検索語", "h_vol": "検索数", "h_pshare": "購入シェア", "h_pbrand": "購入数",
  "g_title": "検索数が多いのにほぼ表示されていない検索語", "h_ishare": "インプレッションシェア", "h_mcvr": "市場コンバージョン", "h_today": "現状",
  "a_few": "少し売れている", "no_sales": "まだ売上なし", "g_note": "カテゴリ内でインプレッションシェアが 1% 未満の検索語が {n} 件あります。",
  "a_eyebrow": "広告と商品", "a_h": "広告レポートでわかること、わからないこと", "a_res": "同じ検索語の広告成果",
  "h_view": "SQP の見方", "h_cvx": "市場比コンバージョン", "h_spend": "広告費", "h_roas": "広告 ROAS", "h_store_avg": "（ストア平均 {a}）",
  "r_reach": "獲得可能 · {a} 件", "r_room": "伸びしろ · シェア {a}",
  "pr_title": "獲得可能な注文が多い商品", "h_prod": "商品", "h_reach": "獲得可能な注文", "h_sales": "総売上",
  "x_eyebrow": "次のステップ", "x_h": "次にやること", "n_eyebrow": "注記", "n_h": "このレポートの読み方",
  "l_ads": "広告データは 7〜14 日のアトリビューションで、ほかの商品の購入も含みます。SQP はクリック後 24 時間以内の購入のみを数えます。並べて示しますが、差し引きはしません。",
  "l_cap": "検索語のエクスポートが上限の 10,000 行に達したため、合計は下限値です。",
  "l_sqp": "SQP は売上金額ではなく注文数を数えます。キャンペーン、広告費、競合名は含みません。",
  "s_value": "≈ <b>{v}</b>（広告注文あたりの広告売上 {aov} で換算）· 上限であり予測ではありません",
  "h_price": "価格 vs 市場",
  "h_clicks": "広告クリック",
  "h_cpc": "CPC",
  "h_acos": "ACOS",
  "h_reach_room": "獲得可能 / 伸びしろ",
  "h_ads_today": "現在の広告",
  "h_group": "グループ",
  "h_yprod": "自社商品",
  "no_ads": "広告なし",
  "check_fit": "商品の適合を確認",
  "head": "ビッグワード",
  "h_main": "主な検索語",
  "need_detail": "ASIN 詳細エクスポートが必要",
  "start_title": "各グループでまず取り組む検索語",
  "start_note": "各グループで最初に取り組む検索語と、それを担う商品、その市場比の価格です。",
  "csv_btn": "全 {n} 検索語をダウンロード（CSV）",
  "csv_note": "クリック 20 以上の全検索語：グループ、シェア、市場比コンバージョン、獲得可能な注文、担う商品と価格。Excel やスプレッドシートで絞り込めます。",
  "conquest": "{q} は他ブランドの名前です。{store} は購入の {s} を獲得していますが、守る語ではなく攻める語なので別に記載しています。",
  "act_where": "対象",
  "act_check": "SQP 2 週間後に確認",
  "room_mp": "伸びしろ · 市場購入 {a}",
  "l_price": "価格 vs 市場は、同じ検索語での自社商品と市場のクリック価格の中央値を比べたものです。容量が異なるため、差が大きい場合は「値下げ」ではなく「1 回分あたりの価値を見せる」と読んでください。",
  "l_insuf": "クリック 20 未満の検索語が {a} 件あり、購入の {b} を占めます。ここでは判断していません。",
  "l_value": "金額は、獲得可能な注文 × ストアの広告注文あたり広告売上（{aov}、スポンサープロダクト、同期間）です。すべての検索語が市場のコンバージョンと普段のクリック率に届いた場合の上限で、予測ではありません。",
  "l_adcvr": "広告クリック、CPC、ACOS は同期間の SparkX 広告データです。広告のコンバージョンは他商品を含む 7 日間の注文なので SQP より高くなります。それぞれ同じ種類同士でのみ比べてください。",
  "b_title": "自社ブランド名・他社ブランド名・一般語の検索",
  "h_mktp": "市場の購入",
  "c_names": "主な検索語：{q}。",
  "spread": "主な検索語は問題なし：差は多くの小さな検索語に分散しています（CSV 参照）。",
  "b_type": "検索の種類",
  "seg_own": "自社ブランド名",
  "seg_comp": "他社ブランド名",
  "seg_gen": "一般語（ブランドなし）",
  "h_mcvr2": "市場コンバージョン",
  "h_clickp": "クリックされる価格",
  "h_buyp": "購入される価格",
  "h_step": "購入価格 vs クリック価格",
  "h_adcpc": "広告 CPC",
  "h_adroas": "広告 ROAS",
  "h_aov": "注文あたり広告売上",
  "lg_click": "クリックされた商品の価格中央値",
  "lg_buy": "購入された商品の価格中央値",
  "b_comp_title": "買い物客が検索する他社ブランド",
  "h_brand": "ブランド",
  "b_gap": "このエクスポートで自社ブランド名を含む検索は {a} 回のみですが、同期間の自社ブランド名への広告クリックは {b} 回でした。エクスポートはブランド検索の大半を含んでいません。ブランド需要の規模は広告レポートかブランド名での SQP 取得で確認してください。上の比率と価格はそのまま有効です。",
  "data": "データ", "print": "印刷 / PDF", "dark": "☾ ダーク", "light": "☀ ライト", "lang_label": "言語",
 },
}


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def pct(v, d=1):
    return "-" if v is None else f"{v * 100:.{d}f}%"


def pct_raw(v, d=2):
    """For values that are ALREADY 0-100 (every ABA share, and the rates aba_section computes).
    Using pct() on them would multiply by 100 a second time."""
    return "-" if v is None else f"{float(v):.{d}f}%"


def num(v):
    if v is None:
        return "-"
    v = float(v)
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs(v) >= 1e4:
        return f"{v / 1e3:.1f}K"
    return f"{v:,.0f}"


def norm(q):
    return " ".join(str(q or "").lower().replace("+", " ").split())


# ------------------------------------------------------------------ blocks
def bars(rows, fmt=pct, hi=None, tip_tmpl=None):
    rows = [(l, v) for l, v in rows if v is not None]
    if not rows:
        return ""
    mx = max(v for _, v in rows) or 1
    out = []
    for l, v in rows:
        cls = "bar-fill hl" if l == hi else "bar-fill"
        ta = tipattr(l, tip_tmpl.format(l=l, v=fmt(v))) if tip_tmpl else ""
        out.append(f'<div class="bar-row"{ta}><div class="bar-label">{esc(l)}</div><div class="bar-track">'
                   f'<div class="{cls}" style="width:{max(v / mx * 85, 1.5):.1f}%"></div>'
                   f'<span class="bar-val">{fmt(v)}</span></div></div>')
    return f'<div class="bars">{"".join(out)}</div>'


def leak_bars(rows, T, n=8):
    tot = lambda r: (r.get("lost_orders_conv") or 0) + (r.get("lost_orders_click_rel") or 0)
    rows = [r for r in rows if tot(r) > 0][:n]
    if not rows:
        return ""
    mx = max(tot(r) for r in rows)
    out = []
    for r in rows:
        a, b = r.get("lost_orders_conv") or 0, r.get("lost_orders_click_rel") or 0
        tb = LABELS[_L["lang"]]["bar_leak"].format(q=r.get("query"), a=num(a), b=num(b), cb=pct(r.get("cvr_brand")), cm=pct(r.get("cvr_mkt")))
        out.append(f'<div class="bar-row"{tipattr(r.get("query"), tb)}><div class="bar-label">{esc(r.get("query"))}</div><div class="bar-track">'
                   f'<div class="bar-fill" style="width:{a / mx * 85:.1f}%"></div>'
                   f'<div class="bar-fill muted" style="width:{b / mx * 85:.1f}%"></div>'
                   f'<span class="bar-val">{num(a + b)}</span></div></div>')
    return (f'<div class="bars stacked">{"".join(out)}</div><div class="legend">'
            f'<span><i style="background:var(--bar)"></i>{esc(T["lg_after"])} {info("after_click")}</span>'
            f'<span><i style="background:var(--bar-muted)"></i>{esc(T["lg_before"])} {info("before_click")}</span></div>')


def conc_bars(c, T):
    if not c:
        return ""
    rows = [(T["c_top_you"], c.get("brand_share_of_own_purchases")),
            (T["c_top_mkt"], c.get("market_share_of_purchases_same_queries")),
            (T["c_next"], c.get("next_20_market_purchase_share"))]
    nx = c.get("next_20_top_room") or []
    names = ", ".join(f'{r["query"]} ({pct(r.get("purch_share"))})' for r in nx[:5])
    extra = (" " + T["c_names"].format(q=names)) if names else ""
    return bars(rows, hi=T["c_top_you"]) + f'<p class="note">{esc(T["c_note"].format(a=pct(c.get("next_20_avg_brand_purchase_share"))) + extra)}</p>'


def portfolio(quads, T):
    cells = [("q_defend", "defend"), ("q_scale", "scale"), ("q_fix", "fix_listing_risk"), ("q_cut", "fix_or_cut")]
    tk_ = {"defend": "defend", "scale": "scale", "fix_listing_risk": "fix", "fix_or_cut": "cut"}
    cards = "".join(f'<div class="card{" hl" if k == "scale" else ""}"><div class="eyebrow">{esc(T[t])} {info(tk_[k])}</div>'
                    f'<div class="stat">{num(quads.get(k, 0))}</div><div class="stat-label">{esc(T[t + "_d"])}</div></div>'
                    for t, k in cells)
    note = T["q_note"].format(a=num(quads.get("hold_at_market", 0)), b=num(quads.get("insufficient_sample", 0)))
    return f'<div class="grid grid-2">{cards}</div><p class="note">{esc(note)}</p>'


def table(head, rows, nums=()):
    def h(x):
        return f"{esc(x[0])} {info(x[1])}" if isinstance(x, tuple) else esc(x)
    th = "".join(f'<th class="num">{h(x)}</th>' if i in nums else f"<th>{h(x)}</th>" for i, x in enumerate(head))
    trs = "".join("<tr>" + "".join(f'<td class="num">{c}</td>' if i in nums else f"<td>{c}</td>" for i, c in enumerate(r)) + "</tr>"
                  for r in rows)
    return f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def money(v):
    return "-" if v is None else f"${num(v)}"


def price_cell(r):
    """Your listing's median click price vs the market median on that search."""
    g = r.get("price_gap") if r else None
    if g is None:
        return "-"
    tag = "down" if g >= 0.15 else ("up" if g <= -0.05 else "")
    sign = "+" if g >= 0 else "−"
    return (f'<span class="tag {tag}">{sign}{abs(g) * 100:.0f}%</span>'
            f'<div class="xs muted">${r["price_top_asin"]:.2f} vs ${r["price_mkt_median"]:.2f}</div>')


def prod_cell(q, r, names, T, fallback=None):
    a = (r or {}).get("top_asin")
    if not a:
        return f'{esc(q)}<div class="xs muted">{esc(fallback or "")}</div>' if fallback else esc(q)
    nm = (names.get(a) or {}).get("name") if isinstance(names.get(a), dict) else names.get(a)
    return f'{esc(q)}<div class="xs muted">{esc(nm or a)} · {esc(a)}</div>'


def ads_rows(s, ads, baseline, picks, T, names=None):
    if not ads:
        return []
    by = {norm(r.get("query") or r.get("query_")): r for r in ads}
    leak = {norm(r["query"]): r for r in (s.get("fix_first") or {}).get("rows", [])}
    scale = {norm(r["query"]): r for r in s.get("scale_candidates", [])}
    out = []
    for q in picks:
        k, a = norm(q), by.get(norm(q))
        if not a:
            continue
        if k in leak:
            r = leak[k]
            role = T["r_reach"].format(a=num((r.get("lost_orders_conv") or 0) + (r.get("lost_orders_click_rel") or 0)))
            cv = f"{r['cvr_brand'] / r['cvr_mkt']:.2f}x" if r.get("cvr_mkt") else "-"
        elif k in scale:
            r = scale[k]
            role = T["r_room"].format(a=pct(r.get("purch_share")))
            cv = f"{r.get('cvr_index', 0):.2f}x"
        else:
            continue
        roas = a.get("ROAS")
        tag = "" if roas is None or not baseline else ("up" if roas >= baseline else "down")
        acos = a.get("ACOS")
        out.append([prod_cell(q, r, names or {}, T), price_cell(r), cv, esc(role), money(a.get("Spend")),
                    f"${a['CPC']:.2f}" if a.get("CPC") is not None else "-",
                    f"{acos:.1f}%" if acos is not None else "-",
                    f'<span class="tag {tag}">{roas:.2f}</span>' if roas is not None else "-"])
    return out


def group_rows(s, picks, names, T, n=4):
    """Top searches per group; picks (from the narrative) can drop off-category searches."""
    src = [("q_scale", "scale_candidates"), ("q_fix", "fix_listing"), ("q_cut", "fix_or_cut")]
    out = []
    for lab, key in src:
        rows = s.get(key) or []
        want = (picks or {}).get(key)
        if want:
            by = {norm(r["query"]): r for r in rows}
            rows = [by[norm(q)] for q in want if norm(q) in by]
        else:
            rows = [r for r in rows if r.get("top_asin")]
        for r in rows[:n]:
            stake = (T["room_mp"].format(a=num(r.get("purch_mkt"))) if key == "scale_candidates"
                     else T["r_reach"].format(a=num((r.get("lost_orders_conv") or 0) + (r.get("lost_orders_click_rel") or 0))))
            out.append([prod_cell(r["query"], r, names, T), f'<span class="chip">{esc(T[lab])}</span>',
                        f"{r['cvr_index']:.2f}x" if r.get("cvr_index") is not None else "-", pct(r.get("purch_share")),
                        price_cell(r), esc(stake)])
    return out


def brand_block(bs, seg_ads, T, tk):
    """Own-brand vs other brands vs generic: what shoppers click, what they buy, what ads cost."""
    segs = (bs or {}).get("segments") or {}
    if not segs:
        return ""
    order = [("own_brand", "seg_own"), ("competitor_brand", "seg_comp"), ("generic", "seg_gen")]
    sa = seg_ads or {}
    mkt, mine, bars_ = [], [], []
    mx = max(max(v.get("click_price") or 0, v.get("purchase_price") or 0) for v in segs.values()) or 1
    for k, lab in order:
        v = segs.get(k)
        if not v:
            continue
        st = v.get("price_step")
        a = sa.get(k) or {}
        name = f'<span class="nowrap">{esc(T[lab])}</span>'
        mkt.append([name, num(v["search_volume"]), pct(v.get("cvr_mkt")),
                    f'${v["click_price"]:.2f}' if v.get("click_price") else "-",
                    f'${v["purchase_price"]:.2f}' if v.get("purchase_price") else "-",
                    f'<b>{"+" if st >= 0 else "−"}{abs(st) * 100:.0f}%</b>' if st is not None else "-"])
        mine.append([name, pct(v.get("purch_share")), f'{v["cvr_index"]:.2f}x' if v.get("cvr_index") else "-",
                     f'${a["CPC"]:.2f}' if a.get("CPC") else "-", f'{a["ROAS"]:.2f}' if a.get("ROAS") else "-",
                     f'${a["SalesPerOrder"]:.2f}' if a.get("SalesPerOrder") else "-"])
        cpv, ppv = v.get("click_price") or 0, v.get("purchase_price") or 0
        tipb = f'{T["lg_click"]}: ${cpv:.2f} · {T["lg_buy"]}: ${ppv:.2f}'
        bars_.append(f'<div class="bar-row pair"{tipattr(T[lab], tipb)}><div class="bar-label">{esc(T[lab])}</div><div class="bar-stack">'
                     f'<div class="bar-track"><div class="bar-fill" style="width:{cpv / mx * 80:.1f}%"></div><span class="bar-val">${cpv:.2f}</span></div>'
                     f'<div class="bar-track"><div class="bar-fill hl" style="width:{ppv / mx * 80:.1f}%"></div><span class="bar-val">${ppv:.2f}</span></div></div></div>')
    legend = (f'<div class="legend"><span><i style="background:var(--bar)"></i>{esc(T["lg_click"])}</span>'
              f'<span><i style="background:var(--highlight)"></i>{esc(T["lg_buy"])}</span></div>')
    body = (f'<div class="bars">{"".join(bars_)}</div>{legend}'
            + table([T["b_type"], (T["h_vol"], "volume"), (T["h_mcvr2"], "mkt_cvr"), (T["h_clickp"], "seg_price"), (T["h_buyp"], "seg_price"),
                     (T["h_step"], "price_step")], mkt, nums=(1, 2, 3, 4, 5)))
    has_ads = any(sa.get(k) for k, _ in order)
    head = [T["b_type"], (T["h_pshare"], "purch_share"), (T["h_cvx"], "cvr_index"), (T["h_adcpc"], "seg_ads"), (T["h_adroas"], "roas"), T["h_aov"]]
    body += table(head if has_ads else head[:3], mine if has_ads else [r[:3] for r in mine], nums=tuple(range(1, 6 if has_ads else 3)))
    own = segs.get("own_brand") or {}
    if sa.get("own_brand") and own.get("search_volume") is not None and sa["own_brand"].get("Clicks", 0) > 3 * own["search_volume"]:
        body += f'<p class="note">{esc(T["b_gap"].format(a=num(own["search_volume"]), b=num(sa["own_brand"]["Clicks"])))}</p>'
    out = section(T["b_title"], body, tk.get("brand"), tip="brand_seg")
    cb = (bs or {}).get("competitor_brands") or []
    if cb:
        rr = [[esc(x["brand"].title()), num(x["search_volume"]), num(x["purch_mkt"]), pct(x.get("purch_share"))] for x in cb[:8]]
        out += section(T["b_comp_title"], table([T["h_brand"], (T["h_vol"], "volume"), T["h_mktp"], (T["h_pshare"], "purch_share")], rr, nums=(1, 2, 3)),
                       tk.get("competitors"))
    return out


def plan_block(plan, lang):
    """Changes to confirm - the plan from sqp_plan.py (plan mode). The page cannot execute."""
    if not plan:
        return ""
    from sqp_plan import L as PL
    P = PL.get(lang) or PL["en"]
    rows = []
    for a in plan.get("rows", []):
        k = P["kinds"][a["kind"]].format(p=abs(a["pct"]) if a.get("pct") is not None else "")
        o = a.get("object", {})
        ft = f'{"-" if a.get("from") is None else a["from"]} → {a.get("to")}'
        rows.append([f'<b>{a["n"]}</b>', esc(f'{k} · "{o.get("text") or o.get("placement") or ""}"'),
                     f'<span class="xs">{esc(o.get("campaign") or "")}</span>', ft, f'<span class="xs">{esc(a.get("why") or "")}</span>'])
    if not rows:
        return ""
    other = plan.get("held", []) + plan.get("not_checked", [])
    notes = "".join(f'<li>{esc(str(h["object"].get("text") or h["object"].get("search") or h["object"].get("campaign")))}: '
                    f'{esc(h["reason"])}</li>' for h in other[:12])
    head = [x.strip() for x in P["head"].strip("|").split("|")]
    body = table(["#", head[1], head[2], head[3], head[4]], rows, nums=(3,))
    if plan.get("meta", {}).get("plan_only"):
        body = f'<p class="note"><b>{esc(P["plan_only"])}</b></p>' + body
    body += (f'<ul class="limits">{notes}</ul>' if notes else "") + f'<p class="note">{esc(P["how"])}</p>'
    return section(P["rows"], body)


def csv_block(path, T):
    if not path or not os.path.exists(path):
        return ""
    txt = open(path, encoding="utf-8").read()
    n = max(txt.count("\n") - 1, 0)
    return (f'<div class="dl"><button class="btn-ghost solid dl-btn" type="button" data-csv="sqp-csv">{esc(T["csv_btn"].format(n=f"{n:,}"))}</button>'
            f'<p class="note">{esc(T["csv_note"])}</p></div>')


def product_rows(s, products, names, T, n=6):
    av = (s.get("asin_view") or {}).get("top_by_lost_orders", [])[:n]
    pm = {p.get("parent_asin") or p.get("asin"): p for p in (products or [])}
    pq = s.get("product_queries") or {}
    out = []
    for r in av:
        p = pm.get(r["asin"], {})
        lost = (r.get("lost_orders_conv") or 0) + (r.get("lost_orders_click_rel") or 0)
        name = names.get(r["asin"]) or p.get("name") or r["asin"]
        qs = []
        for c in [r["asin"]] + list(p.get("children") or []):
            qs += pq.get(c, [])
        seen, uq = set(), []
        lostq = lambda x: (x.get("clicks_brand") or 0) * max(0.0, 1 - (x.get("cvr_index") or 1))
        for x in sorted(qs, key=lambda x: (-lostq(x), -(x.get("clicks_brand") or 0))):
            if x["query"] not in seen:
                seen.add(x["query"]); uq.append(x)
        qs = uq[:2]
        main = "<br>".join(f'{esc(x["query"])} <span class="muted">{x["cvr_index"]:.2f}x</span>' for x in qs) \
            or f'<span class="muted xs">{esc(T["need_detail"])}</span>'
        if qs and r.get("cvr_mkt") and r["cvr_brand"] / r["cvr_mkt"] < 0.8 and all((x.get("cvr_index") or 0) >= 0.9 for x in qs):
            main += f'<div class="xs muted">{esc(T["spread"])}</div>'
        out.append([f'{esc(name)}<div class="xs muted">{esc(r["asin"])}</div>', num(lost),
                    f"{r['cvr_brand'] / r['cvr_mkt']:.2f}x" if r.get("cvr_mkt") else "-", main,
                    f"${num(p['TotalSalesAmount'])}" if p.get("TotalSalesAmount") is not None else "-",
                    f"{p['ROAS']:.2f}" if p.get("ROAS") is not None else "-"])
    return out


def section(title, body, note=None, tip=None):
    if not body:
        return ""
    sub = f'<p class="section-sub">{esc(note)}</p>' if note else ""
    return f'<div class="section"><div class="section-head"><h2>{esc(title)} {info(tip) if tip else ""}</h2></div>{sub}{body}</div>'


def hero(eyebrow, h):
    return f'<div class="hero small"><span class="eyebrow">{esc(eyebrow)}</span><h2>{esc(h)}</h2></div>'


def narrative_for(n, lang):
    """English narrative at the top level; other languages override key by key."""
    if lang == "en":
        return n
    tr = (n.get("i18n") or {}).get(lang) or {}
    m = dict(n)
    for k, v in tr.items():
        if isinstance(v, dict) and isinstance(m.get(k), dict):
            m[k] = {**m[k], **v}
        else:
            m[k] = v
    return m


# ------------------------------------------------------------------ page
CSS = r"""
:root{
  --font-display:"Sora","Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Hiragino Sans",sans-serif;
  --font-sans:"Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans",sans-serif;
  --fs-xs:12px;--fs-sm:14px;--fs-md:16px;--fs-lg:18px;--fs-xl:22px;--fs-2xl:30px;--fs-3xl:52px;--fs-stat:44px;
  --sp-2:8px;--sp-3:12px;--sp-4:20px;--sp-5:28px;--sp-6:40px;--sp-7:64px;--sp-8:96px;
  --r-sm:4px;--r-md:6px;--r-lg:8px;--r-pill:999px;--maxw:1120px;--gutter:20px;
  --bg:#FFFFFF;--surface-2:#F4F4F4;--surface-3:#EAEAEA;--border:#E6E6E6;--border-2:#CFCFCF;
  --text:#050713;--text-2:#202228;--text-3:#6E6E73;--highlight:#003BF9;--bar:#050713;--bar-muted:#D4D4D8;
  --up-bg:rgba(0,59,249,.09);--down-bg:rgba(255,67,9,.10);--down:#C2410C;
  --mesh-bg:linear-gradient(120deg,rgba(78,180,254,.55),rgba(0,59,249,.22) 55%,rgba(110,0,211,.18)),linear-gradient(300deg,rgba(168,215,255,.45),rgba(206,0,132,.10));
  --dot:linear-gradient(135deg,#FFFFFF 0%,#A8D7FF 45%,#4EB4FE 100%);
  color-scheme:light;
}
:root[data-theme="dark"]{
  --bg:#050713;--surface-2:#10121D;--surface-3:#1A1D2A;--border:#1F2230;--border-2:#343849;
  --text:#EEEEEE;--text-2:#CCCCCC;--text-3:#8C8F9A;--highlight:#4EB4FE;--bar:#EEEEEE;--bar-muted:#2F3242;
  --up-bg:rgba(78,180,254,.16);--down-bg:rgba(255,132,0,.16);--down:#FFA45C;color-scheme:dark;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;overflow-x:clip}
body{margin:0;background:var(--bg);color:var(--text-2);font:var(--fs-md)/1.6 var(--font-sans);-webkit-font-smoothing:antialiased;overflow-x:clip}
h1,h2,h3{font-family:var(--font-display);font-weight:500;color:var(--text);line-height:1.15;margin:0 0 var(--sp-3);letter-spacing:-.02em}
h1{font-size:var(--fs-3xl);letter-spacing:-.04em;line-height:1.06;max-width:980px}
h2{font-size:var(--fs-2xl);letter-spacing:-.03em}
h3{font-size:var(--fs-lg)}
p{margin:0 0 var(--sp-3)} b{color:var(--text);font-weight:600}
.xs{font-size:var(--fs-xs)} .muted{color:var(--text-3)}
button{font:inherit;color:inherit}
.topbar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid var(--border)}
.topbar-row{max-width:var(--maxw);margin:0 auto;padding:14px var(--gutter) 0;display:flex;align-items:center;gap:var(--sp-4)}
.brand{font-family:var(--font-display);font-weight:500;font-size:15px;color:var(--text);display:flex;align-items:center;gap:10px;white-space:nowrap;min-width:0}
.brand span:last-child{overflow:hidden;text-overflow:ellipsis}
.brand-mark{width:14px;height:14px;border-radius:3px;background:var(--text);flex:none}
.top-actions{margin-left:auto;display:flex;gap:var(--sp-2)}
.btn-ghost{background:transparent;border:1px solid var(--border);border-radius:var(--r-pill);padding:6px 14px;font-size:13px;font-weight:500;color:var(--text);cursor:pointer}
.btn-ghost:hover{background:var(--surface-2)}
.btn-ghost.solid{background:var(--text);color:var(--bg);border-color:var(--text)}
.tabbar{max-width:var(--maxw);margin:0 auto;padding:0 var(--gutter);display:flex;gap:28px;overflow-x:auto;scrollbar-width:none}
.tabbar::-webkit-scrollbar{display:none}
.tab{background:none;border:0;border-bottom:1.5px solid transparent;padding:14px 0 12px;font-size:var(--fs-sm);color:var(--text-3);cursor:pointer;white-space:nowrap}
.tab:hover{color:var(--text)} .tab[aria-selected="true"]{color:var(--text);font-weight:500;border-bottom-color:var(--text)}
main{max-width:var(--maxw);margin:0 auto;padding:0 var(--gutter) var(--sp-8)}
.tabpanel[hidden]{display:none}
.hero{position:relative;isolation:isolate;padding:var(--sp-8) 0 var(--sp-6)}
.hero::before{content:"";position:absolute;z-index:-1;left:-160px;top:20px;width:540px;height:400px;border-radius:46% 54% 60% 40%/52% 44% 56% 48%;background:var(--mesh-bg);opacity:.9;filter:blur(56px) saturate(1.1);pointer-events:none}
.hero.small{padding:var(--sp-7) 0 var(--sp-2)} .hero.small::before{width:380px;height:240px;opacity:.55}
.eyebrow{display:block;font-size:var(--fs-sm);color:var(--text-3);margin-bottom:var(--sp-4)}
.lede{font-size:20px;color:var(--text-2);max-width:720px;line-height:1.55}
.sources-strip{margin-top:var(--sp-5);padding-left:var(--sp-4);border-left:1px solid var(--text);font-size:var(--fs-sm);color:var(--text-3);max-width:760px}
.section{margin-top:var(--sp-6)}
.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:var(--sp-4);margin-bottom:var(--sp-4);padding-bottom:var(--sp-4);border-bottom:1px solid var(--border)}
.section-head h2{margin:0;display:flex;align-items:center;gap:14px;font-size:var(--fs-xl)}
.section-head h2::before{content:"";flex:none;width:16px;height:16px;border-radius:50%;background:var(--dot)}
.section-sub{color:var(--text-3);font-size:var(--fs-md);max-width:760px;margin-bottom:var(--sp-4)}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.grid-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.card{position:relative;background:var(--surface-2);border-radius:var(--r-lg);padding:var(--sp-5);display:flex;flex-direction:column;min-width:0;border:1px solid transparent}
.card.hl{border-color:var(--highlight)}
.card .eyebrow{font-size:var(--fs-xs);margin-bottom:var(--sp-3)}
.card[data-goto]{cursor:pointer} .card[data-goto]:hover{background:var(--surface-3)}
.card p{flex:1}
.open{margin-top:var(--sp-3);font-size:var(--fs-sm);font-weight:500;color:var(--text)} .open::after{content:" →"}
.stat{font-family:var(--font-display);font-size:var(--fs-stat);font-weight:400;letter-spacing:-.045em;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.stat.hl{color:var(--highlight)}
.stat-label{color:var(--text-3);font-size:var(--fs-sm);margin-top:var(--sp-3);line-height:1.5}
.stat-label b{font-weight:500;color:var(--text-2)}
.callout{padding:var(--sp-4) 0;border-top:1px solid var(--text);border-bottom:1px solid var(--border);color:var(--text);font-family:var(--font-display);font-size:var(--fs-xl);line-height:1.4;letter-spacing:-.015em;margin:0 0 var(--sp-4)}
.section-head + .callout{border-top:0;padding-top:0}
.note{font-size:var(--fs-sm);color:var(--text-3);border-left:1px solid var(--border-2);padding-left:var(--sp-3);margin:var(--sp-4) 0}
.bars{display:grid;gap:10px;margin-top:var(--sp-3)}
.bar-row{display:grid;grid-template-columns:minmax(120px,30%) 1fr;gap:var(--sp-3);align-items:center;font-size:var(--fs-sm)}
.bar-label{color:var(--text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{height:22px;display:flex;align-items:center;min-width:0}
.bar-fill{height:6px;border-radius:1px;background:var(--bar);min-width:2px;flex:none}
.bar-fill.muted{background:var(--bar-muted);margin-left:2px} .bar-fill.hl{background:var(--highlight)}
.bars.stacked .bar-fill{height:8px}
.bar-val{margin-left:10px;font-weight:500;font-variant-numeric:tabular-nums;font-size:var(--fs-xs);white-space:nowrap;color:var(--text)}
.legend{display:flex;gap:var(--sp-4);flex-wrap:wrap;font-size:var(--fs-xs);color:var(--text-3);margin-top:var(--sp-3)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.table-wrap{overflow-x:auto;margin:var(--sp-3) 0 var(--sp-4);border-top:1px solid var(--text)}
table{border-collapse:collapse;width:100%;font-size:var(--fs-sm)}
th,td{text-align:left;padding:12px 14px 12px 0;border-bottom:1px solid var(--border);vertical-align:top}
td{color:var(--text-2)} td:first-child{color:var(--text);font-weight:500}
th{font-size:var(--fs-xs);color:var(--text-3);font-weight:450;white-space:nowrap}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tag{padding:2px 8px;border-radius:var(--r-sm);font-weight:600;font-variant-numeric:tabular-nums}
.tag.up{background:var(--up-bg);color:var(--highlight)} .tag.down{background:var(--down-bg);color:var(--down)}
.chip{display:inline-flex;align-items:center;padding:3px 10px;border-radius:var(--r-sm);background:var(--bg);border:1px solid var(--border);font-size:var(--fs-xs);color:var(--text-2)}
.chip.accent{background:var(--text);border-color:var(--text);color:var(--bg);font-weight:500}
.act{display:grid;grid-template-columns:34px 1fr;gap:var(--sp-3)}
.act-num{display:inline-flex;width:24px;height:24px;border-radius:var(--r-sm);align-items:center;justify-content:center;background:var(--text);color:var(--bg);font-size:var(--fs-xs);font-weight:500}
.act h3{margin-bottom:6px} .act p{flex:none} .act .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:var(--sp-3)}
.limits{padding-left:1.1em;max-width:780px} .limits li{margin-bottom:var(--sp-3);font-size:var(--fs-md)}
.footer{margin-top:var(--sp-7);padding-top:var(--sp-4);border-top:1px solid var(--border);font-size:var(--fs-xs);color:var(--text-3)}
@media (min-width:760px){:root{--gutter:40px}}
@media (max-width:760px){.grid-2{grid-template-columns:1fr}}
@media (max-width:600px){:root{--fs-3xl:32px;--fs-2xl:24px;--fs-xl:19px;--fs-stat:36px;--sp-8:56px;--sp-7:40px;--gutter:16px}
  .hero::before{left:-140px;width:400px;height:300px} .lede{font-size:var(--fs-lg)} .tabbar{gap:20px}
  .card{padding:var(--sp-4)} .bar-row{grid-template-columns:1fr;gap:2px} .bar-label{white-space:normal}
  th,td{padding:10px 10px 10px 0} .btn-ghost.solid{display:none}}
@media print{:root{--bg:#fff;--surface-2:#f3f3f3;--text:#000;--text-2:#222;--text-3:#555;--border:#ccc}
  .topbar{display:none!important} .tabpanel,.tabpanel[hidden]{display:block!important;break-before:page}
  .tabpanel:first-of-type{break-before:auto} .card,.act,table{break-inside:avoid} main{max-width:none;padding:0}
  .hero{padding:24px 0}}

.info{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;border:1px solid var(--border-2);background:var(--bg);color:var(--text-3);font:600 10px/1 var(--font-sans);font-style:italic;cursor:help;padding:0;vertical-align:2px;margin-left:4px;flex:none}
.info:hover,.info:focus-visible{border-color:var(--text);color:var(--text);outline:none}
.section-head h2 .info{width:18px;height:18px;font-size:11px;vertical-align:4px}
.stat-label .info{float:right;margin:2px 0 4px 8px}
.bar-row[data-tip-t]{cursor:default;border-radius:4px} .bar-row[data-tip-t]:hover{background:var(--surface-2)} .bar-row[data-tip-t]:focus-visible{outline:2px solid var(--text);outline-offset:2px}
#tip{position:fixed;z-index:60;max-width:320px;background:var(--text);color:var(--bg);font-size:12.5px;line-height:1.5;padding:10px 12px;border-radius:var(--r-md);box-shadow:0 20px 60px -20px rgba(0,0,0,.35);pointer-events:none;opacity:0;transition:opacity 120ms}
#tip.show{opacity:1} #tip b{display:block;margin-bottom:3px;color:inherit;font-weight:600} #tip .h{display:block;margin-top:6px;opacity:.8}
.terms-list{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.term{background:var(--surface-2);border-radius:var(--r-md);padding:var(--sp-4);font-size:var(--fs-sm)} .term b{display:block;font-weight:500;margin-bottom:4px} .term p{margin:0 0 6px} .term .how{color:var(--text-3)} .term .how span{font-weight:500;color:var(--text-2)}
@media print{.info,#tip,.dl{display:none!important}}
.stat-sub{margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:var(--fs-xs);color:var(--text-3)} .stat-sub b{color:var(--text);font-weight:600}
.act-meta{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;margin:6px 0 0;font-size:var(--fs-sm)} .act-meta dt{color:var(--text-3);white-space:nowrap} .act-meta dd{margin:0;color:var(--text-2)}
.dl{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:var(--sp-4)} .dl .note{margin:0;flex:1;min-width:220px}
.chip.xs{font-size:11px;padding:1px 6px;vertical-align:1px}
.nowrap{white-space:nowrap} .table-wrap + .table-wrap{margin-top:var(--sp-4)} .bar-row.pair{align-items:center} .bar-stack{display:flex;flex-direction:column;gap:4px;flex:1;min-width:0} .bar-stack .bar-track{width:100%}
@media (max-width:600px){.act-meta{grid-template-columns:1fr;gap:0 0}.act-meta dd{margin-bottom:6px}}
.lang-switch{display:inline-flex;border:1px solid var(--border);border-radius:var(--r-pill);padding:2px;gap:2px}
.lang-btn{background:transparent;border:0;border-radius:var(--r-pill);padding:4px 10px;font-size:12.5px;font-weight:500;color:var(--text-3);cursor:pointer}
.lang-btn[aria-pressed="true"]{background:var(--text);color:var(--bg)}
.lang-root[hidden],.tab[hidden]{display:none!important}
@media (max-width:600px){.topbar-row{flex-wrap:wrap;row-gap:8px}.top-actions{margin-left:0;width:100%;justify-content:space-between}}
@media print{.lang-root[hidden]{display:none!important}}
"""

JS = r"""
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let lang='en',tab='overview';
const UIL=JSON.parse(document.getElementById('ui-labels').textContent);
function render(){
  $$('.lang-root').forEach(r=>r.hidden=r.dataset.lang!==lang);
  $$('.lang-btn').forEach(b=>b.setAttribute('aria-pressed',b.dataset.lang===lang));
  document.documentElement.lang=lang==='zh'?'zh-CN':lang;
  const root=$('.lang-root[data-lang="'+lang+'"]');
  if(!root.querySelector('.tabpanel[data-tab="'+tab+'"]'))tab='overview';
  $$('.tab').forEach(t=>{t.hidden=!root.querySelector('.tabpanel[data-tab="'+t.dataset.tab+'"]');
    t.textContent=UIL[lang][t.dataset.tab];t.setAttribute('aria-selected',t.dataset.tab===tab)});
  root.querySelectorAll('.tabpanel').forEach(p=>p.hidden=p.dataset.tab!==tab);
  $('#printBtn').textContent=UIL[lang].print;applyTheme();
}
function show(id){tab=id;render();window.scrollTo({top:0})}
$$('.tab').forEach(t=>t.addEventListener('click',()=>show(t.dataset.tab)));
$$('[data-goto]').forEach(c=>c.addEventListener('click',()=>show(c.dataset.goto)));
$$('.lang-btn').forEach(b=>b.addEventListener('click',()=>{lang=b.dataset.lang;render()}));
let theme='light';try{theme=localStorage.getItem('xn-sqp-theme')||'light'}catch(e){}
function applyTheme(){document.documentElement.dataset.theme=theme;$('#themeBtn').textContent=theme==='light'?UIL[lang].dark:UIL[lang].light}
$('#themeBtn').addEventListener('click',()=>{theme=theme==='light'?'dark':'light';applyTheme();try{localStorage.setItem('xn-sqp-theme',theme)}catch(e){}});
$('#printBtn').addEventListener('click',()=>window.print());
render();
$$('[data-csv]').forEach(b=>b.addEventListener('click',()=>{const s=document.getElementById(b.dataset.csv);
  const blob=new Blob(['\ufeff'+s.textContent.replace(/<\\\//g,'</')],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download=s.dataset.name;document.body.appendChild(a);a.click();a.remove()}));
const tip=document.getElementById('tip');let pinned=null;
function place(el){const t=el.dataset.tipT,b=el.dataset.tipB,h=el.dataset.tipH;
  tip.innerHTML='';const bt=document.createElement('b');bt.textContent=t;tip.appendChild(bt);
  const sb=document.createElement('span');sb.textContent=b;tip.appendChild(sb);
  if(h){const sh=document.createElement('span');sh.className='h';sh.textContent=h;tip.appendChild(sh)}
  tip.classList.add('show');const r=el.getBoundingClientRect(),w=tip.offsetWidth,hh=tip.offsetHeight;
  let x=Math.min(Math.max(8,r.left+r.width/2-w/2),window.innerWidth-w-8),y=r.top-hh-10;if(y<8)y=r.bottom+10;
  tip.style.left=x+'px';tip.style.top=y+'px'}
function hide(){tip.classList.remove('show');pinned=null}
document.addEventListener('mouseover',e=>{const el=e.target.closest('[data-tip-t]');if(el&&!pinned)place(el)});
document.addEventListener('mouseout',e=>{const el=e.target.closest('[data-tip-t]');if(el&&!pinned&&!el.contains(e.relatedTarget))hide()});
document.addEventListener('focusin',e=>{const el=e.target.closest('[data-tip-t]');if(el)place(el)});
document.addEventListener('focusout',()=>{if(!pinned)hide()});
document.addEventListener('click',e=>{const el=e.target.closest('[data-tip-t]');if(el){e.stopPropagation();if(pinned===el){hide()}else{pinned=el;place(el)}}else hide()},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape')hide()});window.addEventListener('scroll',hide,{passive:true});
"""


def render_body(s, n, brand, lang, open_lang="en", ads=None, baseline=None, products=None, store_ads=None, names=None, csv_path=None, seg_ads=None, plan=None):
    T = UI[lang]
    _L["lang"] = lang
    pos = s.get("store_position") or {}
    ff = s.get("fix_first") or {}
    uc = s.get("use_cases") or {}
    tk = n.get("takeaways", {})
    lost = (ff.get("lost_orders_conversion_stage") or 0) + (ff.get("lost_orders_click_stage") or 0)
    capped = any("export cap" in x for x in s.get("notes", []))
    store, period, title = n.get("store", ""), n.get("period", ""), n.get("title", "SQP Audit")
    src = T["src"] + (T["src_x"] if brand == "sparkx" else "")
    names = names or {}
    adby = {norm(r.get("query") or r.get("query_")): r for r in (ads or [])}
    aov = (store_ads["Sales"] / store_ads["Conversions"]) if store_ads and store_ads.get("Conversions") else None
    aov_s = f"${aov:,.2f}" if aov else ""

    def ads_today(q):
        a = adby.get(norm(q))
        if not a or not a.get("Spend"):
            return f'<span class="muted">{esc(T["no_ads"])}</span>' if ads else "-"
        tag = "" if not baseline or a.get("ROAS") is None else ("up" if a["ROAS"] >= baseline else "down")
        return f'{money(a["Spend"])} · <span class="tag {tag}">{a["ROAS"]:.2f}</span>'

    stats = [
        (pct(pos.get("purchase_share")), info("purch_share") + T["s_purch"].format(a=num(pos.get("brand_purchases")), b=num(pos.get("market_purchases")), c=num(pos.get("queries"))), False),
        (pct(pos.get("click_share")), info("click_share") + T["s_click"].format(a=pct(pos.get("impression_share"))), False),
        (f"{pos['cvr_index']:.2f}x" if pos.get("cvr_index") else "-", info("cvr_index") + T["s_cvr"].format(a=pct(pos.get("cvr_brand")), b=pct(pos.get("cvr_market"))), False),
        (num(lost), info("within_reach") + T["s_lost"].format(a=num(ff.get("lost_orders_conversion_stage")), b=num(ff.get("lost_orders_click_stage")))
         + (f'<div class="stat-sub">{T["s_value"].format(v=money(lost * aov), aov=aov_s)}</div>' if aov else ""), True),
    ]
    stat_html = "".join(f'<div class="card"><div class="stat{" hl" if hl else ""}">{esc(v)}</div><div class="stat-label">{l}</div></div>' for v, l, hl in stats)
    nav = [("funnel", tk.get("leaks") or tk.get("funnel")), ("searches", tk.get("portfolio")), ("ads", tk.get("ads")),
           ("actions", T["n_actions"].format(n=len(n.get("actions", []))))]
    if not ads and not products:
        nav = [x for x in nav if x[0] != "ads"]
    nav_html = "".join(f'<div class="card" data-goto="{k}"><div class="eyebrow">{esc(T[k])}</div><p>{esc(x or "")}</p><span class="open">{esc(T["open"])}</span></div>' for k, x in nav)
    lede = f'<p class="lede">{esc(n["subline"])}</p>' if n.get("subline") else ""
    overview = (f'<div class="hero"><span class="eyebrow">{esc(title)} · {esc(store)} · {esc(period)}</span>'
                f'<h1>{esc(n.get("headline", ""))}</h1>{lede}'
                f'<div class="sources-strip">{esc(T["built_on"].format(src=src, ads=T["plus_ads"] if ads else ""))}</div></div>'
                + section(T["at_glance"], f'<div class="grid">{stat_html}</div>', tip="sqp")
                + section(T["look_next"], f'<div class="grid grid-2">{nav_html}</div>'))

    funnel_rows = [(T["impr"], pos.get("impression_share")), (T["clicks"], pos.get("click_share")), (T["purch"], pos.get("purchase_share"))]
    funnel = (hero(T["f_eyebrow"], T["f_h"]) + section(T["f_share"], bars(funnel_rows, hi=T["purch"], tip_tmpl=LABELS[lang]["bar_share"]), tk.get("funnel"), tip="funnel")
              + section(T["f_slip"], leak_bars(ff.get("rows", []), T), tk.get("leaks"), tip="within_reach"))

    sx = section(T["s_quad"], portfolio(s.get("quadrants") or {}, T), tk.get("portfolio"), tip="quadrants")
    gr = group_rows(s, n.get("group_picks"), names, T)
    if gr:
        sx += section(T["start_title"], table([T["h_search"], T["h_group"], (T["h_cvx"], "cvr_index"), (T["h_pshare"], "purch_share"),
                                               (T["h_price"], "price"), T["h_reach_room"]], gr, nums=(2, 3, 4, 5))
                      + csv_block(csv_path, T), tk.get("groups") or T["start_note"])
    sx += section(T["s_conc"], conc_bars(s.get("concentration"), T), tk.get("concentration"), tip="concentration")
    sx += brand_block(s.get("brand_segments"), seg_ads, T, tk)
    if (uc.get("protect") or {}).get("rows"):
        rows = [[esc(r["query"]), num(r["search_volume"]), pct(r.get("purch_share")), num(r.get("purch_brand")), ads_today(r["query"])]
                for r in uc["protect"]["rows"][:8]]
        cq = (uc.get("conquest") or {}).get("rows") or []
        cqn = "".join(f'<p class="note">{esc(T["conquest"].format(q=r["query"], s=pct(r.get("purch_share")), store=(store.split("·")[0].strip() or "The store")))}</p>' for r in cq[:2])
        sx += section(T["p_title"], table([T["h_search"], (T["h_vol"], "volume"), (T["h_pshare"], "purch_share"), T["h_pbrand"],
                                           (T["h_ads_today"], "roas")], rows, nums=(1, 2, 3, 4)) + cqn,
                      tk.get("protect") or T["p_note"], tip="protect")
    if (uc.get("coverage_gaps") or {}).get("rows"):
        g = uc["coverage_gaps"]
        rows = [[prod_cell(r["query"], r, names, T, T["check_fit"]) + (f' <span class="chip xs">{esc(T["head"])}</span>' if r.get("head_term") else ""),
                 num(r["search_volume"]), pct(r.get("impr_share")), price_cell(r), ads_today(r["query"]),
                 T["a_few"] if (r.get("purch_brand") or 0) > 0 else T["no_sales"]] for r in g["rows"][:8]]
        sx += section(T["g_title"], table([T["h_search"], (T["h_vol"], "volume"), (T["h_ishare"], "impr_share"), (T["h_price"], "price"),
                                           (T["h_ads_today"], "roas"), T["h_today"]], rows, nums=(1, 2, 3, 4)),
                      tk.get("gaps") or T["g_note"].format(n=g["count"]), tip="gaps")
    # ABA: the same figures the markdown carries, so both deliverables agree (reports.md)
    aba = s.get("aba") or {}
    ab = ""
    if aba.get("status") == "INCLUDED":
        head = [T["aba_band"], (T["aba_q"], "volume"), (T["aba_mcvr"], "cvr"), (T["aba_impr"], "volume"),
                (T["aba_clk"], "volume"), (T["aba_pur"], "volume"), (T["aba_cvr"], "cvr"), (T["aba_share"], "share")]
        brows = [[b["band"], num(b["queries"]), pct_raw(b["market_cvr"]), num(b["brand_impressions"]),
                  num(b["brand_clicks"]), num(b["brand_purchases"]), pct_raw(b["brand_cvr"]),
                  pct_raw(b["purchase_share"])] for b in aba.get("bands") or []]
        if brows:
            ab += section(T["aba_band_t"], table(head, brows, nums=(1, 2, 3, 4, 5, 6, 7)),
                          aba.get("coverage_note") or T["aba_cov"].format(
                              r=aba.get("rows_with_aba", 0), t=aba.get("rows_total", 0),
                              q=aba.get("queries_with_aba", 0), w=len(aba.get("weeks") or [])))
        tr = aba.get("rank_trend") or {}
        cc = aba.get("concentration") or {}
        bits = []
        if tr:
            bits.append(T["aba_trend"].format(up=tr.get("up", 0), down=tr.get("down", 0), stable=tr.get("stable", 0)))
        if cc:
            bits.append(T["aba_conc"].format(v=cc.get("median_top3_click_share"),
                                             n=cc.get("queries_over_50pct", 0), q=cc.get("queries", 0)))
        ta = aba.get("top_asins") or {}
        if ta.get("rows"):
            own_lab = {True: T["aba_own_yes"], False: T["aba_own_no"], None: T["aba_own_unknown"]}
            arows = [[r["asin"], num(r["queries"]), pct_raw(r["max_click_share"]),
                      own_lab.get(r.get("is_own_asin"), T["aba_own_unknown"])] for r in ta["rows"][:10]]
            note = T["aba_own"].format(n=len(ta["rows"]),
                                       own="" if ta.get("own_asin_list_given") else T["aba_own_unverified"])
            ab += section(T["aba_asin_t"], table([T["h_aba_asin"], (T["h_aba_nq"], "volume"),
                                                  (T["h_aba_cs"], "share"), T["h_aba_own"]],
                                                 arows, nums=(1, 2)), note)
        if bits:
            ab = f'<p class="section-sub">{esc(" ".join(bits))}</p>' + ab
    elif aba.get("status") in ("NOT_RETURNED", "NOT_REQUESTED"):
        ab = f'<p class="section-sub">{esc(T["aba_none"])}</p>'
    if ab:
        sx += hero(T["aba_eyebrow"], T["aba_h"]) + ab

    searches = hero(T["s_eyebrow"], T["s_h"]) + sx

    ax = ""
    picks = n.get("ads_queries") or [r["query"] for r in ff.get("rows", [])[:5]] + [r["query"] for r in s.get("scale_candidates", [])[:3]]
    ar = ads_rows(s, ads, baseline, picks, T, names)
    if ar:
        base = T["h_store_avg"].format(a=f"{baseline:.2f}") if baseline else ""
        ax += section(T["a_res"], (f'<div class="callout">{esc(tk["ads"])}</div>' if tk.get("ads") else "")
                      + table([T["h_search"], (T["h_price"], "price"), (T["h_cvx"], "cvr_index"), T["h_view"], T["h_spend"], T["h_cpc"],
                               T["h_acos"], (T["h_roas"] + base, "roas")], ar, nums=(1, 2, 4, 5, 6, 7))
                      + f'<p class="note">{esc(T["l_adcvr"])}</p>', tip="ads_vs_sqp")
    pr = product_rows(s, products, n.get("products_names") or {}, T)
    if pr and products:
        ax += section(T["pr_title"], table([T["h_prod"], (T["h_reach"], "within_reach"), (T["h_cvx"], "prod_cvx"), T["h_main"], T["h_sales"], (T["h_roas"], "roas")],
                                           pr, nums=(1, 2, 4, 5)), tk.get("products"))
    ads_tab = (hero(T["a_eyebrow"], T["a_h"]) + ax) if ax else ""

    def act_extra(a):
        x = ""
        if a.get("where"):
            x += f'<dl class="act-meta"><dt>{esc(T["act_where"])}</dt><dd>{esc(a["where"])}</dd></dl>'
        if a.get("measure"):
            x += f'<dl class="act-meta"><dt>{esc(T["act_check"])}</dt><dd>{esc(a["measure"])}</dd></dl>'
        return x
    acts = "".join(f'<div class="card act"><span class="act-num">{i + 1}</span><div><h3>{esc(a.get("action"))}</h3>'
                   f'<p>{esc(a.get("why"))}</p>{act_extra(a)}<div class="chips"><span class="chip accent">{esc(a.get("owner"))}</span>'
                   f'<span class="chip">{esc(a.get("impact"))}</span>'
                   + (f'<span class="chip">{esc(a["when"])}</span>' if a.get("when") else "") + '</div></div></div>' for i, a in enumerate(n.get("actions", [])))
    actions = (hero(T["x_eyebrow"], T["x_h"]) + (f'<div class="grid grid-2">{acts}</div>' if acts else "")
               + plan_block(plan, lang) + csv_block(csv_path, T))

    limits = list(n.get("limits", []))
    if ads:
        limits.append(T["l_ads"])
    if capped:
        limits.append(T["l_cap"])
    if aov:
        limits.append(T["l_value"].format(aov=aov_s))
    if any(r.get("price_gap") is not None for r in ff.get("rows", [])):
        limits.append(T["l_price"])
    qps = s.get("quadrant_purchase_share") or {}
    if qps.get("insufficient_sample") is not None:
        limits.append(T["l_insuf"].format(a=num((s.get("quadrants") or {}).get("insufficient_sample")), b=pct(qps["insufficient_sample"])))
    limits.append(T["l_sqp"])
    order = ["sqp", "funnel", "impr_share", "click_share", "purch_share", "cvr_index", "mkt_cvr", "volume", "within_reach",
             "after_click", "before_click", "quadrants", "defend", "scale", "fix", "cut", "concentration", "protect", "gaps",
             "price", "head", "brand_seg", "seg_price", "price_step", "seg_ads", "ads_vs_sqp", "roas", "prod_cvx"]
    LB = LABELS[lang]
    terms = "".join(f'<div class="term"><b>{esc(TIPS[lang][k][0])}</b><p>{esc(TIPS[lang][k][1])}</p><p class="how"><span>{esc(LB["how"])}</span> {esc(TIPS[lang][k][2])}</p></div>'
                    for k in order if k in TIPS[lang])
    notes = (hero(T["n_eyebrow"], T["n_h"]) + f'<ul class="limits">{"".join(f"<li>{esc(x)}</li>" for x in limits)}</ul>'
             + section(LB["glossary"], f'<div class="terms-list">{terms}</div>', LB["glossary_sub"]))

    tabs = [("overview", overview), ("funnel", funnel), ("searches", searches), ("ads", ads_tab), ("actions", actions), ("notes", notes)]
    foot = f'{esc(title)} · {esc(store)} · {esc(period)} · {esc(T["data"])}: {esc(src)}'
    panels = "".join(f'<section class="tabpanel" data-tab="{k}" role="tabpanel">{b}<div class="footer">{foot}</div></section>' for k, b in tabs if b)
    return f'<div class="lang-root" data-lang="{lang}"{"" if lang == open_lang else " hidden"}>{panels}</div>', [k for k, b in tabs if b]


def render_health(s, n, brand, ads=None, baseline=None, products=None, store_ads=None, names=None, csv_path=None,
                  seg_ads=None, plan=None, open_lang="en"):
    """open_lang: the language the page opens in. The other two stay available in the switcher."""
    bodies, tab_keys = [], None
    for code, _ in LANGS:
        b, keys = render_body(s, narrative_for(n, code), brand, code, open_lang, ads, baseline, products, store_ads,
                              names, csv_path, seg_ads, plan)
        bodies.append(b)
        tab_keys = tab_keys or keys
    title, store = n.get("title", "SQP Audit"), n.get("store", "")
    T = UI[open_lang]
    tabbar = "".join(f'<button class="tab" type="button" role="tab" data-tab="{k}">{esc(T[k])}</button>'
                     for k in ["overview", "funnel", "searches", "ads", "actions", "notes"])
    langs = "".join(f'<button class="lang-btn" type="button" data-lang="{c}" aria-pressed="{str(c == open_lang).lower()}">{l}</button>' for c, l in LANGS)
    brand_name = f"SparkX · {title}" if brand == "sparkx" else f"{store} · {title}"
    labels = json.dumps({c: {k: UI[c][k] for k in ("overview", "funnel", "searches", "ads", "actions", "notes", "print", "dark", "light")}
                         for c, _ in LANGS}, ensure_ascii=False)
    csv_data = ""
    if csv_path and os.path.exists(csv_path):
        fn = (store.split("·")[0].strip().lower().replace(" ", "_") or "store") + "_sqp_searches.csv"
        csv_data = (f'<script type="text/csv" id="sqp-csv" data-name="{esc(fn)}">'
                    + open(csv_path, encoding="utf-8").read().replace("</", "<\\/") + "</script>")
    js = JS.replace("let lang='en'", "let lang='" + open_lang + "'")
    return f"""<!doctype html><html lang="{open_lang}" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} · {esc(store)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;450;500;600&family=Sora:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="topbar"><div class="topbar-row"><div class="brand"><span class="brand-mark" aria-hidden="true"></span><span>{esc(brand_name)}</span></div>
<div class="top-actions"><div class="lang-switch" role="group" aria-label="Language">{langs}</div>
<button class="btn-ghost" id="themeBtn" type="button">☾ Dark</button><button class="btn-ghost solid" id="printBtn" type="button">Print / PDF</button></div></div>
<nav class="tabbar" role="tablist">{tabbar}</nav></header>
<main>{"".join(bodies)}</main><div id="tip" role="tooltip"></div>{csv_data}<script type="application/json" id="ui-labels">{labels}</script><script>{js}</script></body></html>"""


# --------------------------------------------------------------- markdown
MD_L = {
 "en": {"period": "Period", "store": "Store", "verdict": "Verdict", "position": "Where the store stands",
        "metric": "Metric", "you": "You", "market": "Market", "share": "Your share",
        "impr": "Impressions", "clicks": "Clicks", "purch": "Purchases", "cvr": "Conversion (purchases / clicks)",
        "searches": "Searches covered", "with_purch": "Searches with a purchase of yours",
        "leaks": "Where the orders go", "stage": "Stage", "orders": "Orders lost", "basis": "Basis",
        "conv_stage": "After the click (conversion)", "click_stage": "Before the click",
        "conv_basis": "at the market conversion rate (upper bound)",
        "click_basis": "against the store own median CTR index, not the market CTR",
        "top10": "The top 10 searches carry {pct:.0f}% of the loss.",
        "groups": "Searches by group", "group": "Group", "n": "Searches", "sh": "Share of your purchases",
        "g_fix_or_cut": "Fix or cut", "g_defend": "Defend", "g_fix_listing_risk": "Listing at risk",
        "g_insufficient_sample": "Insufficient sample (listed, never dropped)",
        "actions": "Actions", "action": "Action", "why": "Why", "owner": "Owner", "impact": "At stake",
        "where": "Where", "measure": "How we check",
        "aba": "Market demand (ABA)", "aba_band": "ABA rank band", "aba_q": "Searches",
        "aba_mcvr": "Market conversion", "aba_impr": "Your impressions", "aba_clk": "Your clicks",
        "aba_pur": "Your orders", "aba_cvr": "Your conversion", "aba_share": "Your purchase share",
        "aba_trend": "Demand direction: {up} rising, {down} falling, {stable} flat (a rank getting smaller means the search got more popular).",
        "aba_conc": "Median top-3 click share {v}% - {n} of {q} searches are more than half owned by three listings.",
        "aba_own": "ABA top-3 ASINs seen: {n}. They are the most-clicked listings on the search, not automatically competitors{own}.",
        "aba_own_unverified": " - no own-ASIN list was passed, so none of them has been checked against your own catalogue",
        "aba_none": "No ABA columns in this pull. ABA is attached to weekly marketSearchQuery rows only; marketAsinQuery rows and aggregated rows never carry it.",
        "aba_cov": "ABA covers {r} of {t} weekly market rows ({q} searches, {w} weeks).",
        "limits": "What this report cannot see",
        "src": "Computed by sqp_calc.py; every figure matches sqp_summary.json."},
 "zh": {"period": "周期", "store": "店铺", "verdict": "结论", "position": "店铺在市场的位置",
        "metric": "指标", "you": "本店", "market": "市场", "share": "本店占比",
        "impr": "曝光", "clicks": "点击", "purch": "购买", "cvr": "转化率（购买 / 点击）",
        "searches": "覆盖的搜索词", "with_purch": "出过单的搜索词",
        "leaks": "订单丢在哪一环", "stage": "环节", "orders": "丢失订单", "basis": "口径",
        "conv_stage": "点击之后（转化环节）", "click_stage": "点击之前",
        "conv_basis": "按市场转化率折算，是上限",
        "click_basis": "对比店铺自身 CTR 中位数，不是对比市场 CTR",
        "top10": "前 10 个搜索词占全部流失的 {pct:.0f}%。",
        "groups": "搜索词分组", "group": "分组", "n": "词数", "sh": "占本店购买",
        "g_fix_or_cut": "修或砍", "g_defend": "守住", "g_fix_listing_risk": "页面有风险",
        "g_insufficient_sample": "样本不足（照常列出，不丢弃）",
        "actions": "行动项", "action": "动作", "why": "为什么", "owner": "负责人", "impact": "量级",
        "where": "对象", "measure": "怎么验证",
        "aba": "市场需求（ABA）", "aba_band": "ABA 排名区间", "aba_q": "词数",
        "aba_mcvr": "市场转化率", "aba_impr": "我方曝光", "aba_clk": "我方点击",
        "aba_pur": "我方订单", "aba_cvr": "我方转化率", "aba_share": "我方购买份额",
        "aba_trend": "需求方向：{up} 个上升，{down} 个下降，{stable} 个持平（排名数字变小 = 这个词更热门了）。",
        "aba_conc": "Top3 点击份额中位数 {v}%——{q} 个词里有 {n} 个被三个listing占去一半以上。",
        "aba_own": "ABA Top3 里共出现 {n} 个 ASIN。它们只是该词上点击最多的listing，不自动等于竞品{own}。",
        "aba_own_unverified": "——本次没有传入自家 ASIN 清单，所以没有任何一个与自家商品做过比对",
        "aba_none": "本次取数没有 ABA 列。ABA 只挂在周粒度的 marketSearchQuery 行上；marketAsinQuery 行和按周合并的行都不带。",
        "aba_cov": "ABA 覆盖 {t} 行周度市场数据中的 {r} 行（{q} 个搜索词，{w} 周）。",
        "limits": "这份报告看不到什么",
        "src": "由 sqp_calc.py 计算；所有数字与 sqp_summary.json 一致。"},
 "ja": {"period": "期間", "store": "ストア", "verdict": "結論", "position": "市場における自社の位置",
        "metric": "指標", "you": "自社", "market": "市場", "share": "自社シェア",
        "impr": "インプレッション", "clicks": "クリック", "purch": "購入", "cvr": "転換率（購入 / クリック）",
        "searches": "対象の検索クエリ", "with_purch": "購入が発生した検索クエリ",
        "leaks": "注文が失われている段階", "stage": "段階", "orders": "失われた注文", "basis": "基準",
        "conv_stage": "クリック後（転換段階）", "click_stage": "クリック前",
        "conv_basis": "市場の転換率で換算した上限値",
        "click_basis": "市場CTRではなく自社CTR指数の中央値との比較",
        "top10": "上位10クエリが損失全体の {pct:.0f}% を占めます。",
        "groups": "検索クエリのグループ", "group": "グループ", "n": "クエリ数", "sh": "自社購入に占める割合",
        "g_fix_or_cut": "改善または停止", "g_defend": "維持", "g_fix_listing_risk": "商品ページに懸念",
        "g_insufficient_sample": "サンプル不足（除外せず掲載）",
        "actions": "アクション", "action": "アクション", "why": "理由", "owner": "担当", "impact": "規模",
        "where": "対象", "measure": "確認方法",
        "aba": "市場需要（ABA）", "aba_band": "ABA順位帯", "aba_q": "クエリ数",
        "aba_mcvr": "市場転換率", "aba_impr": "自社インプレッション", "aba_clk": "自社クリック",
        "aba_pur": "自社注文", "aba_cvr": "自社転換率", "aba_share": "自社購入シェア",
        "aba_trend": "需要の方向：上昇 {up}、下降 {down}、横ばい {stable}（順位の数値が小さくなるほど検索が増えています）。",
        "aba_conc": "上位3商品のクリックシェア中央値 {v}% —— {q} クエリ中 {n} 件は3商品で半分以上を占有。",
        "aba_own": "ABA上位3に登場したASINは {n} 件。これらは当該クエリで最もクリックされた商品であり、自動的に競合とは限りません{own}。",
        "aba_own_unverified": "（自社ASINリストが渡されていないため、自社商品との照合は行われていません）",
        "aba_none": "今回の取得にABA列はありません。ABAは週次のmarketSearchQuery行にのみ付与され、marketAsinQuery行や集計行には含まれません。",
        "aba_cov": "ABAは週次市場データ {t} 行のうち {r} 行（{q} クエリ、{w} 週）をカバーしています。",
        "limits": "本レポートで分からないこと",
        "src": "sqp_calc.py による算出。全ての数値は sqp_summary.json と一致します。"},
}


def _cell(v):
    return str(v).replace("|", "\\|")


def render_md(s, n, lang="en"):
    """Markdown twin of the HTML page: the default deliverable, same numbers, no interactivity."""
    M = MD_L.get(lang, MD_L["en"])
    nn = narrative_for(n, lang)
    sp = s.get("store_position") or {}
    ff = s.get("fix_first") or {}
    q = s.get("quadrants") or {}
    qs = s.get("quadrant_purchase_share") or {}
    tk = nn.get("takeaways") or {}
    o = ["# " + nn.get("title", "SQP Audit"), ""]
    if nn.get("store"):
        o.append("**" + M["store"] + "**: " + str(nn["store"]) + "  ")
    if nn.get("period"):
        o.append("**" + M["period"] + "**: " + str(nn["period"]))
    o += ["", "## " + M["verdict"], "", nn.get("headline", ""), ""]
    if nn.get("subline"):
        o += [nn["subline"], ""]

    if sp:
        def pc(v):
            return "-" if v is None else "%.2f%%" % (v * 100)
        o += ["## " + M["position"], "",
              "| %s | %s | %s | %s |" % (M["metric"], M["you"], M["market"], M["share"]), "|---|---|---|---|",
              "| %s | - | - | %s |" % (M["impr"], pc(sp.get("impression_share"))),
              "| %s | - | - | %s |" % (M["clicks"], pc(sp.get("click_share"))),
              "| %s | %s | %s | %s |" % (M["purch"], format(sp.get("brand_purchases") or 0, ",.0f"),
                                         format(sp.get("market_purchases") or 0, ",.0f"),
                                         pc(sp.get("purchase_share"))),
              "| %s | %s | %s | x%.2f |" % (M["cvr"], pc(sp.get("cvr_brand")), pc(sp.get("cvr_market")),
                                            sp.get("cvr_index") or 0),
              "",
              "%s: %s - %s: %s" % (M["searches"], format(sp.get("queries") or 0, ","),
                                   M["with_purch"], format(sp.get("queries_with_brand_purchases") or 0, ",")),
              ""]
    if tk.get("funnel"):
        o += [tk["funnel"], ""]

    if ff:
        o += ["## " + M["leaks"], "",
              "| %s | %s | %s |" % (M["stage"], M["orders"], M["basis"]), "|---|---|---|",
              "| %s | %.0f | %s |" % (M["conv_stage"], ff.get("lost_orders_conversion_stage") or 0, M["conv_basis"]),
              "| %s | %.0f | %s |" % (M["click_stage"], ff.get("lost_orders_click_stage") or 0, M["click_basis"]), ""]
        if ff.get("top10_share_of_loss"):
            o += [M["top10"].format(pct=ff["top10_share_of_loss"] * 100), ""]
        if tk.get("leaks"):
            o += [tk["leaks"], ""]

    if q:
        o += ["## " + M["groups"], "", "| %s | %s | %s |" % (M["group"], M["n"], M["sh"]), "|---|---|---|"]
        for k in ("fix_or_cut", "defend", "fix_listing_risk", "insufficient_sample"):
            if k in q:
                sh = qs.get(k)
                o.append("| %s | %s | %s |" % (M["g_" + k], format(q[k], ","),
                                               ("%.1f%%" % (sh * 100)) if sh is not None else "-"))
        o.append("")
        if tk.get("portfolio"):
            o += [tk["portfolio"], ""]

    aba = s.get("aba") or {}
    if aba.get("status") == "INCLUDED":
        o += ["## " + M["aba"], "",
              M["aba_cov"].format(r=aba.get("rows_with_aba", 0), t=aba.get("rows_total", 0),
                                  q=aba.get("queries_with_aba", 0), w=len(aba.get("weeks") or [])), ""]
        if aba.get("bands"):
            o += ["| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                      M["aba_band"], M["aba_q"], M["aba_mcvr"], M["aba_impr"], M["aba_clk"],
                      M["aba_pur"], M["aba_cvr"], M["aba_share"]),
                  "|---|---|---|---|---|---|---|---|"]
            for b in aba["bands"]:
                # same formatting as the HTML (pct_raw): the two deliverables must print
                # the same figure, not the same number at different precision
                f = lambda v, suf="": "-" if v is None else (("%.2f%s" % (float(v), suf)) if suf else "%s" % v)
                o.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    b["band"], format(b["queries"], ","), f(b["market_cvr"], "%"),
                    format(b["brand_impressions"], ","), format(b["brand_clicks"], ","),
                    format(b["brand_purchases"], ","), f(b["brand_cvr"], "%"), f(b["purchase_share"], "%")))
            o.append("")
        tr = aba.get("rank_trend") or {}
        if tr:
            o += [M["aba_trend"].format(up=tr.get("up", 0), down=tr.get("down", 0),
                                        stable=tr.get("stable", 0)), ""]
        cc = aba.get("concentration") or {}
        if cc:
            o += [M["aba_conc"].format(v=cc.get("median_top3_click_share"),
                                       n=cc.get("queries_over_50pct", 0), q=cc.get("queries", 0)), ""]
        ta = aba.get("top_asins") or {}
        if ta.get("rows"):
            o += [M["aba_own"].format(n=len(ta["rows"]),
                                      own="" if ta.get("own_asin_list_given") else M["aba_own_unverified"]), ""]
    elif aba.get("status") == "NOT_RETURNED":
        o += ["## " + M["aba"], "", M["aba_none"], ""]

    acts = nn.get("actions") or []
    if acts:
        o += ["## " + M["actions"], "",
              "| # | %s | %s | %s | %s | %s | %s |" % (M["action"], M["why"], M["owner"], M["impact"],
                                                       M["where"], M["measure"]),
              "|---|---|---|---|---|---|---|"]
        for i, x in enumerate(acts, 1):
            o.append("| %d | %s | %s | %s | %s | %s | %s |" % (
                i, _cell(x.get("action", "")), _cell(x.get("why", "")), _cell(x.get("owner", "")),
                _cell(x.get("impact", "-")), _cell(x.get("where", "-")), _cell(x.get("measure", "-"))))
        o.append("")

    lim = list(nn.get("limits") or [])
    for extra in (s.get("notes") or []):
        if extra not in lim:
            lim.append(extra)
    if lim:
        o += ["## " + M["limits"], ""] + ["- " + str(x) for x in lim] + [""]
    o += ["---", "", M["src"]]
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--narrative", required=True)
    ap.add_argument("--template", default="health", choices=["health"])
    ap.add_argument("--brand", default="sparkx", choices=["sparkx", "none"])
    ap.add_argument("--out", default=".",
                    help="output DIRECTORY: writes sqp_report.md (the default deliverable) and sqp_report.html. "
                         "A path ending in .html or .md writes only that one file.")
    ap.add_argument("--lang", default="en", choices=[c for c, _ in LANGS],
                    help="language the report is written and opened in; must match the narrative you wrote")
    ap.add_argument("--ads", help="JSON rows from get_ads_perf factEntity=searchTerm for the same weeks")
    ap.add_argument("--baseline-roas", type=float, help="store ROAS for the same weeks and ad type")
    ap.add_argument("--products", help="JSON rows: parent_asin, name, TotalSalesAmount, ROAS, children (same weeks)")
    ap.add_argument("--store-ads", help="JSON: store Sponsored Products Sales and Conversions for the same weeks (dollar estimate)")
    ap.add_argument("--names", help="JSON: {asin: {name, price}} short product names (get_entity_metadata titles)")
    ap.add_argument("--actions-csv", help="sqp_actions.csv from sqp_calc.py: embedded as a download")
    ap.add_argument("--plan", help="plan.json from sqp_plan.py: shown as 'changes to confirm' (confirmed in chat)")
    ap.add_argument("--segment-ads", help="JSON: {own_brand|competitor_brand|generic: {Clicks, Spend, Sales, Conversions, CPC, ROAS}} search-term ad totals")
    a = ap.parse_args()

    def load(p):
        if not p:
            return None
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return d.get("data", {}).get("rows", []) if isinstance(d, dict) else d

    s, n = json.load(open(a.summary, encoding="utf-8")), json.load(open(a.narrative, encoding="utf-8"))
    sa = json.load(open(a.store_ads, encoding="utf-8")) if a.store_ads else None
    nm = json.load(open(a.names, encoding="utf-8")) if a.names else None
    sg = json.load(open(a.segment_ads, encoding="utf-8")) if a.segment_ads else None
    plan = json.load(open(a.plan, encoding="utf-8")) if a.plan else None
    html_doc = render_health(s, n, a.brand, load(a.ads), a.baseline_roas, load(a.products), sa, nm, a.actions_csv,
                             sg, plan, open_lang=a.lang)
    md_doc = render_md(s, n, a.lang)
    low = a.out.lower()
    written = []
    if low.endswith(".html"):
        open(a.out, "w", encoding="utf-8").write(html_doc); written = [a.out]
    elif low.endswith(".md"):
        open(a.out, "w", encoding="utf-8").write(md_doc); written = [a.out]
    else:
        os.makedirs(a.out, exist_ok=True)
        for name, doc in (("sqp_report.md", md_doc), ("sqp_report.html", html_doc)):
            fp = os.path.join(a.out, name)
            open(fp, "w", encoding="utf-8").write(doc)
            written.append(fp)
    print(", ".join(written))


if __name__ == "__main__":
    main()
