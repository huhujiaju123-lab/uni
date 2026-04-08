# Lucky US 数据分析知识库

> 基于 470 份生产 SQL 系统学习，2026-03-04 整理
> 适用角色：数据分析师 / 增长运营 / BI 开发

---

## 一、业务全景

### 1.1 公司概况

Lucky US（瑞幸美国）是一家面向美国市场的连锁茶饮品牌。主要业务形态：
- **门店自取（Pickup）**：用户通过 APP 下单，到店取餐
- **外卖配送（Delivery）**：通过 DoorDash / Grubhub / UberEats 第三方平台配送
- **裂变获客**：分享有礼（Share The Luck）邀请好友

### 1.2 核心业务指标体系

```
                        ┌─────────────────┐
                        │    GMV / 销售额   │
                        └───────┬─────────┘
                  ┌─────────────┼─────────────┐
                  ▼             ▼             ▼
           ┌──────────┐  ┌──────────┐  ┌──────────┐
           │  杯量     │  │ 单杯实收  │  │  门店数   │
           └────┬─────┘  └──────────┘  └──────────┘
          ┌─────┼─────┐
          ▼     ▼     ▼
       ┌─────┐┌─────┐┌───────┐
       │ 新客 ││ 老客 ││ 多杯率 │
       └──┬──┘└──┬──┘└───────┘
          │      │
    ┌─────┘  ┌───┘
    ▼        ▼
 ┌──────┐ ┌──────┐
 │ 留存率││ 复购率│
 └──────┘ └──────┘
```

### 1.3 用户生命周期

```
注册 → 首单转化 → 复购激活 → 频次提升 → 多杯消费 → 忠诚用户
 │        │          │          │         │          │
 └ t_user └ v_order  └ D3/D7   └ 周/月   └ 多杯率   └ R0_active
           (首单)      复购率     复购表              (RFM)
```

---

## 二、数据架构

### 2.1 分层架构

```
┌────────────────────────────────────────────────────────┐
│  ADS 应用层    ads_*                    ⚡ 秒级响应      │
│  ─ 预聚合宽表，面向特定分析场景                           │
│  ─ 门店日销售、周/月复购、人群标签、触达权限               │
├────────────────────────────────────────────────────────┤
│  DWS/DWD 汇总层    dws_* / dwd_*       ⚡ 秒级响应      │
│  ─ 中间聚合层，按主题域组织                               │
│  ─ 页面日志汇总、推送记录、券使用记录                      │
├────────────────────────────────────────────────────────┤
│  DIM 维度层    dim_*                    ⚡ 秒级响应      │
│  ─ 门店、商品等缓慢变化维度                               │
├────────────────────────────────────────────────────────┤
│  ODS 原始层    ods_*                    🐢 视数据量而定   │
│  ─ 业务系统原始数据镜像                                   │
│  ─ 订单、用户、券、邀请、埋点                              │
└────────────────────────────────────────────────────────┘
```

### 2.2 选表决策矩阵

| 我需要 | 首选表 | 备选表 | 禁忌 |
|--------|--------|--------|------|
| 门店每日杯量/销售额 | `ads_mg_sku_shop_sales_statistic_d_1d` | — | 不要用 t_order_item |
| 某个 SPU 的销量明细 | `ads_mg_sku_shop_sales_statistic_d_1d` | `t_order_item`(慢) | — |
| 用户周复购率 | `ads_user_order_rep_info_d_nw` | — | 不要自己算 |
| 用户月复购率 | `ads_user_order_rep_info_d_nm` | — | 不要自己算 |
| APP 页面漏斗 | `dws_mg_log_user_screen_name_d_1d` | — | — |
| 用户是否新客/老客 | `v_order` (首单日期CTE) | — | — |
| AB 实验人群 | `t_user_traffic_distribution` | `ads_marketing_t_user_group_d_his` | — |
| 券发放/核销 | `t_coupon_record` | `dwd_t_mkt_coupon_use_record_d_inc` | — |
| SMS/Push 触达效果 | `dwd_marketing_t_push_receipt_d_inc` | — | — |
| 分享邀请关系 | `t_user_invitation_info` | — | — |
| 订单级明细(客单价) | `v_order` | — | 避免 JOIN t_order_item |
| 杯级明细(单杯实收) | `t_order_item` | — | 避免与 v_order JOIN |
| 履约时效 | `v_order` + `t_order_make` | — | — |
| 用户注册信息 | `t_user` | — | — |
| 用户可触达性 | `ads_marketing_t_user_grant_d_his` | — | — |
| 埋点事件详情 | `v_hmonitor_track_event_rt` | — | 大表，加 dt 分区 |

