# 小红书笔记抓取工具 v3.0

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Chrome](https://img.shields.io/badge/Chrome-Extension-orange)

一键启动自动监控，智能抓取小红书笔记内容和评论，支持批量导出CSV。省时高效，完全本地存储。

## ✨ 核心特性

### 🚀 全自动监控
- **一键启动**：点击一次，全程自动抓取
- **智能识别**：自动识别列表页和详情页
- **实时保存**：数据自动保存，无需手动操作
- **URL监控**：自动检测页面切换，无缝抓取

### 📋 双模式抓取

#### 列表页模式
- 自动抓取所有笔记卡片
- 监控页面滚动，新笔记自动记录
- 抓取内容：作者、点赞数、标题、链接

#### 详情页模式
- 打开笔记自动抓取
- 完整记录笔记正文
- 自动收集所有评论
- 评论详情：用户名、内容、点赞数

### 📊 数据管理
- 智能去重，避免重复
- 分类展示：列表数据和详情数据
- 一键导出CSV文件
- 本地存储，数据安全

## 🎯 使用方法

### 快速开始

1. **安装扩展**
   - 下载或克隆本项目
   - 打开 Chrome 浏览器
   - 访问 `chrome://extensions/`
   - 开启"开发者模式"
   - 点击"加载已解压的扩展程序"
   - 选择项目文件夹

2. **启动监控**
   - 打开小红书网站
   - 点击扩展图标
   - 点击"🚀 启动自动监控"

3. **开始浏览**
   - 正常浏览小红书
   - 所有笔记自动抓取
   - 数据实时保存

4. **导出数据**
   - 点击扩展图标
   - 查看已抓取数据
   - 点击"下载所有数据"

## 📁 项目结构

```
xiaohongshu-crawler/
├── manifest.json           # 扩展配置文件
├── background.js           # Service Worker 后台脚本
├── content/
│   └── content.js         # 内容脚本（抓取逻辑）
├── popup/
│   ├── popup.html         # 弹窗界面
│   ├── popup.js           # 弹窗逻辑
│   └── popup.css          # 弹窗样式
├── icons/
│   ├── icon-generator.html # 图标生成器
│   ├── icon16.png         # 16x16 图标
│   ├── icon32.png         # 32x32 图标
│   ├── icon48.png         # 48x48 图标
│   └── icon128.png        # 128x128 图标
├── PRIVACY_POLICY.md      # 隐私政策
├── STORE_LISTING.md       # 商店列表说明
├── 上架指南.md            # Chrome Web Store 上架指南
├── 使用说明.md            # 详细使用文档
├── 调试指南.md            # 调试和问题排查
├── v3.0更新说明.md        # 版本更新说明
├── package.sh             # 打包脚本
└── README.md              # 本文件
```

## 🔧 开发指南

### 环境要求
- Chrome 浏览器（版本 88+）
- 文本编辑器（推荐 VS Code）

### 本地开发

1. **克隆项目**
```bash
git clone https://github.com/yourusername/xiaohongshu-crawler.git
cd xiaohongshu-crawler
```

2. **加载扩展**
- 打开 `chrome://extensions/`
- 启用"开发者模式"
- 点击"加载已解压的扩展程序"
- 选择项目目录

3. **修改代码**
- 编辑相关文件
- 在 `chrome://extensions/` 中点击刷新按钮
- 刷新小红书页面测试

### 打包发布

1. **生成图标**
```bash
# 在浏览器中打开
open icons/icon-generator.html
# 下载生成的图标
```

2. **打包扩展**
```bash
# 使用打包脚本
./package.sh

# 或手动打包
zip -r xiaohongshu-crawler.zip \
  manifest.json \
  background.js \
  content/ \
  popup/ \
  icons/ \
  -x "*.DS_Store"
```

3. **上架 Chrome Web Store**
- 参考 `上架指南.md`

## 📖 文档

- [使用说明](./使用说明.md) - 完整的功能介绍和使用方法
- [调试指南](./调试指南.md) - 问题排查和调试技巧
- [v3.0更新说明](./v3.0更新说明.md) - 最新版本更新内容
- [上架指南](./上架指南.md) - Chrome Web Store 上架步骤
- [隐私政策](./PRIVACY_POLICY.md) - 隐私保护说明
- [商店列表](./STORE_LISTING.md) - 应用商店信息

## 🔒 隐私与安全

### 数据安全承诺
- ✅ **100%本地存储** - 所有数据保存在您的浏览器本地
- ✅ **零数据上传** - 不上传任何数据到服务器
- ✅ **无追踪** - 不使用任何第三方分析或追踪
- ✅ **开源透明** - 代码完全公开，可审查

### 权限说明
- **storage** - 用于本地存储抓取的数据
- **activeTab** - 用于读取当前小红书页面内容
- **xiaohongshu.com** - 仅在小红书网站上运行

详见：[隐私政策](./PRIVACY_POLICY.md)

## 🆕 版本历史

### v3.0.0 (2024-12-11)
- 🎉 全新自动监控系统
- ✨ 智能双模式抓取（列表+详情）
- 💅 优化评论显示格式
- 🚀 一键启动，全程自动
- 📱 添加Service Worker后台处理
- 🔄 实时URL变化检测

### v2.1 (2024-12-10)
- 🐛 修复详情页抓取bug
- 💬 改进DOM选择器策略
- 📝 添加详细日志输出

### v2.0 (2024-12-09)
- ✨ 新增详情页抓取功能
- 💬 新增评论抓取功能
- 🎨 优化UI界面

### v1.0 (2024-12-08)
- 🎉 首个版本发布
- 📋 基础列表页抓取功能
- 📥 CSV导出功能

## 🤝 贡献

欢迎提交问题和功能建议！

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com

## 🙏 致谢

感谢所有使用和支持本项目的用户！

## 📞 支持

如有问题或建议：
- 提交 [GitHub Issues](https://github.com/yourusername/xiaohongshu-crawler/issues)
- 发送邮件至 your.email@example.com

---

**⭐ 如果这个项目对你有帮助，请给个星标！**

**💡 立即开始使用，让小红书内容收集变得简单高效！**
