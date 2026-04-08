# 微信小程序开发需求文档 (PRD) - 会员裂变商城

## 1. 项目概述

### 1.1 项目目标
构建一个基于微信小程序的会员裂变商城，通过双等级会员体系实现用户增长裂变。

### 1.2 技术架构
- **前端**: 微信原生小程序
- **后端**: 微信云开发 (云函数 + 云数据库)
- **样式**: 参考 Nike 小程序风格 (黑白极简 + 橙色点缀)

---

## 2. UI 设计规范 (Design System)

### 2.1 配色方案 (Color Palette)

| 用途 | 色值 | 说明 |
|------|------|------|
| 主色 (Primary) | `#000000` | 纯黑，用于核心按钮、一级标题、底部导航选中态 |
| 背景色 (Background) | `#FFFFFF` | 纯白，页面主背景 |
| 背景色-次级 | `#F6F6F6` | 浅灰，用于分隔带、搜索框背景、卡片背景 |
| 强调色 (Accent) | `#FA5400` | 活力橙，用于会员价、优惠券、CTA按钮、未读红点 |
| 辅助色 | `#999999` | 深灰，用于原价划线、辅助说明文字 |
| 边框色 | `#E5E5E5` | 浅灰，用于分割线、边框 |
| 成功色 | `#07C160` | 微信绿，用于成功提示 |
| 警告色 | `#FF9500` | 橙黄，用于警告提示 |
| 错误色 | `#FA5151` | 红色，用于错误提示 |

### 2.2 字体规范

| 用途 | 字号 | 字重 | 颜色 |
|------|------|------|------|
| 大标题 | 36rpx | Bold (600) | #000000 |
| 页面标题 | 32rpx | Bold (600) | #000000 |
| 正文-大 | 30rpx | Regular (400) | #000000 |
| 正文-中 | 28rpx | Regular (400) | #333333 |
| 正文-小 | 26rpx | Regular (400) | #666666 |
| 辅助文字 | 24rpx | Regular (400) | #999999 |
| 价格-大 | 40rpx | Bold (600) | #FA5400 |
| 价格-小 | 28rpx | Regular (400) | #999999 (划线) |

### 2.3 圆角规范

| 元素 | 圆角 |
|------|------|
| 按钮-大 | 8rpx |
| 按钮-胶囊 | 999rpx (全圆角) |
| 卡片 | 16rpx |
| 头像 | 50% (圆形) |
| 输入框 | 8rpx |
| 弹窗 | 24rpx |

### 2.4 间距规范

| 用途 | 间距 |
|------|------|
| 页面边距 | 32rpx |
| 卡片内边距 | 24rpx |
| 元素间距-大 | 32rpx |
| 元素间距-中 | 24rpx |
| 元素间距-小 | 16rpx |
| 元素间距-微 | 8rpx |

---

## 3. 会员等级系统

### 3.1 等级定义

| 等级名称 | 字段值 | 获取方式 | 权益说明 |
|----------|--------|----------|----------|
| 普通会员 | `normal` | 注册即默认 | 1. 仅能按原价购买<br>2. 不可生成邀请码<br>3. 个人中心显示"输入邀请码"入口 |
| 高级会员 | `premium` | 1. 填写有效邀请码<br>2. 通过高级会员链接注册 | 1. 享受会员折扣价<br>2. 可生成邀请海报/邀请码<br>3. 个人中心显示"邀请好友"入口<br>4. 专属客服通道 |

### 3.2 邀请裂变流程

#### 流程 A: 主动升级
```
普通会员 A
  -> 点击"个人中心"
  -> 点击"成为高级会员"
  -> 弹出 Modal 输入 6 位邀请码
  -> 后端验证邀请码有效性
  -> 验证成功
  -> 升级为 premium
  -> 记录邀请关系 (inviter_id)
```

#### 流程 B: 被动受邀
```
高级会员 B
  -> 生成邀请海报/分享小程序卡片 (携带 invite_code 参数)
  -> 新用户 C 扫码/点击进入
  -> 授权注册
  -> 系统检测到 invite_code 参数
  -> C 注册即为 premium
  -> 记录邀请人为 B
```

### 3.3 邀请码规则
- 格式: 6 位大写字母 + 数字组合
- 生成算法: 基于 UserID 使用 Hashids 生成，保证唯一性
- 有效期: 永久有效
- 使用次数: 无限制