---

## 三、表字段百科

### 3.1 dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
> 门店 × SKU × 日 销售汇总表。**日常分析首选表。**

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| dt | DATE | 统计日期 | 分区键，必须指定 |
| tenant | VARCHAR | 租户 | 过滤 `= 'LKUS'` |
| shop_name | VARCHAR | 门店名称 | 排除 'NJ Test Kitchen' 系列 |
| spu_name | VARCHAR | 商品名称 | 可 LIKE 做关键词匹配 |
| spu_code | VARCHAR | 商品编码 | — |
| one_category_name | VARCHAR | 一级类目 | 'Drink' = 饮品 |
| two_category_name | VARCHAR | 二级类目 | — |
| sku_cnt | INT | 杯量 | **每杯计 1**，非订单数 |
| order_cnt | INT | 订单数 | 含该 SKU 的订单去重数 |
| pay_amount | DECIMAL | 实付金额 | — |
| origin_amount | DECIMAL | 原价金额 | 用于算折扣深度 |

**常用 SQL**：
```sql
-- 全店汇总
SELECT dt, COUNT(DISTINCT shop_name) AS 门店数, SUM(sku_cnt) AS 杯量,
       ROUND(SUM(pay_amount), 2) AS 销售额,
       ROUND(SUM(pay_amount)/SUM(sku_cnt), 2) AS 单杯实收
FROM dw_ads.ads_mg_sku_shop_sales_statistic_d_1d
WHERE dt BETWEEN '2026-02-25' AND '2026-03-03'
  AND tenant = 'LKUS' AND one_category_name = 'Drink'
  AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')
GROUP BY dt ORDER BY dt;

-- 商品渗透率
SELECT dt, SUM(order_cnt) AS 总订单,
  SUM(CASE WHEN spu_name LIKE '%Coconut%' THEN order_cnt ELSE 0 END) AS Coconut订单
FROM ... GROUP BY dt;
```

---

### 3.2 ods_luckyus_sales_order.v_order
> 订单主表。每条记录 = 一笔订单。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| id | BIGINT | 订单ID | 主键 |
| user_no | VARCHAR | 用户编号 | 关联 t_user, t_order_item |
| shop_name | VARCHAR | 门店名称 | — |
| channel | INT | 下单渠道 | 见枚举表 |
| status | INT | 订单状态 | **90 = 成功**，只统计这个 |
| pay_money | DECIMAL | 实付金额 | 订单级，包含所有 item |
| create_time | DATETIME | 下单时间 | 系统时区，需 CONVERT_TZ |
| pay_time | DATETIME | 支付时间 | 用于履约时效起点 |
| tenant | VARCHAR | 租户 | 过滤 INSTR(tenant,'IQ')=0 |

**渠道枚举**：

| channel | 含义 | 分类 |
|---------|------|------|
| 1 | Android | Pickup |
| 2 | iOS | Pickup |
| 3 | H5 | Pickup |
| 4 | 自助下单机 | Pickup |
| 5 | Grab | Delivery |
| 6 | EPoint | Pickup |
| 8 | DoorDash | Delivery |
| 9 | Grubhub | Delivery |
| 10 | UberEats | Delivery |

```sql
-- Pickup vs Delivery
CASE WHEN channel IN (5, 8, 9, 10) THEN 'Delivery' ELSE 'Pickup' END
```

---

