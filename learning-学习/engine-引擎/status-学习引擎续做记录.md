# 学习引擎续做记录

更新时间：2026-04-10（北京时间）

## 今晚已完成

1. 打通了终端收件底座
   - 终端是唯一人工入口
   - 收件窗口固定为北京时间 `06:00 - 22:00`
   - `23:00` 后自动滚到下一批
   - 工作内容会被标记为 `excluded_work`

2. 打通了计划层
   - 已能从原始收件生成 [daily_learning_plan-每日学习计划.json](./state-状态/daily_learning_plan-每日学习计划.json)
   - 英语内容单独成期
   - 新闻和知识输入合并成一期
   - 待定内容进入 deferred

3. 打通了节目骨架层
   - 已能生成 [program_manifests-节目骨架](./state-状态/program_manifests-节目骨架/2026-04-11/index.json)
   - 每个节目都有结构、时长、来源材料、前置处理要求

4. 打通了写稿简报层
   - 已能生成 [episode_briefs-节目简报](./state-状态/episode_briefs-节目简报/2026-04-11/index.json)
   - 每个节目都有可直接喂给 AI 的 Markdown 写稿简报

5. 打通了最小反馈闭环
   - [record_feedback-录入反馈.py](./scripts-脚本/record_feedback-录入反馈.py) 已支持按北京时间写反馈
   - 会回写 `avg_feedback_score`
   - 会回写 `last_feedback_score`
   - 会回写 `last_feedback_at`
   - 会回写 `last_feedback_note`
   - 会更新 `weak_areas` 和 `mastered_concepts`

## 当前系统能做什么

现在已经可以正常进入“每日投递”模式：

1. 你在终端里分多次丢内容
2. 系统按北京自然日收件
3. 系统生成每日学习计划
4. 系统拆成英语节目和信息输入节目
5. 系统生成节目骨架
6. 系统生成写稿简报
7. 听完后可录入反馈并更新状态

## 当前还没做完的部分

离“自动生成成品播客”还差最后两层：

1. 音频生成接线层
   - 目标：把正式脚本接到现有 TTS / 播客生成链路

2. 正式公众号成稿层
   - 目标：把公众号推文草稿补成可直接发布的完整图文稿

## 明天继续时的直接入口

明天继续这个项目时，直接从下面这一步开始：

**下一步：实现“正式脚本 -> 播客音频”，同时完善“公众号草稿 -> 可发布图文稿”**

建议顺序：

1. 把 [podcast_scripts-播客脚本](./state-状态/podcast_scripts-播客脚本/2026-04-11/index.json) 接进现有 [generate_podcast-生成播客.py](./scripts-脚本/generate_podcast-生成播客.py)
2. 产出英语节目和每日输入节目的样例音频
3. 把 [wechat_articles-公众号推文](./state-状态/wechat_articles-公众号推文/2026-04-11/index.json) 从草稿扩成完整公众号图文
4. 用 [daily_delivery-每日交付](./state-状态/daily_delivery-每日交付/2026-04-11/README.md) 作为每天的统一交付入口

## 关键边界

这个项目只处理个人学习内容，不处理工作内容。

明确排除：
- 瑞幸咖啡
- 数据分析
- 业务运营
- AB 实验
- SQL / 报表 / 经营分析

## Git 状态

1. 今晚学习引擎改动已经本地 commit
   - commit: `f94283e`
   - message: `Build learning engine intake planning and feedback loop`

2. 远端 push 没成功
   - 不是学习引擎本身的问题
   - 是仓库里其他超大文件触发了 GitHub 限制
   - 当前本地代码和文件都已保存

## 明天我需要记住的事

1. 不再重新讨论入口，入口已经定死为终端
2. 不再重新讨论时区，统一按北京时间
3. 不再把工作内容混入学习项目
4. 直接进入“节目脚本生成层”实现
5. 输出层已经改成双产物：播客 + 公众号图文