---

## 4. 数据库设计 (云数据库)

### 4.1 用户表 (users)

```javascript
{
  _id: String,              // 文档ID (自动生成)
  openid: String,           // 微信 OpenID (唯一索引)
  unionid: String,          // 微信 UnionID (可选)
  nickname: String,         // 用户昵称
  avatar_url: String,       // 头像URL
  phone: String,            // 手机号 (可选)
  role: String,             // 'normal' | 'premium'
  invite_code: String,      // 该用户的邀请码 (仅 premium 用户有)
  inviter_id: String,       // 邀请人的 _id
  invited_count: Number,    // 已邀请人数
  created_at: Date,         // 注册时间
  updated_at: Date          // 更新时间
}
```

### 4.2 商品表 (products)

```javascript
{
  _id: String,              // 文档ID
  name: String,             // 商品名称
  description: String,      // 商品描述
  images: Array<String>,    // 商品图片列表
  category_id: String,      // 分类ID
  price_original: Number,   // 原价 (分)
  price_member: Number,     // 会员价 (分)
  stock: Number,            // 库存
  sales: Number,            // 销量
  status: String,           // 'on' | 'off' 上架/下架
  sort_order: Number,       // 排序权重
  created_at: Date,
  updated_at: Date
}
```

### 4.3 分类表 (categories)

```javascript
{
  _id: String,
  name: String,             // 分类名称
  icon: String,             // 分类图标
  sort_order: Number,       // 排序
  status: String            // 'on' | 'off'
}
```

### 4.4 订单表 (orders)

```javascript
{
  _id: String,
  order_no: String,         // 订单号 (唯一索引)
  user_id: String,          // 用户ID
  openid: String,           // 用户 OpenID
  items: [{                 // 订单商品
    product_id: String,
    product_name: String,
    product_image: String,
    price: Number,          // 成交单价 (分)
    quantity: Number
  }],
  total_amount: Number,     // 订单总额 (分)
  pay_amount: Number,       // 实付金额 (分)
  status: String,           // 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled'
  address: {                // 收货地址
    name: String,
    phone: String,
    province: String,
    city: String,
    district: String,
    detail: String
  },
  remark: String,           // 买家备注
  paid_at: Date,            // 支付时间
  shipped_at: Date,         // 发货时间
  completed_at: Date,       // 完成时间
  created_at: Date,
  updated_at: Date
}
```

### 4.5 邀请记录表 (invite_records)

```javascript
{
  _id: String,
  inviter_id: String,       // 邀请人ID
  invitee_id: String,       // 被邀请人ID
  invitee_openid: String,   // 被邀请人 OpenID
  invite_code: String,      // 使用的邀请码
  created_at: Date          // 邀请时间
}
```

---

## 5. 页面原型与功能详解

### 5.1 Tab 1: 商城首页 (pages/index/index)

#### 页面结构
```
┌─────────────────────────────────────┐
│  🔍 搜索商品...                      │  <- 搜索栏 (灰色背景)
├────────┬────────────────────────────┤
│        │  ┌────────┐ ┌────────┐    │
│  鞋类  │  │  商品1  │ │  商品2  │    │  <- 左侧分类 + 右侧商品网格
│        │  │  ¥800  │ │  ¥600  │    │
│ ────── │  └────────┘ └────────┘    │
│        │  ┌────────┐ ┌────────┐    │
│  服饰  │  │  商品3  │ │  商品4  │    │
│        │  │  ¥500  │ │  ¥900  │    │
│ ────── │  └────────┘ └────────┘    │
│        │                            │
│  配件  │         ...               │
│        │                            │
└────────┴────────────────────────────┘
```

#### 功能说明
1. **搜索栏**: 点击跳转搜索页面
2. **左侧分类导航**:
   - 宽度约 20%
   - 选中项: 文字加粗 + 左侧 3px 黑色竖线
   - 点击切换右侧商品列表
3. **右侧商品列表**:
   - 两列网格布局
   - 下拉刷新 + 上拉加载更多
4. **商品卡片价格显示逻辑**:
   - **普通会员**: 显示 `¥1000`(黑色)，下方 `高级会员 ¥800`(灰色+锁图标)
   - **高级会员**: 显示 `¥800`(橙色)，旁边 `¥1000`(灰色划线)

### 5.2 Tab 2: 福利中心 (pages/benefits/benefits)