### 3.3 ods_luckyus_sales_order.t_order_item
> 订单明细表。每条记录 = 一个 SKU 行项。**大表，慎用。**

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| order_id | BIGINT | 订单ID | 关联 v_order.id |
| user_no | VARCHAR | 用户编号 | — |
| spu_name | VARCHAR | 商品名称 | — |
| spu_code | VARCHAR | 商品编码 | — |
| spu_type | INT | 商品类型 | 2 = 套餐 |
| one_category_name | VARCHAR | 一级类目 | 'Drink' |
| two_category_name | VARCHAR | 二级类目 | — |
| three_category_name | VARCHAR | 三级类目 | — |
| sku_name | VARCHAR | SKU名称 | 含规格信息 |
| sku_attributes | VARCHAR | SKU属性 | 温度/甜度/加料 |
| origin_price | DECIMAL | 原价 | **可能为 0**（赠品） |
| pay_money | DECIMAL | 实付金额 | **item 级**，用于算单杯实收 |
| refunded_money | DECIMAL | 退款金额 | — |
| sku_num | INT | 数量 | 通常 = 1，套餐可 > 1 |
| status | INT | 状态 | 同 v_order |
| tenant | VARCHAR | 租户 | — |
| create_time | DATETIME | 创建时间 | — |

**关键公式**：
```sql
-- 杯量（不是订单数！）
COUNT(*) AS cups  -- 每行 = 一杯

-- 单杯实收（用 item 级 pay_money）
SUM(pay_money) / SUM(sku_num) AS price_per_cup

-- 多杯判断
SUM(CASE WHEN one_category_name = 'Drink' THEN 1 ELSE 0 END) AS drink_cnt
-- drink_cnt >= 2 → 多杯用户
```

---

### 3.4 ods_luckyus_sales_crm.t_user
> 用户注册表。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| user_no | VARCHAR | 用户编号 | 全局唯一 |
| create_time | DATETIME | 注册时间 | 需 CONVERT_TZ |
| origin | VARCHAR | 来源 | — |
| type | INT | 用户类型 | **4=游客，5=外卖，需剔除** |
| tenant | VARCHAR | 租户 | — |

```sql
-- 分析时必须剔除
WHERE type NOT IN (4, 5)
```

---

### 3.5 ods_luckyus_sales_marketing.t_coupon_record
> 优惠券发放和核销表。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| member_no | VARCHAR | 用户编号 | 对应 v_order.user_no |
| activity_no | VARCHAR | 活动编号 | AB实验常用此字段区分组 |
| proposal_no | VARCHAR | 券方案编号 | — |
| coupon_name | VARCHAR | 券名称 | — |
| coupon_denomination | DECIMAL | 券面额 | — |
| use_status | INT | 使用状态 | **1 = 已使用** |
| coupon_status | INT | 券状态 | 2 = 已过期 |
| effective_begin_time | DATETIME | 生效时间 | — |
| expire_time | DATETIME | 过期时间 | — |
| use_time | DATETIME | 使用时间 | — |

```sql
-- 核销率
COUNT(CASE WHEN use_status = 1 THEN 1 END) / COUNT(*) AS redemption_rate

-- 同日核销率（衡量券激活速度）
COUNT(CASE WHEN DATE(use_time) = DATE(effective_begin_time) THEN 1 END) / COUNT(*) AS same_day_rate
```

---

### 3.6 dw_dws.dws_mg_log_user_screen_name_d_1d
> APP 页面访问日志汇总表。用于漏斗分析。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| dt | DATE | 统计日期 | 分区键 |
| user_no | VARCHAR | 用户编号 | — |
| screen_name | VARCHAR | 页面名称 | 见漏斗定义 |

**页面漏斗**：
```
home → menu → productdetail → confirmorder → orderdetail
首页     菜单     商品详情        确认订单       订单详情(支付成功)
```

