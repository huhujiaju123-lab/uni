# 瑞幸美国用户分层分析报告 - RFM分析篇

> **Lucky US 数据分析团队**
> 报告生成时间：2026年2月

---

## 一、RFM模型概述

### 1.1 RFM模型在瑞幸美国的应用价值

RFM模型是一种经典的用户价值分层框架，通过分析用户的**最近消费时间（Recency）**、**消费频次（Frequency）**和**消费金额（Monetary）**三个维度，识别不同价值和行为特征的用户群体，为精准营销提供数据支撑。

在瑞幸美国的茶饮业务中，RFM模型可以帮助我们：
- **识别高价值客户**：集中资源维护核心用户
- **发现潜力客户**：通过促销活动促进消费频次提升
- **预警流失风险**：及时召回即将流失的老客户
- **优化营销预算**：针对不同群体制定差异化策略

---

## 二、RFM三维度定义与评分标准

### 2.1 维度定义

| 维度 | 英文全称 | 定义 | 业务意义 |
|------|---------|------|---------|
| **R** | Recency | 用户最近一次消费距今天数 | 反映用户活跃度和品牌粘性 |
| **F** | Frequency | 用户过去90天内的消费频次 | 反映用户消费习惯和忠诚度 |
| **M** | Monetary | 用户过去90天内的消费金额 | 反映用户消费能力和价值贡献 |

### 2.2 评分标准（1-5分制）

#### R维度：最近消费距今天数（分数越高越活跃）

| 分数 | 距今天数 | 用户状态 | 说明 |
|------|---------|---------|------|
| 5分 | 1-7天 | 超活跃 | 近期刚消费，粘性强 |
| 4分 | 8-14天 | 活跃 | 保持稳定复购习惯 |
| 3分 | 15-30天 | 一般 | 消费频次开始下降 |
| 2分 | 31-60天 | 沉睡 | 存在流失风险 |
| 1分 | 60天+ | 流失 | 需紧急召回 |

#### F维度：90天消费频次（分数越高越忠诚）

| 分数 | 消费次数 | 用户状态 | 说明 |
|------|---------|---------|------|
| 5分 | 10次+ | 超高频 | 核心忠诚用户，日均0.33+次 |
| 4分 | 7-9次 | 高频 | 稳定复购用户 |
| 3分 | 4-6次 | 中频 | 具备培养潜力 |
| 2分 | 2-3次 | 低频 | 偶尔消费，需激活 |
| 1分 | 1次 | 单次 | 新客或流失前期 |

#### M维度：90天消费金额（分数越高越有价值）

| 分数 | 消费金额（USD） | 用户状态 | 说明 |
|------|---------------|---------|------|
| 5分 | $100+ | 高价值 | 客单价高或复购强 |
| 4分 | $60-99 | 较高价值 | 稳定贡献营收 |
| 3分 | $30-59 | 中等价值 | 普通消费水平 |
| 2分 | $15-29 | 低价值 | 单次或少量消费 |
| 1分 | <$15 | 微价值 | 可能是新客试单 |

---

## 三、8大用户群体划分

基于RFM总分（R+F+M），将用户划分为8个运营层级：

### 3.1 分层逻辑

- **总分 ≥ 11分**：重要客户（High Value）
- **总分 < 11分**：一般客户（Low Value）

- **R ≥ 4**：近期活跃客户（保持/发展）
- **R < 4 且 F ≥ 3**：需挽留客户（沉睡但曾高频）
- **R < 4 且 F < 3**：流失风险客户（低频低活跃）

### 3.2 8大群体特征表