#### 页面结构
```
┌─────────────────────────────────────┐
│  ┌─────────────────────────────┐   │
│  │   ★ 高级会员专属福利 ★       │   │  <- 顶部 Banner (黑色卡片)
│  │                             │   │
│  │   [ 去升级 / 去邀请 ]        │   │  <- CTA按钮 (橙色)
│  └─────────────────────────────┘   │
│                                     │
│  我的权益                           │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐      │
│  │折扣│ │包邮│ │礼包│ │客服│      │  <- 权益图标Grid
│  └────┘ └────┘ └────┘ └────┘      │
│                                     │
│  会员专区商品                        │
│  ┌─────────────────────────────┐   │
│  │ 商品列表...                  │   │  <- 会员专属商品
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

#### 功能说明
1. **顶部 Banner**:
   - 普通会员: 显示"解锁高级福利"，按钮"去升级"
   - 高级会员: 显示"尊贵会员权益生效中"，按钮"去邀请"
2. **权益图标**:
   - 普通会员: 图标灰色 + 锁标志，点击提示"请输入邀请码解锁"
   - 高级会员: 图标彩色，正常展示
3. **权益列表**:
   - 专属折扣: 全场商品享会员价
   - 免费包邮: 订单满99元免邮
   - 生日礼包: 生日月领取专属礼券
   - 专属客服: VIP客服通道

### 5.3 Tab 3: 个人中心 (pages/profile/profile)

#### 页面结构
```
┌─────────────────────────────────────┐
│                                     │
│    ┌────┐                          │
│    │头像│  昵称                     │
│    └────┘  [Normal] / [Premium]    │  <- 等级徽章
│                                     │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │  输入邀请码，升级高级会员     │   │  <- 普通会员显示
│  └─────────────────────────────┘   │
│                     或              │
│  ┌─────────────────────────────┐   │
│  │  邀请好友，已邀请 X 人        │   │  <- 高级会员显示
│  └─────────────────────────────┘   │
│                                     │
├─────────────────────────────────────┤
│  我的订单                    全部 > │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐      │
│  │待付款│ │待发货│ │待收货│ │已完成│  │
│  └────┘ └────┘ └────┘ └────┘      │
├─────────────────────────────────────┤
│  > 收货地址                         │
│  > 联系客服                         │
│  > 关于我们                         │
└─────────────────────────────────────┘
```

#### 功能说明
1. **用户信息区**:
   - 未登录: 显示默认头像 + "点击登录"
   - 已登录: 显示头像 + 昵称 + 等级徽章
2. **等级徽章样式**:
   - Normal: 灰色背景(#F6F6F6) + 黑色文字
   - Premium: 黑色背景 + 橙色文字
3. **核心行动区 (CTA)**:
   - **普通会员**: 黑色大按钮"输入邀请码，升级高级会员"
     - 点击弹出 Modal，含输入框 + 确认按钮
   - **高级会员**: 黑色大按钮"邀请好友，已邀请 X 人"
     - 点击跳转邀请页面，可生成海报/复制邀请码
4. **订单入口**: 四个状态图标，点击跳转对应订单列表
5. **功能列表**: 收货地址管理、客服、关于我们

### 5.4 邀请码弹窗 (Modal)

#### 弹窗结构
```
┌─────────────────────────────────────┐
│              成为高级会员            │
│                                     │
│  请输入6位邀请码                     │
│  ┌─────────────────────────────┐   │
│  │                             │   │  <- 输入框
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │          确认升级            │   │  <- 黑色按钮
│  └─────────────────────────────┘   │
│                                     │
│              稍后再说               │  <- 灰色文字链接
└─────────────────────────────────────┘
```

### 5.5 商品详情页 (pages/product/detail)

#### 页面结构
```
┌─────────────────────────────────────┐
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │        商品轮播图            │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  商品名称                           │
│  ¥800  ¥1000                       │  <- 会员价 + 原价划线
│  [高级会员专享价]                    │  <- 橙色标签
│                                     │
│  ─────────────────────────────────  │
│  商品详情                           │
│  ...图文描述...                     │
│                                     │
├─────────────────────────────────────┤
│  [ 客服 ]  [ 购物车 ]  [ 立即购买 ]  │  <- 底部操作栏
└─────────────────────────────────────┘
```

---

## 6. 云函数设计

### 6.1 用户模块 (cloudfunctions/user)

#### login - 用户登录/注册
```javascript
// 入参
{
  code: String,           // wx.login 获取的 code
  userInfo: Object,       // 用户信息 (昵称、头像)
  invite_code: String     // 邀请码 (可选，来自分享参数)
}

