# 会员裂变商城小程序

基于微信小程序 + 云开发的会员裂变商城系统。

## 项目特点

- **双等级会员体系**: 普通会员 / 高级会员
- **邀请裂变机制**: 高级会员可邀请好友，新用户通过邀请码注册自动升级
- **差异化定价**: 普通会员原价，高级会员享专属折扣
- **Nike 风格 UI**: 黑白极简 + 橙色点缀

## 快速开始

### 1. 准备工作

1. 注册微信小程序账号，获取 AppID
2. 下载并安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)

### 2. 导入项目

1. 打开微信开发者工具
2. 选择「导入项目」
3. 选择项目目录 `member-mall-miniprogram`
4. 填入你的 AppID
5. 点击「导入」

### 3. 配置云开发

1. 点击开发者工具左上角「云开发」按钮
2. 开通云开发，创建云环境
3. 复制环境 ID
4. 修改 `miniprogram/app.js` 中的 `env` 配置:

```javascript
wx.cloud.init({
  env: 'your-env-id',  // 替换为你的环境 ID
  traceUser: true
});
```

5. 修改 `project.config.json` 中的 `appid`:

```json
{
  "appid": "your-appid"  // 替换为你的 AppID
}
```

### 4. 创建数据库集合

在云开发控制台 → 数据库中创建以下集合:

| 集合名 | 说明 |
|--------|------|
| users | 用户表 |
| products | 商品表 |
| categories | 分类表 |
| orders | 订单表 |
| addresses | 地址表 |
| invite_records | 邀请记录表 |

### 5. 部署云函数

右键点击 `cloudfunctions` 目录下的每个云函数文件夹，选择「上传并部署: 云端安装依赖」:

- user
- product
- order
- invite

### 6. 初始化示例数据

在云开发控制台 → 云函数 → product → 云端测试，输入:

```json
{
  "action": "initData"
}
```

点击运行，即可初始化示例商品数据。

## 项目结构

```
member-mall-miniprogram/
├── miniprogram/                 # 小程序前端
│   ├── pages/                   # 页面
│   │   ├── index/              # 商城首页
│   │   ├── benefits/           # 福利中心
│   │   ├── profile/            # 个人中心
│   │   ├── product/            # 商品详情
│   │   ├── order/              # 订单
│   │   ├── search/             # 搜索
│   │   └── invite/             # 邀请
│   ├── components/              # 公共组件
│   ├── utils/                   # 工具函数
│   ├── images/                  # 图片资源
│   ├── app.js
│   ├── app.json
│   └── app.wxss
├── cloudfunctions/              # 云函数
│   ├── user/                    # 用户模块
│   ├── product/                 # 商品模块
│   ├── order/                   # 订单模块
│   └── invite/                  # 邀请模块
├── docs/
│   └── PRD.md                   # 需求文档
└── README.md
```

## 核心功能

### 会员等级

| 等级 | 获取方式 | 权益 |
|------|----------|------|
| 普通会员 | 注册即为普通会员 | 原价购买 |
| 高级会员 | 1. 输入邀请码<br>2. 通过邀请链接注册 | 1. 会员折扣价<br>2. 可生成邀请码<br>3. 邀请好友 |

### 邀请流程

```
高级会员 A
  → 生成邀请码/分享链接
  → 好友 B 输入邀请码或点击链接
  → B 升级为高级会员
  → A 的邀请人数 +1
```

## 图片资源

项目需要以下图片资源，请放置在 `miniprogram/images/` 目录:

```
images/
├── tab-mall.png           # TabBar 商城图标
├── tab-mall-active.png
├── tab-benefits.png       # TabBar 福利图标
├── tab-benefits-active.png
├── tab-profile.png        # TabBar 我的图标
├── tab-profile-active.png
├── icon-search.png        # 搜索图标
├── icon-lock.png          # 锁图标
├── icon-clear.png         # 清除图标
├── icon-service.png       # 客服图标
├── avatar-default.png     # 默认头像
├── placeholder.png        # 占位图
├── empty-product.png      # 空商品
├── empty-order.png        # 空订单
├── empty-search.png       # 空搜索
├── order-pending.png      # 待付款图标
├── order-paid.png         # 待发货图标
├── order-shipped.png      # 待收货图标
├── order-completed.png    # 已完成图标
├── menu-address.png       # 地址菜单图标
├── menu-service.png       # 客服菜单图标
├── menu-about.png         # 关于菜单图标
├── benefit-discount.png   # 折扣权益图标
├── benefit-shipping.png   # 包邮权益图标
├── benefit-gift.png       # 礼包权益图标
└── benefit-service.png    # 客服权益图标
```

## 注意事项

1. **价格单位**: 数据库中价格以「分」为单位存储，前端展示时除以 100
2. **权限校验**: 所有涉及金额的操作必须在云函数中进行校验
3. **邀请码**: 6 位大写字母+数字，基于用户 ID 生成

## 后续开发建议

- [ ] 接入微信支付
- [ ] 添加购物车功能
- [ ] 商品规格 SKU
- [ ] 优惠券系统
- [ ] 海报生成
- [ ] 后台管理系统

## License

MIT