```sql
SELECT dt,
  COUNT(DISTINCT CASE WHEN screen_name = 'menu' THEN user_no END) AS menu_uv,
  COUNT(DISTINCT CASE WHEN screen_name = 'productdetail' THEN user_no END) AS detail_uv,
  COUNT(DISTINCT CASE WHEN screen_name = 'confirmorder' THEN user_no END) AS confirm_uv,
  COUNT(DISTINCT CASE WHEN screen_name = 'orderdetail' THEN user_no END) AS paid_uv
FROM dw_dws.dws_mg_log_user_screen_name_d_1d
WHERE dt = '2026-03-03'
  AND screen_name IN ('menu','productdetail','confirmorder','orderdetail')
GROUP BY dt;
```

---

### 3.7 dw_dwd.dwd_marketing_t_push_receipt_d_inc
> 营销触达记录表。SMS / Push / WhatsApp / EDM。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| user_no | VARCHAR | 用户编号 | — |
| activity_name | VARCHAR | 活动名称 | 可用 REGEXP 分类 |
| cdp_push_time | DATETIME | 触达时间 | — |
| contact_channel | INT | 触达渠道 | 1=SMS,2=Push,3-4=WhatsApp,5=EDM |
| user_receipt_state | INT | 送达状态 | — |

```sql
-- 按渠道统计触达人数
SELECT contact_channel,
  COUNT(DISTINCT user_no) AS reached_users
FROM dw_dwd.dwd_marketing_t_push_receipt_d_inc
WHERE activity_name LIKE '%Recall%'
GROUP BY contact_channel;
```

---

### 3.8 ods_luckyus_sales_marketing.t_user_invitation_info
> 分享有礼邀请关系表。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| activity_no | VARCHAR | 活动编号 | LIKE '%LKUS%'，随月份变化 |
| inviter_user_no | VARCHAR | 邀请人 | — |
| invitee_user_no | VARCHAR | 被邀请人 | — |
| invitation_success | INT | 是否成功 | **1 = 被邀请人已下单** |
| create_time | DATETIME | 注册时间 | 被邀请人注册时间 |
| modify_time | DATETIME | 下单时间 | invitation_success=1 时取此值 |

---

### 3.9 ods_luckyus_isalesdatamarketing.t_user_traffic_distribution
> 实验分流表。AB 实验的人群分组来源。

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| experiment_layer_no | VARCHAR | 实验层编号 | — |
| experiment_group_no | VARCHAR | 实验组编号 | 区分 A/B/C 组 |
| user_no | VARCHAR | 用户编号 | — |

---

### 3.10 ods_luckyus_track.v_hmonitor_track_event_rt
> 前端埋点事件表。**大表，必须加 dt 分区过滤。**

| 字段 | 类型 | 业务含义 | 备注 |
|------|------|---------|------|
| dt | INT | 日期分区 | 格式 YYYYMMDD，整数型 |
| event | VARCHAR | 事件名 | 含 page/model/content/action |
| login_id | VARCHAR | 登录ID | — |
| p_login_id | VARCHAR | 补充登录ID | UV 去重用 `COALESCE(p_login_id, login_id)` |
| server_time_form | DATETIME | 服务端时间 | 需 CONVERT_TZ |
| p_* | VARCHAR | 自定义参数 | p_screen_name, p_location, p_pic_url 等 |

**事件命名规则**：`$page.{页面}$model.{模块}$content.{内容}$action.{动作}`
- `action.bw` = 曝光
- `action.ck` = 点击

---

### 3.11 其他重要表

| 表 | 用途 | 核心字段 |
|----|------|----------|
| `dw_ads.user_label_df` | 用户标签 + 哈希桶 | user_no, ab_bash_10000(0-9999), dt |
| `dw_ads.ads_marketing_t_user_group_d_his` | CDP 人群标签 | group_name, user_no, dt |
| `dw_ads.ads_marketing_t_user_grant_d_his` | 触达权限 | is_able_sms, is_able_push, is_able_waapp, is_able_mail |
| `dw_ads.ads_user_order_rep_info_d_nw` | 周复购矩阵 | src_week, dst_week, src_usr_cnt, dst_usr_cnt |
| `dw_ads.ads_user_order_rep_info_d_nm` | 月复购矩阵 | src_month, dst_month, src_usr_cnt, dst_usr_cnt |
| `dw_dim.dim_shop_d_his` | 门店维度 | dept_id, shop_name, dt |
| `ods_luckyus_sales_order.t_order_make` | 制作完成 | order_id, finish_time |
| `ods_luckyus_sales_order.t_order_promotion_detail` | 促销明细 | order_id, promotion_name |
| `dw_dwd.dwd_t_mkt_coupon_use_record_d_inc` | 券使用记录(DWD版) | coupon_name, user_no, use_status, receive_time |