// 返回
{
  success: Boolean,
  data: {
    user: UserObject,     // 用户信息
    isNewUser: Boolean    // 是否新用户
  }
}
```

#### getUserInfo - 获取用户信息
```javascript
// 入参: 无 (通过 openid 自动识别)

// 返回
{
  success: Boolean,
  data: UserObject
}
```

#### upgradeToPremiun - 升级为高级会员
```javascript
// 入参
{
  invite_code: String     // 邀请码
}

// 返回
{
  success: Boolean,
  message: String,        // 成功/失败消息
  data: {
    user: UserObject      // 更新后的用户信息
  }
}
```

### 6.2 商品模块 (cloudfunctions/product)

#### getCategories - 获取分类列表
```javascript
// 入参: 无

// 返回
{
  success: Boolean,
  data: Array<Category>
}
```

#### getProducts - 获取商品列表
```javascript
// 入参
{
  category_id: String,    // 分类ID (可选)
  keyword: String,        // 搜索关键词 (可选)
  page: Number,           // 页码，默认 1
  page_size: Number       // 每页数量，默认 10
}

// 返回
{
  success: Boolean,
  data: {
    list: Array<Product>,
    total: Number,
    page: Number,
    page_size: Number
  }
}
```

#### getProductDetail - 获取商品详情
```javascript
// 入参
{
  product_id: String
}

// 返回
{
  success: Boolean,
  data: Product
}
```

### 6.3 邀请模块 (cloudfunctions/invite)

#### getInviteCode - 获取/生成邀请码
```javascript
// 入参: 无 (需要是高级会员)

// 返回
{
  success: Boolean,
  data: {
    invite_code: String,
    invite_count: Number  // 已邀请人数
  }
}
```

#### verifyInviteCode - 验证邀请码
```javascript
// 入参
{
  code: String
}

// 返回
{
  success: Boolean,
  valid: Boolean,
  inviter: {              // 邀请人信息 (脱敏)
    nickname: String,
    avatar: String
  }
}
```

#### getInviteRecords - 获取邀请记录
```javascript
// 入参
{
  page: Number,
  page_size: Number
}

// 返回
{
  success: Boolean,
  data: {
    list: Array<InviteRecord>,
    total: Number
  }
}
```

### 6.4 订单模块 (cloudfunctions/order)

#### createOrder - 创建订单
```javascript
// 入参
{
  items: [{
    product_id: String,
    quantity: Number
  }],
  address_id: String,
  remark: String
}

// 返回
{
  success: Boolean,
  data: {
    order_id: String,
    order_no: String,
    pay_amount: Number,
    // 微信支付参数
    payment: {
      timeStamp: String,
      nonceStr: String,
      package: String,
      signType: String,
      paySign: String
    }
  }
}
```

#### getOrders - 获取订单列表
```javascript
// 入参
{
  status: String,         // 订单状态 (可选)
  page: Number,
  page_size: Number
}

// 返回
{
  success: Boolean,
  data: {
    list: Array<Order>,
    total: Number
  }
}
```

---

## 7. 关键交互逻辑

### 7.1 邀请码升级流程

```javascript
// pages/profile/profile.js

// 1. 点击升级按钮，显示弹窗
onTapUpgrade() {
  this.setData({ showModal: true });
}

// 2. 输入邀请码
onInputCode(e) {
  this.setData({ inputCode: e.detail.value.toUpperCase() });
}

// 3. 确认升级
async onConfirmUpgrade() {
  const { inputCode } = this.data;

  if (!inputCode || inputCode.length !== 6) {
    wx.showToast({ title: '请输入6位邀请码', icon: 'none' });
    return;
  }

  wx.showLoading({ title: '验证中...' });

  try {
    const res = await wx.cloud.callFunction({
      name: 'user',
      data: {
        action: 'upgradeToPremium',
        invite_code: inputCode
      }
    });

    wx.hideLoading();

    if (res.result.success) {
      wx.showToast({ title: '升级成功！', icon: 'success' });
      this.setData({
        showModal: false,
        userInfo: res.result.data.user
      });
    } else {
      wx.showToast({ title: res.result.message || '邀请码无效', icon: 'none' });
    }
  } catch (err) {
    wx.hideLoading();
    wx.showToast({ title: '网络错误，请重试', icon: 'none' });
  }
}
```

### 7.2 价格展示逻辑

```javascript
// utils/price.js