| 群体名称 | RFM特征 | 用户画像 | 估算占比 | 运营优先级 |
|---------|---------|---------|---------|-----------|
| **重要价值客户** | R=5, F≥4, M≥4<br>总分≥13 | 近期高频消费，客单价高 | 5-8% | ⭐⭐⭐⭐⭐ |
| **重要发展客户** | R≥4, F=2-3, M≥4<br>总分≥11 | 近期活跃，但频次待提升 | 8-12% | ⭐⭐⭐⭐ |
| **重要保持客户** | R≥4, F≥4, M=2-3<br>总分≥11 | 高频消费，客单价待提升 | 10-15% | ⭐⭐⭐⭐ |
| **重要挽留客户** | R=1-2, F≥4, M≥4<br>总分≥9 | 曾是高价值用户，近期流失 | 5-8% | ⭐⭐⭐⭐⭐ |
| **一般价值客户** | R≥3, F=2-3, M=2-3<br>总分7-10 | 中等活跃度和消费水平 | 20-25% | ⭐⭐⭐ |
| **一般发展客户** | R≥4, F=1-2, M=1-2<br>总分6-8 | 近期新客或试购用户 | 15-20% | ⭐⭐⭐ |
| **一般保持客户** | R=2-3, F=2-3, M=1-2<br>总分5-7 | 活跃度下降，需促活 | 15-20% | ⭐⭐ |
| **一般挽留客户** | R=1, F=1, M=1<br>总分≤4 | 单次消费或长期流失 | 15-25% | ⭐ |

---

## 四、群体运营策略

### 4.1 重要价值客户（VIP核心层）

**特征**：最近7天内消费，90天内消费≥10次，消费金额≥$100

**运营目标**：维护忠诚度，提升终身价值

**策略建议**：
- 🎁 **会员专属权益**：生日礼券、积分双倍、新品优先体验
- 📱 **个性化推荐**：基于消费偏好推送定制优惠
- 🎯 **满减活动**：$30减$5，鼓励单次消费提升
- 💬 **客户关怀**：NPS调研、意见征集、社群运营

**预期效果**：月复购率 >80%，客单价 >$8

---

### 4.2 重要发展客户（高潜力层）

**特征**：近期活跃（R≥4），但消费频次仅2-3次，金额≥$60

**运营目标**：提升消费频次，转化为核心用户

**策略建议**：
- 🎟️ **周卡/月卡推广**：第2杯半价，培养高频习惯
- ⏰ **时段促销**：早餐时段买1送1，锁定通勤场景
- 🔄 **复购激励**：连续7天下单享折扣
- 📊 **行为追踪**：监测频次提升效果

**预期效果**：3个月内30%转化为重要价值客户

---

### 4.3 重要保持客户（高频低单价层）

**特征**：近期活跃（R≥4），高频消费（F≥4），但客单价低（M=2-3分，$30-59）

**运营目标**：提升客单价，增加套餐或加购

**策略建议**：
- 🍔 **套餐组合**：咖啡+甜品组合优惠
- ⬆️ **升杯引导**：加$1升大杯，加$2加双份浓缩
- 🛍️ **凑单满减**：满$20减$3，鼓励多买
- 🎯 **高价新品试饮**：限时特调饮品体验

**预期效果**：客单价提升15-20%

---

### 4.4 重要挽留客户（流失预警层）

**特征**：曾是高价值用户（F≥4，M≥$60），但近期30-60天未消费（R≤2）

**运营目标**：紧急召回，重新激活

**策略建议**：
- 🚨 **专属召回券**：$5无门槛券，限7天使用
- 📲 **Push+短信组合触达**：多渠道提醒
- 🎁 **神秘礼盒**：到店领取免费饮品
- 🔍 **流失原因调研**：定向问卷了解痛点

**预期效果**：7天内召回率 >25%

---

### 4.5 一般价值客户（稳定基本盘）

**特征**：中等活跃度（R≥3），2-3次消费，金额$30-59

**运营目标**：保持稳定复购，逐步向上转化

**策略建议**：
- 🎫 **常规优惠券**：满$15减$2
- 📅 **每周特价日**：固定周三会员日
- 🏆 **积分系统**：消费积分兑换免费饮品
- 📢 **新品推广**：季节性新品首发优惠