---

## 四、指标口径词典

### 4.1 经营核心指标

| 指标 | 精确公式 | 数据来源 | 陷阱提醒 |
|------|---------|---------|---------|
| **杯量** | `COUNT(*)` from t_order_item WHERE Drink | ads 表的 SUM(sku_cnt) | 不是订单数！每行=一杯 |
| **销售额** | `SUM(pay_amount)` | ads 表 | — |
| **单杯实收** | `SUM(pay_amount) / SUM(sku_cnt)` | ads 表 | 不是 销售额/订单数 |
| **客单价(AOV)** | `SUM(pay_money) / COUNT(DISTINCT order_id)` | v_order | pay_money=0 也参与 |
| **店日均杯量** | 杯量 / 营业门店数 | — | — |
| **营业门店数** | `COUNT(DISTINCT shop_name)` | ads 表 (当天有销售) | — |

### 4.2 用户指标

| 指标 | 精确公式 | 陷阱提醒 |
|------|---------|---------|
| **新客** | 首笔成功订单日期 = 统计日的用户 | 首单日期用 `MIN(stat_date)` |
| **老客** | 首笔成功订单日期 < 统计日 | — |
| **新客占比** | 新客数 / (新客 + 老客) × 100% | 分母不含未购用户 |
| **注册用户** | t_user 当日 create_time | 需 CONVERT_TZ |
| **店日均新客** | 新客数 / 营业门店数 | — |

### 4.3 留存与复购

| 指标 | 精确公式 | 时间窗口 |
|------|---------|---------|
| **D7 留存率** | 7日前的用户中，7日内有再购的 / 7日前用户数 | [date-7, date] |
| **D3 复购率** | 首单后3天内有再购 / 首单用户数 | 首单后 [+1d, +3d] |
| **D7 复购率** | 首单后7天内有再购 / 首单用户数 | 首单后 [+1d, +7d] |
| **同日复购率** | 当天下单>=2笔的用户 / 当天下单用户 | 当天 |
| **周复购率** | 本周购买且上周也购买的用户 / 上周购买用户 | 周 → 周 |
| **多杯率** | 当天饮品>=2杯的用户 / 当天下单用户 | 当天 |

### 4.4 漏斗与转化

| 指标 | 精确公式 |
|------|---------|
| **到访率** | APP打开用户(dws表任意记录) / 总用户 × 100% |
| **下单率** | 下单用户 / 总用户 × 100% |
| **到访转化率** | 下单用户 / APP打开用户 × 100% |
| **菜单→详情转化** | productdetail_uv / menu_uv × 100% |
| **详情→确认转化** | confirmorder_uv / productdetail_uv × 100% |
| **确认→支付转化** | orderdetail_uv / confirmorder_uv × 100% |

### 4.5 价格与折扣

| 指标 | 精确公式 | 陷阱提醒 |
|------|---------|---------|
| **折扣深度** | (origin_price - pay_money) / origin_price × 100% | NULLIF(origin_price, 0) |
| **实收比** | pay_money / origin_price × 100% | 反向看折扣 |
| **ARPU (全用户)** | SUM(pay_money) / total_users | 含未购 |
| **ARPU (有购)** | SUM(pay_money) / order_users | 仅购买用户 |
| **外卖占比** | channel IN (8,9,10) 的订单数 / 总订单数 | — |
| **完成率** | finish_time IS NOT NULL 的订单 / 总订单 | — |
| **商品渗透率** | 含某商品的订单数 / 总订单数 × 100% | — |