/**
 * 格式化价格显示
 * @param {Object} product - 商品对象
 * @param {String} userRole - 用户角色 'normal' | 'premium'
 * @returns {Object} 价格显示对象
 */
function formatPrice(product, userRole) {
  const originalPrice = (product.price_original / 100).toFixed(2);
  const memberPrice = (product.price_member / 100).toFixed(2);

  if (userRole === 'premium') {
    return {
      mainPrice: memberPrice,
      mainPriceColor: '#FA5400',  // 橙色
      subPrice: originalPrice,
      subPriceStyle: 'line-through',
      showMemberTag: true,
      tagText: '会员专享'
    };
  } else {
    return {
      mainPrice: originalPrice,
      mainPriceColor: '#000000',  // 黑色
      subPrice: memberPrice,
      subPriceStyle: 'normal',
      showMemberTag: true,
      tagText: '高级会员 ¥' + memberPrice,
      showLock: true
    };
  }
}

module.exports = { formatPrice };
```

---

## 8. 安全规范

### 8.1 数据安全
1. **价格计算**: 所有订单金额必须在云函数中计算，前端仅做展示
2. **权限校验**: 云函数中必须校验用户 openid 和角色
3. **敏感信息**: 手机号、地址等敏感信息需加密存储

### 8.2 接口安全
1. 云函数使用 `wx-server-sdk` 获取 openid，不信任前端传值
2. 订单创建时二次校验商品价格和库存
3. 邀请码升级需校验邀请人是否为有效的高级会员

### 8.3 防刷策略
1. 登录接口限频: 同一 openid 每分钟最多 10 次
2. 订单创建限频: 同一用户每分钟最多 5 次
3. 邀请码验证限频: 每分钟最多 10 次

---

## 9. 部署检查清单

### 9.1 云开发配置
- [ ] 创建云开发环境
- [ ] 开通云数据库
- [ ] 创建数据集合并设置索引
- [ ] 部署云函数
- [ ] 配置云函数权限

### 9.2 小程序配置
- [ ] 配置 app.json (页面路径、tabBar、权限)
- [ ] 配置 project.config.json (appid、云开发环境ID)
- [ ] 上传小程序图标资源
- [ ] 配置分享参数

### 9.3 上线前测试
- [ ] 普通会员购买流程
- [ ] 高级会员购买流程 (验证会员价)
- [ ] 邀请码升级流程
- [ ] 分享邀请流程 (新用户直接成为高级会员)
- [ ] 订单支付流程
- [ ] 异常场景测试 (网络错误、无效邀请码等)

---

## 10. 项目目录结构

```
member-mall-miniprogram/
├── miniprogram/                 # 小程序前端
│   ├── pages/                   # 页面
│   │   ├── index/              # 商城首页
│   │   ├── benefits/           # 福利中心
│   │   ├── profile/            # 个人中心
│   │   ├── product/            # 商品详情
│   │   ├── order/              # 订单相关
│   │   ├── search/             # 搜索页
│   │   └── invite/             # 邀请页
│   ├── components/              # 公共组件
│   │   ├── product-card/       # 商品卡片
│   │   ├── member-badge/       # 会员徽章
│   │   ├── invite-modal/       # 邀请码弹窗
│   │   └── empty-state/        # 空状态
│   ├── utils/                   # 工具函数
│   │   ├── api.js              # API 封装
│   │   ├── util.js             # 通用工具
│   │   └── price.js            # 价格处理
│   ├── styles/                  # 公共样式
│   │   └── common.wxss         # 全局样式
│   ├── images/                  # 图片资源
│   ├── app.js                   # 应用入口
│   ├── app.json                 # 应用配置
│   └── app.wxss                 # 全局样式
├── cloudfunctions/              # 云函数
│   ├── user/                    # 用户模块
│   ├── product/                 # 商品模块
│   ├── order/                   # 订单模块
│   └── invite/                  # 邀请模块
├── docs/                        # 文档
│   └── PRD.md                   # 本文档
└── README.md                    # 项目说明
```

---

*文档版本: v1.0*
*最后更新: 2024年*