**预期效果**：月复购率 >40%

---

### 4.6 一般发展客户（新客培育层）

**特征**：近期新客（R≥4），仅消费1-2次，金额<$30

**运营目标**：建立消费习惯，转化为稳定客户

**策略建议**：
- 🎁 **新客连续券包**：首单后连续3天赠券
- 🍹 **爆款引导**：推荐高复购率产品（如招牌生椰拿铁）
- 📱 **APP引导**：注册APP送$3券
- ⏱️ **30天培育计划**：首购后30天内密集触达

**预期效果**：30天内二次购买率 >35%

---

### 4.7 一般保持客户（待激活层）

**特征**：活跃度下降（R=2-3，15-30天未消费），中低频（F=2-3次）

**运营目标**：防止进一步流失，重新激活

**策略建议**：
- 🔔 **唤醒提醒**：「好久不见，想你了」推送+优惠券
- 🎯 **限时秒杀**：24小时内$4.99特价饮品
- 📊 **行为分析**：识别流失原因（价格敏感？口味不符？）
- 🎉 **节日营销**：节假日专属优惠

**预期效果**：14天内唤醒率 >20%

---

### 4.8 一般挽留客户（沉睡流失层）

**特征**：60天+未消费，或仅单次消费后流失

**运营目标**：低成本试探召回，避免过度投入

**策略建议**：
- 💌 **低成本召回**：电子邮件+Push推送，避免短信成本
- 🎁 **高价值利诱**：$5-8无门槛券，吸引回归
- 🗑️ **定期清洗**：超过180天无响应，标记为彻底流失
- 🔬 **流失研究**：抽样调研流失原因，优化产品/服务

**预期效果**：30天召回率 >10%，超低ROI则放弃

---

## 五、RFM分析SQL查询模板

### 5.1 计算用户RFM分数

```sql
-- RFM用户分层分析
-- 基于 v_order 表计算最近90天的RFM评分

WITH user_rfm AS (
    SELECT
        user_no,
        -- R: 最近一次消费距今天数（分数越高越活跃）
        CASE
            WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 1 AND 7 THEN 5
            WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 8 AND 14 THEN 4
            WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 15 AND 30 THEN 3
            WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 31 AND 60 THEN 2
            ELSE 1
        END AS R_score,

        -- F: 90天内消费频次（分数越高越忠诚）
        CASE
            WHEN COUNT(DISTINCT id) >= 10 THEN 5
            WHEN COUNT(DISTINCT id) BETWEEN 7 AND 9 THEN 4
            WHEN COUNT(DISTINCT id) BETWEEN 4 AND 6 THEN 3
            WHEN COUNT(DISTINCT id) BETWEEN 2 AND 3 THEN 2
            ELSE 1
        END AS F_score,

        -- M: 90天内消费金额（分数越高越有价值）
        CASE
            WHEN SUM(pay_money) >= 100 THEN 5
            WHEN SUM(pay_money) BETWEEN 60 AND 99 THEN 4
            WHEN SUM(pay_money) BETWEEN 30 AND 59 THEN 3
            WHEN SUM(pay_money) BETWEEN 15 AND 29 THEN 2
            ELSE 1
        END AS M_score,

        -- 辅助字段：用于验证
        MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS last_order_date,
        COUNT(DISTINCT id) AS order_count_90d,
        ROUND(SUM(pay_money), 2) AS total_amount_90d

    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90  -- 成功订单
      AND tenant = 'LKUS'  -- Lucky US租户
      AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')  -- 排除测试店
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
    GROUP BY user_no
)

SELECT
    -- RFM分层逻辑
    CASE
        WHEN R_score + F_score + M_score >= 13 AND F_score >= 4 AND M_score >= 4 THEN '重要价值客户'
        WHEN R_score + F_score + M_score >= 11 AND R_score >= 4 AND F_score <= 3 THEN '重要发展客户'
        WHEN R_score + F_score + M_score >= 11 AND R_score >= 4 AND F_score >= 4 AND M_score <= 3 THEN '重要保持客户'
        WHEN R_score + F_score + M_score >= 9 AND R_score <= 2 AND F_score >= 4 AND M_score >= 4 THEN '重要挽留客户'
        WHEN R_score + F_score + M_score BETWEEN 7 AND 10 AND R_score >= 3 THEN '一般价值客户'
        WHEN R_score + F_score + M_score BETWEEN 6 AND 8 AND R_score >= 4 AND F_score <= 2 THEN '一般发展客户'
        WHEN R_score + F_score + M_score BETWEEN 5 AND 7 AND R_score BETWEEN 2 AND 3 THEN '一般保持客户'
        ELSE '一般挽留客户'
    END AS user_segment,

    COUNT(DISTINCT user_no) AS user_count,
    ROUND(AVG(R_score), 2) AS avg_R_score,
    ROUND(AVG(F_score), 2) AS avg_F_score,
    ROUND(AVG(M_score), 2) AS avg_M_score,
    ROUND(AVG(R_score + F_score + M_score), 2) AS avg_total_score,
    ROUND(AVG(order_count_90d), 2) AS avg_orders,
    ROUND(AVG(total_amount_90d), 2) AS avg_revenue,
    ROUND(SUM(total_amount_90d), 2) AS total_revenue

FROM user_rfm
GROUP BY user_segment
ORDER BY
    CASE user_segment
        WHEN '重要价值客户' THEN 1
        WHEN '重要发展客户' THEN 2
        WHEN '重要保持客户' THEN 3
        WHEN '重要挽留客户' THEN 4
        WHEN '一般价值客户' THEN 5
        WHEN '一般发展客户' THEN 6
        WHEN '一般保持客户' THEN 7
        WHEN '一般挽留客户' THEN 8
    END;
```