---

## 五、分析场景 Playbook

### 5.1 每日经营日报

**目的**：监控核心经营指标的日变化和周同比

| 步骤 | 模块 | 数据源 | 耗时 |
|------|------|--------|------|
| 1 | 业务结果(杯量/销售额/单杯实收) | ads_mg_sku... | 秒出 |
| 2 | 门店明细(各店杯量排名) | ads_mg_sku... | 秒出 |
| 3 | 漏斗转化(菜单→下单) | dws_mg_log... | 秒出 |
| 4 | 商品渗透(TOP5商品占比) | ads_mg_sku... | 秒出 |
| 5 | 用户指标(新客/老客/留存) | v_order + t_user | 8-15s/天 |

**关键**：模块5 只查目标日和上周同天，不要查全部 7 天。

### 5.2 AB 实验分析

**三阶段渐进法**：

```
阶段1: Fixed Cohort 快速评估（实验开始 3-7 天）
 └ 锁定实验开始日人群 → 统一追踪 D0-D7
 └ 输出：组间到访率、转化率、AOV、ARPU 差异

阶段2: Rolling Cohort 长期追踪（实验开始 7-14 天）
 └ 每日新入组用户按各自 first_group_date 追踪
 └ 输出：D0-D7 每日指标对比，消除时间混淆

阶段3: 分层深度诊断
 └ 按 RFM 分层：哪些用户群对实验更敏感？
 └ 按首单特征：AOV / 折扣深度 / 杯数 分层
 └ 输出：敏感人群识别，策略建议
```

### 5.3 用户留存分析

**CTE 标准模板**：
```sql
WITH target_users AS (
    -- 第1步：锁定基准日用户
    SELECT DISTINCT user_no FROM v_order WHERE stat_date = '{date}' AND status = 90
),
future_orders AS (
    -- 第2步：查后续活跃
    SELECT DISTINCT user_no FROM v_order
    WHERE stat_date > '{date}' AND stat_date <= DATE_ADD('{date}', INTERVAL {n} DAY)
      AND user_no IN (SELECT user_no FROM target_users)
),
retention AS (
    -- 第3步：计算留存率
    SELECT
        (SELECT COUNT(*) FROM target_users) AS base_users,
        (SELECT COUNT(*) FROM future_orders) AS retained_users
)
SELECT base_users, retained_users,
       ROUND(retained_users / NULLIF(base_users, 0) * 100, 2) AS retention_rate
FROM retention;
```

### 5.4 分享有礼分析

**六大板块**：获客结果 → 流量获取 → 分享意愿 → 分享效率 → 被邀请人转化 → 人均邀请

**全链路漏斗**：
```
资源位曝光 → 资源位点击 → 进入分享页 → 点击分享 → 被邀请人注册 → D0下单 → D7下单
(v_hmonitor)  (v_hmonitor)  (v_hmonitor)  (v_hmonitor)  (t_invitation)  (v_order)   (v_order)
```

### 5.5 触达效果分析

**标准漏斗**：
```
可触达用户(grant表) → 已触达(push表) → APP打开(dws表) → 菜单浏览 → 下单
```

**按渠道拆分**：SMS(1) / Push(2) / WhatsApp(3-4) / EDM(5)

---

## 六、SQL 规范手册

### 6.1 必须遵守的 6 条铁律

```sql
-- 1. 时区转换（后台存 UTC，展示美东时间）
DATE(CONVERT_TZ(create_time, @@time_zone, 'America/New_York'))

-- 2. 租户过滤
WHERE INSTR(tenant, 'IQ') = 0   -- 或 tenant = 'LKUS'

-- 3. 成功订单
AND status = 90

-- 4. 排除测试店
AND shop_name NOT IN ('NJ Test Kitchen', 'NJ Test Kitchen 2')

-- 5. 饮品过滤（杯量统计时）
AND one_category_name = 'Drink'

-- 6. 用户剔除（用户分析时）
AND type NOT IN (4, 5)  -- 排除游客和外卖用户
```

