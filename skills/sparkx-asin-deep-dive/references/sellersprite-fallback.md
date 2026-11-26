# When SellerSprite Is Not Connected

Use the platform's SQP / ABA, eligible brand peer benchmark and current competitorProduct report
first. When SellerSprite is absent, use this reference only for questions those sources cannot
answer. **Leaving a section empty is unacceptable** when account data supports a narrower answer.

Every substituted section must carry two labels: **which path produced it**, and **what that path
cannot answer**. A reader who is not told will take the fallback for the full version.

## The probe

Detect by calling, not by reading a tool list — a tool name can be present while the account has no
entitlement. One cheap SellerSprite call against the target ASIN and marketplace. Data back means
connected. An error, an empty body or no such tool means not connected.

Offer once, in one sentence, and move on. Do not re-ask mid-report.

## 1. 市场位置

| | |
|---|---|
| **Full path** | Category price bands, rating and review distribution, listing quality, same-brand cannibalisation |
| **Substitute** | `asinPrice`, `asinBsr`, `asinBrand` from `get_entity_metadata` (`entity=asin`) |
| **Reframed question** | Not "how does this price compare to the category" but **"where does this product sit on price and rank among the products this account sells"** |

Rank this ASIN's price and BSR against the account's own catalogue, and against its siblings under
the same parent. A product priced at the top of its own brand's range with a BSR behind its
siblings is a finding you can make without any external data.

**This substitute alone cannot answer** category price distribution, rating, review count or
listing quality. The separate `competitorProduct` read may supply price, stars and review count
for up to 60 recommended competitors per report type, if the report and permission are available.
Do not turn that limited list into a category distribution. BSR is a rank within a category whose
size is unknown here, so treat it as direction over time, not as market share.

## 2. 竞品

| | |
|---|---|
| **Full path** | Head-to-head comparison against same-tier competitors, interception and defence opportunities |
| **Substitute** | `get_ads_perf` at `factEntity=target` with **`queryType: product`** (that parameter is what selects product targeting — `targetType` is not a selectable dimension), over this ASIN's ad groups |
| **Reframed question** | Not "how do competitors compare to us" but **"which competitor ASINs is this account paying to target, and does that spend pay back"** |

This is the substitution with the most value in it, because it is about money already spent. For
each competitor ASIN being targeted: spend, clicks, conversions, sales and ACOS, over both windows.
Three findings come out of it directly:

- Competitor targets taking spend with no conversions — a candidate list for the customer to review
- Competitor targets that convert well — where interception is working, and worth more budget
- The account's **own** ASINs appearing as product targets — self-competition, and almost always
  unintentional

**This product-target path cannot answer** the competitor's price, stars, review count, sales
volume or ranking. The separate `competitorProduct` report can add price, stars and review count
for its returned products, but not sales volume or a complete ranking. Label each source.

## 3. 流量结构

| | |
|---|---|
| **Full path** | Organic vs ad share, core keyword organic rank, entrance concentration, traffic-collapse attribution |
| **Substitute** | `TACOS`, `TotalSalesAmount`, `Sessions` at `factEntity=asin`, plus `searchTerm` rows for concentration |
| **Reframed question** | Mostly the same question. **`TACOS` is ad spend over total sales, so ad dependence falls straight out of it** — no external data needed |

- **Ad dependence**: `TACOS` across both windows. Rising TACOS with flat total sales means the
  business is buying the same revenue at a higher cost
- **Ad share of sales**: ad-attributed sales over `TotalSalesAmount`. A rising share shows greater
  reliance on ad-attributed sales; attribution differences mean it does not prove organic sales fell
- **Entrance concentration**: Top1 / Top2 / Top5 search terms' share of orders, sales and spend.
  Concentration is not itself a problem — it is a *risk measure*, and it matters most when the top
  entrance is also the one whose efficiency is falling
- **Sessions vs clicks**: a drop in `Sessions` with steady ad clicks points outside advertising

**Cannot answer**: organic keyword rank itself — say it plainly, because "自然排名掉了" is the most
common explanation offered for a traffic decline and this path cannot confirm it.

### 流量塌方：仍然有清单可走，不是耸肩

按顺序逐步走，每步记录数据源和结论。其中两步只用 SparkX 数据，所以即便没有卖家精灵，替代口径也能把答案收窄。

| 步骤 | 需要 | 能得到的结论 |
|---|---|---|
| **断货** | SparkX `entity=asin` 的可售件数与库存覆盖 | 主力变体健康 → 排除。边缘变体断货要注明它占多少销量 |
| **广告掩盖** | SparkX 两期花费、广告归因销售占比与总销售额 | 花费和广告归因占比先升、总销售额后弱，提示广告可能掩盖下滑；单凭该模式不能证明自然销量下降 |
| 价格 | 两期的 Buy Box 价格 | 价格相同 → 排除 |
| Listing 压制 | Buy Box 归属与促销状态 | 正常 → 排除 |
| 搜索词需求变化 | 已知**泛词与细分词**的 SQP 周市场量 | 泛词下降而细分词稳定，提示词级需求变化；不能据此断定整个类目进入季节性下滑 |
| 排名螺旋 | 自然占比与排名跌幅 vs 类目需求 | 自然分跌幅显著大于大盘 → 份额丢失 |

没有卖家精灵时，覆盖到的已知搜索词仍可用平台的 SQP 周搜索量核对市场变化。其他步骤按各自数据可用性执行；无法验证的机制保持待核，不写成已排除。

### 业务数字里的一个坑

`TotalSalesAmount ÷ OrderCount` 是**每单金额**，不是每件单价。它含一单多件和跨变体的价格 mix。凡出现必须标注是「每单」口径；要每件单价得用实际成交价，拿除法推出来的只是代理指标，必须标明。

## What the fallback report should say about itself

One block, near the top, not buried at the end:

> 市场与竞品部分先使用覆盖到的平台 SQP / ABA 与竞品推荐列表，再用店内价格、BSR 和竞品定向数据补足。
> 推荐列表只是有限的当前结果，不代表整个类目。关键词自然排名和更广的类目比较，缺少卖家精灵时仍待核。

Say it once. Repeating it in every section turns a caveat into noise.
