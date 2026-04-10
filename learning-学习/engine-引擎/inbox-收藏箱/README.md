# 收藏箱 — 学习收件后台原始层

这个目录不再作为你的人工入口。

从现在开始：
- **唯一人工入口**：终端会话
- **唯一启动口令**：`开启学习收件`
- **唯一结束口令**：`结束学习收件`

你在终端里分多次丢给我的内容，会由脚本写入这个目录。

## 收件时间规则（北京时间）

- 开窗：`06:00`
- 软截点：`22:00`
- 硬截点：`23:00`
- 一个批次按北京自然日组织

规则说明：
- `06:00 - 22:00` 持续收件
- `22:00` 前进入当天主批次
- `22:00 - 23:00` 预留给处理准备
- `23:00` 后的新内容自动滚到下一批
- 你中途说 `结束学习收件`，当天批次会提前冻结

## 目录结构

```text
inbox-收藏箱/
├── README.md
├── batches-批次/           # 每天一个批次元信息 JSON
├── raw-原始收件/          # 每天一个 JSONL，逐条记录收件内容
└── assets-附件/            # 本地复制的文件/图片附件
```

## 支持的输入类型

- URL
  - 公众号
  - YouTube
  - B站
  - 小宇宙
- 文件路径
  - PDF
  - MD
  - TXT
  - 图片
- 直接粘贴文本
- 图片附件

## 频道建议

- `english-coach`：英语学习
- `news-daily`：新闻输入
- `learning-digest`：知识输入
- `pending`：待定

你不需要先分类；默认先收，再判断。

## 工作内容排除规则

以下内容不进入这个学习项目：
- 瑞幸咖啡
- 数据分析
- 业务运营
- AB 实验
- SQL / 报表 / 经营分析

这类内容会被标记为 `excluded_work`，不会进入学习类 Obsidian 记录。

## 脚本入口

```bash
# 开启当天收件
python scripts-脚本/capture_terminal_intake-终端收件.py start

# 添加一条 URL
python scripts-脚本/capture_terminal_intake-终端收件.py add \
  --source-type url \
  --source-value "https://example.com"

# 添加一条文本，并指定英语频道
python scripts-脚本/capture_terminal_intake-终端收件.py add \
  --source-type text \
  --source-value "A note about English shadowing" \
  --channel 英语

# 查看当前批次状态
python scripts-脚本/capture_terminal_intake-终端收件.py status

# 结束当天收件
python scripts-脚本/capture_terminal_intake-终端收件.py close

# 渲染 Obsidian 当天收件记录
python scripts-脚本/render_obsidian_intake-渲染收件记录.py
```