### 6.2 性能优化原则

| 原则 | 说明 |
|------|------|
| ADS 表优先 | 能用汇总表绝不查明细表 |
| 避免大表 JOIN | t_order_item JOIN v_order 会超时 |
| 分区键必须 | 查 ODS 表必须加 dt 或日期条件 |
| 先过滤再 JOIN | 用 CTE/子查询先缩小范围 |
| NULLIF 防零 | 除法运算用 `NULLIF(denominator, 0)` |
| 整数日期比较 | 埋点表 dt 是 INT 型，用 `BETWEEN int AND int` |

### 6.3 常用 SQL 模式速查

| 模式 | 代码片段 |
|------|---------|
| 新老客判定 | `MIN(stat_date) OVER (PARTITION BY user_no) = current_date → 新客` |
| 留存CTE | `target_users → future_orders → retention_calc` |
| 复购（N日内） | `MAX(CASE WHEN stat_date BETWEEN first+1 AND first+N THEN 1 ELSE 0 END)` |
| 复购（同日） | `CASE WHEN COUNT(DISTINCT order_id) >= 2 THEN 1 END` |
| 折扣分层 | `pay/NULLIF(origin,0) ≤ 0.3/0.5/0.7/1.0` |
| 时段划分 | `HOUR(CONVERT_TZ(...)) BETWEEN 7-8/9-10/11-12/13-14/15-16/17-18/19+` |
| 多杯判断 | `SUM(CASE WHEN Drink THEN 1 END) >= 2 → 多杯` |
| 外卖标记 | `channel IN (8, 9, 10)` |
| 累计计算 | `SUM(...) OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING)` |
| 周分组 | `YEARWEEK(dt, 1)` — ISO周制 |
| 周同比 | `(本期值 - 上周同天值) / 上周同天值 × 100%` |

---

## 七、用户分层体系

### 7.1 RFM 分层

```
           Frequency
           F1(1次)  F2(2-3)  F3(4-7)  F4(8+)
R0(≤7d)    新客      激活中    活跃     忠诚
R1(8-30d)  流失风险  温热      活跃     高价值
R2(31-60d) 沉睡      沉睡      唤醒     挽回
R3(60d+)   流失      流失      流失     流失
```

### 7.2 生命周期分层

| 阶段 | 条件 | 策略方向 |
|------|------|---------|
| 注册未购 | t_user 有记录，v_order 无记录 | 首单券激活 |
| 新购用户(≤15d) | 首单后 1-15 天 | 复购券培养 |
| 成长用户(16-30d) | 首购后 16-30 天 | 频次提升 |
| 成熟用户(31d+) | 首购后 31天+ | 多杯/高单价 |
| 来访未购 | 7天内有访问无购买 | 转化推送 |
| 沉默用户 | 最后下单 30 天+ | 召回 |

### 7.3 首单特征分层（实验用）

| 维度 | 分档 | 含义 |
|------|------|------|
| AOV | <$5 / $5-10 / ≥$10 | 首单消费力 |
| 折扣深度 | ≥35% / 25-35% / <25% | 价格敏感度 |
| 杯数 | 单杯 / 双杯 / 3杯+ | 消费深度 |
| 注册天数 | 3d / 7d / 15d / 30d | 用户成熟度 |

---

## 八、项目索引

| 项目/分析 | 关键文件 | 状态 |
|-----------|---------|------|
| 日报 | `~/.claude/skills/daily-report/SKILL.md` | 技能化 |
| AB 实验 | `~/.claude/skills/ab-experiment/skill.md` | 技能化 |
| 分享有礼 | `~/.claude/skills/share-the-luck/skill.md` | 技能化 |
| 数据查询 | `~/.claude/skills/luckyus-data-query/skill.md` | 技能化 |
| SQL 学习库 | `~/Downloads/sql/`（470份） | 参考 |
| 新客实验 | `~/Desktop/实验报告/` | 已完成 |
| 涨价实验 | `~/Vibe coding/` 相关 html/py | 进行中 |
