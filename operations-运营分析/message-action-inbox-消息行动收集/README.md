# message-action-inbox-消息行动收集

用途：定时读取指定飞书群消息，识别和李宵霄相关的待办、日程候选和需要跟进的信息。

## 当前监听范围

| 群名 | chat_id | 用途 |
|---|---|---|
| 美国业务部 | `oc_3d2c0d335d8175cea3f3fd21456f9a46` | 业务主群 |
| 美国数据小群 | `oc_88d5b162c1b9a12d38a781a64403f827` | 数据协作小群 |

## 当前模式

默认是增量扫描 + 飞书卡片审核模式：

- 增量读取新消息。
- 生成候选事项。
- 写入本地 Markdown / JSON。
- 定时发送飞书交互卡片给 owner。
- 支持接收交互卡片按钮回调，并把决策写入本地状态。
- 点击“建 Todo”后，才会真实创建飞书 Todo。
- 点击“建日程”后，只有原消息能解析出明确时间时才会真实创建飞书日程；否则只记录请求。
- 点击“忽略 / 稍后”只记录本地决策。

## 运行

增量扫描两个指定群的新消息：

```bash
python3 scripts/hourly_message_action_scan.py
```

默认策略：

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `probe_page_size` | 1 | 每个群先只读取最新 1 条，用于判断有没有新增 |
| `page_size` | 20 | 确认有新增后，每页读取 20 条 |
| `limit_per_chat` | 100 | 单次每群最多读取 100 条新消息，防止长时间离线后无限拉取 |
| `include_processed` | false | 遇到已处理 message_id 立即停止 |

手动回放最近 100 条历史消息：

```bash
python3 scripts/hourly_message_action_scan.py --limit 100 --include-processed
```

扫描后生成：

```text
outputs/digests/
outputs/candidates/
outputs/cards/
state/state.json
state/candidates.json
state/decisions.json
```

生成并真实发送交互卡片给 owner：

```bash
python3 scripts/hourly_message_action_scan.py --limit 100 --send-card
```

注意：`--send-card` 会产生飞书消息，属于外部可见写操作；当前定时任务已启用这个参数。

## 定时推送

当前 launchd 定时任务：

| 配置项 | 值 |
|---|---|
| Label | `com.xiaoxiao.message-action-inbox.hourly` |
| 命令 | `python3 scripts/hourly_message_action_scan.py --limit 100 --send-card` |
| 推送时间 | 每天 22:00、00:00、02:00、04:00 |
| 推送对象 | owner 的飞书机器人单聊 |
| 空结果 | 也会推送 0 候选卡片 |

## 交互审核链路

当前推荐链路：

```text
每小时扫描群消息
→ 只读取新增消息，遇到已处理消息即停止
→ 生成候选事项
→ 生成飞书交互卡片 JSON
→ 用户在卡片上点击 建 Todo / 忽略 / 稍后 / 建日程
→ card.action.trigger 监听器记录决策
→ 建 Todo / 建日程 按钮触发对应飞书动作
→ 处理结果通过单独飞书消息反馈到同一会话
```

本地测试卡片回调处理：

```bash
printf '%s\n' '{"event_id":"test_event_1","operator_id":"ou_17aa56f8a8a7650051d1fed93a956831","action_value":"{\"source\":\"message-action-inbox\",\"candidate_id\":\"候选ID\",\"action\":\"ignore\"}"}' \
  | python3 scripts/card_action_listener.py --stdin --max-events 1
```

监听飞书卡片按钮事件：

```bash
python3 scripts/card_action_listener.py --timeout 60s
```

前置条件：飞书开发者后台需要启用 `card.action.trigger` 事件回调；否则监听器可以启动，但收不到按钮事件。

## 识别规则

| 类型 | 识别方式 | 输出 |
|---|---|---|
| 明确提到我 | mentions 包含我的 open_id | 高置信待办 |
| 我主动承诺 | 我发送“我去 / 我来 / 明天 / 和产品确认 / 看一下”等 | 待办候选 |
| 问题未闭环 | 我提出问题，后续没有明确回复 | 跟进候选 |
| 时间安排 | 消息中出现时间 + 对齐/会议/沟通 | 日程候选 |
| 普通讨论 | 没有 owner 或动作 | 只进入上下文，不生成待办 |

## Token / 调用节约策略

| 场景 | 处理方式 |
|---|---|
| 每小时定时任务 | 先每群探测最新 1 条，再决定是否继续 |
| 没有新增消息 | 每群只读取 1 条后停止，不生成大上下文 |
| 有少量新增消息 | 只分析新增消息 |
| 有大量新增消息 | 最多读取 `limit_per_chat` 条，避免异常消耗 |
| 需要复盘历史 | 手动使用 `--include-processed`，不放进默认定时任务 |

## 安全边界

- 不读取未配置群。
- 定时任务只向 owner 单聊发送候选审核卡片。
- 不修改群消息。
- 状态文件只记录已处理 message_id / position、候选摘要和用户决策。
- 不在扫描阶段自动创建 Todo / 日程。
- 只有用户点击“建 Todo / 建日程”按钮后，监听器才执行对应飞书写操作。
- 当前 Feishu 同一个 app 只允许一个事件长连接；为了接收卡片按钮回调，`Claude-to-IM` 桥接服务当前保持暂停。