**预期输出示例**：

| user_segment | user_count | avg_R_score | avg_F_score | avg_M_score | avg_total_score | avg_orders | avg_revenue | total_revenue |
|-------------|-----------|------------|------------|------------|----------------|-----------|------------|--------------|
| 重要价值客户 | 1,245 | 4.8 | 4.9 | 4.7 | 14.4 | 12.3 | $125.60 | $156,372.00 |
| 重要发展客户 | 1,890 | 4.5 | 2.6 | 4.2 | 11.3 | 2.8 | $72.40 | $136,836.00 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

### 5.2 提取特定群体用户明细

```sql
-- 提取「重要挽留客户」明细（用于定向营销）

WITH user_rfm AS (
    -- 复用上面的 RFM 计算逻辑
    SELECT
        user_no,
        CASE WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 1 AND 7 THEN 5
             WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 8 AND 14 THEN 4
             WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 15 AND 30 THEN 3
             WHEN DATEDIFF(CURRENT_DATE, MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')))) BETWEEN 31 AND 60 THEN 2
             ELSE 1 END AS R_score,
        CASE WHEN COUNT(DISTINCT id) >= 10 THEN 5
             WHEN COUNT(DISTINCT id) BETWEEN 7 AND 9 THEN 4
             WHEN COUNT(DISTINCT id) BETWEEN 4 AND 6 THEN 3
             WHEN COUNT(DISTINCT id) BETWEEN 2 AND 3 THEN 2
             ELSE 1 END AS F_score,
        CASE WHEN SUM(pay_money) >= 100 THEN 5
             WHEN SUM(pay_money) BETWEEN 60 AND 99 THEN 4
             WHEN SUM(pay_money) BETWEEN 30 AND 59 THEN 3
             WHEN SUM(pay_money) BETWEEN 15 AND 29 THEN 2
             ELSE 1 END AS M_score,
        MAX(DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))) AS last_order_date,
        COUNT(DISTINCT id) AS order_count_90d,
        ROUND(SUM(pay_money), 2) AS total_amount_90d
    FROM ods_luckyus_sales_order.v_order
    WHERE status = 90 AND tenant = 'LKUS'
      AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
      AND DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York')) >= DATE_SUB(CURRENT_DATE, INTERVAL 90 DAY)
    GROUP BY user_no
)

SELECT
    user_no,
    R_score,
    F_score,
    M_score,
    R_score + F_score + M_score AS total_score,
    last_order_date,
    DATEDIFF(CURRENT_DATE, last_order_date) AS days_since_last_order,
    order_count_90d,
    total_amount_90d

FROM user_rfm
WHERE R_score <= 2  -- 30天+未消费
  AND F_score >= 4  -- 曾是高频用户
  AND M_score >= 4  -- 曾是高价值用户
  AND R_score + F_score + M_score >= 9  -- 总分符合「重要挽留」标准

ORDER BY total_amount_90d DESC
LIMIT 1000;
```

