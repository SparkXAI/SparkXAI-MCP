# 部分指标不适用于所有广告类型的特别说明

## 总体原则

一批需要查询的指标中，有的适用于所有广告类型/定向类型，有的只适用于一部分，则应该按适用情况拆分查询。查询和计算这些指标时，如涉及基础指标（click/impression/order/sales/conversion 等）作为分子或分母，也需要限制为对应的广告类型范围。

---

## 按广告类型（campaignType）区分的指标

### 新客指标（NTB）— 不适用于 SP（sponsoredProducts）

| 指标 | 说明 |
|------|------|
| NTBOrders / NTB Orders | 新客订单数 |
| NTBUnits / NTB Units | 新客销量 |
| NTBSales / NTB Sales | 新客销售额 |
| NTBOrdersRate / % of NTB Orders | 新客订单占比 |
| NTBUnitsRate / % of NTB Units | 新客销量占比 |
| NTBSalesRate / % of NTB Sales | 新客销售额占比 |

⚠️ 计算 NTB 占比指标时，分子分母的 Orders/Units/Sales 都应该限制为 non-SP only（仅 sponsoredBrands 和 sponsoredDisplay）。

---

### 视频指标（Video）— 不适用于 SP（sponsoredProducts）

| 指标 | 说明 |
|------|------|
| VideoUnmutes | 视频取消静音数 |
| VideoFirstQuartileViews | 视频播放25% |
| VideoMidpointViews | 视频播放50% |
| VideoThirdQuartileViews | 视频播放75% |
| VideoCompleteViews | 视频播放100% |
| Video5SecondViews | 播放5秒或完成数 |
| Video5SecondViewRate | 播放5秒或完成数占比 |
| VTR | 视频浏览率 |
| vCTR | 视频浏览点击率 |

---

### 展示型指标（Display）— 不适用于 SP（sponsoredProducts）

| 指标 | 说明 |
|------|------|
| DPV | 商品详情页浏览次数（= DPVClick + DPVvCPM） |
| DPVR | 商品详情页浏览率。计算逻辑：`sum(DPV) / sum(nsp_impression)`，查询计算时需限制 campaignType 不为 SP |
| ViewableImpressions | 可见曝光量（广告进入用户可视区域的次数，所有广告类型均有） |
| ViewableImpressionsRate | 可见曝光率 |
| vCPM | 千次可见曝光成本 |
| ViewImpressions | vCPM 展示量（⚠️ 仅 SD vCPM 广告有，用于计算 vCPM = Spend / ViewImpressions × 1000） |

⚠️ 注意区分：
- **ViewableImpressions**（可见展示量）：所有广告类型均有
- **ViewImpressions**（vCPM 展示量）：仅 SD vCPM 广告有

---

### vCPM/Click 归因指标 — 不适用于 SP（sponsoredProducts）

支持的事实实体：campaign / adGroup / target / searchTerm / productAd
不支持：placement、asin

| 指标 | 说明 |
|------|------|
| DPVClick / DPV(Click) | 商品详情页浏览次数(Click归因) |
| DPVvCPM / DPV(vCPM) | 商品详情页浏览次数(vCPM归因) |
| OrdersClick / Orders(Click) | 订单数(Click归因) |
| UnitsClick / Units(Click) | 销量(Click归因) |
| SalesClick / Sales(Click) | 销售额(Click归因) |
| OrdersvCPM / Orders(vCPM) | 订单数(vCPM归因) |
| UnitsvCPM / Units(vCPM) | 销量(vCPM归因) |
| SalesvCPM / Sales(vCPM) | 销售额(vCPM归因) |

---

## 按事实实体区分的指标

### AI 专属指标 — 仅 campaign 事实实体支持

| 指标 | 说明 |
|------|------|
| AISpend | AI花费 |
| AISales | AI销售额（AI花费>0时计入） |
| AIACOS | AI ACOS |
| AIROAS | AI ROAS |

---

### 搜索顶部份额 — 仅 campaign、target 事实实体支持

| 指标 | 说明 |
|------|------|
| TopOfSearchIS | 搜索结果顶部展示份额（取 max，非 sum） |

---

### asin 独有指标 — 仅 asin 事实实体支持

TotalSalesAmount、OrderCount、Sessions、PageViews、TACOS、UnitSessionPercentage、BuyBoxPercentage、ShippedRevenue、ShippedUnits、GlanceViews、OrganicSales、OrganicOrders 等业务指标只属于 asin 事实表，不可与 productAd 或其他广告实体混用。

⚠️ asin 自有指标禁止与 Campaign/AdGroup/aiGroup 做任何形式的关联（包括聚合和过滤），否则 JOIN 会产生重复行导致结果虚高。

---

## 按维度实体区分的约束

### productAd 维度 — 仅适用于 SP（sponsoredProducts）广告类型

推广商品（productAd）维度只对 sponsoredProducts (SP) 广告类型适用，查询相关此维度字段时应对广告类型设置 filter 限制为 SP。

---

## 查询拆分规则

当一批需要查询的指标中，有的适用于所有广告类型，有的只适用于部分广告类型时，必须按适用情况拆分为多个查询任务：

1. 基础广告指标（Impressions、Clicks、Spend、Sales、ACOS 等）→ 适用于所有广告类型，可以不限 campaignType
2. NTB/视频/展示型/vCPM归因指标 → 需限制 campaignType 为 non-SP（sponsoredBrands 和 sponsoredDisplay）
3. AI专属指标 → 仅 campaign 事实实体
4. TopOfSearchIS → 仅 campaign 和 target 事实实体
5. asin 业务指标 → 仅 asin 事实实体，且禁止与广告层级关联