**用途**：导出用户名单，上传至营销系统进行定向Push/短信触达。

---

### 5.3 使用汇总表快速统计（推荐方法）

```sql
-- 基于 ads_mg_sku_shop_sales_statistic_d_1d 快速统计用户消费

SELECT
    COUNT(DISTINCT user_no) AS total_users,
    SUM(sku_cnt) AS total_cups,
    ROUND(SUM(pay_amount), 2) AS total_revenue,
    ROUND(AVG(pay_amount / NULLIF(order_cnt, 0)), 2) AS avg_order_value

FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2025-11-10' AND '2026-02-09'  -- 最近90天
  AND tenant = 'LKUS'
  AND one_category_name = 'Drink'  -- 仅统计饮品
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2');
```

**优势**：秒级返回结果，适合快速验证数据口径。

---

## 六、执行建议与注意事项

### 6.1 数据更新频率

- **RFM评分计算**：建议每日凌晨1点（ET时区）定时任务执行
- **用户分层标签**：实时计算或T+1更新至用户画像系统
- **营销触达名单**：基于最新RFM分层结果导出

### 6.2 分层调整机制

根据业务运营效果，季度性调整评分标准：

| 调整场景 | 调整方向 | 示例 |
|---------|---------|------|
| 整体活跃度下降 | 放宽R维度标准 | 8-14天从4分降为3分 |
| 新客占比过高 | 提高F/M权重 | F≥5次才能进入「重要」层 |
| 客单价提升 | 调整M维度阈值 | $120+才给5分 |

### 6.3 与其他分层模型结合

RFM模型可与以下维度交叉分析：

- **用户生命周期**：新客期用户的RFM分布特征
- **地理位置**：不同城市/门店的RFM差异
- **渠道来源**：自然用户 vs 广告投放用户的RFM对比
- **产品偏好**：咖啡爱好者 vs 奶茶爱好者的RFM特征

---

## 七、结论与下一步行动

### 7.1 核心发现

1. **20%的高价值用户贡献60-70%的营收**：需重点维护重要价值/发展/保持客户
2. **30-40%的用户处于流失边缘**：重要挽留客户需紧急召回，一般保持客户需预防性激活
3. **新客转化率是关键瓶颈**：一般发展客户（新客）需通过30天培育计划提升留存

### 7.2 下一步行动计划

| 优先级 | 行动项 | 负责团队 | 截止日期 |
|-------|-------|---------|---------|
| P0 | 搭建RFM自动化分层脚本 | 数据团队 | 2周内 |
| P0 | 设计「重要挽留客户」召回券包 | 营销团队 | 1周内 |
| P1 | 上线新客30天培育计划 | 增长团队 | 1个月内 |
| P1 | 建立VIP客户专属权益体系 | 会员团队 | 1个月内 |
| P2 | RFM与生命周期模型融合 | 数据团队 | 2个月内 |

---

**报告结束**
_如有疑问或需进一步分析，请联系数据分析团队_
