# meeting-codex-inbox-会议上下文

用途：把飞书会议和妙记整理成 Codex 可继续使用的上下文材料。

## 工作流

1. 扫描指定时间范围内的飞书日程。
2. 对“我创建 / 我有编辑权限”的飞书 VC 会议，支持开启自动录制。
3. 对“别人创建、我只是参会”的会议，只做会后妙记发现，不强行录制。
4. 找到妙记后，拉取 summary / chapter / todo / keyword / transcript。
5. 生成 Codex context Markdown，保存到 `contexts/`。
6. 生成桥接 AI 助手推送稿，保存到 `bridge-outbox/`。
7. 生成可执行任务入口，保存到 `task-prompts/`。
8. 可选：生成飞书 IM 推送稿，保存到 `feishu-push-outbox/`，并推送到个人或群聊。
9. 没找到妙记的会议，记录到 `pending-missing-minutes.md`，用于后续向 owner 要权限或链接。

## 桥接 AI 助手链路

目标流程：

```text
会议结束
→ 发现/收到妙记
→ 整理 Codex context
→ 飞书 IM 推送会后总结
→ 生成飞书任务
→ 飞书任务自动提醒/下发
→ Codex 执行
```

当前安全实现：

- 自动化脚本默认只生成 `bridge-outbox/*.md` 和 `feishu-push-outbox/*.md`。
- 飞书 IM 推送默认 dry-run；显式传 `--apply-push` 才会真实发送。
- 自动化脚本会生成 `task-outbox/*.json` 作为飞书任务 payload 草稿。
- 默认只对飞书任务创建做 dry-run；显式传 `--apply-task` 才会真实创建飞书任务。
- `claude-to-im` 桥接已运行时，你可以把 outbox 内容发给桥接 AI 助手，让它继续执行。

飞书推送内容结构：

- 会议标题和会议时间
- 核心信息：来自妙记 summary / chapter
- 我可以帮你推进：待办跟进、行动清单、飞书纪要、项目上下文
- 入口：飞书妙记链接、Codex context、任务入口

## 飞书任务能力

这里使用的是飞书 **任务中心 / Task v2**：

- `lark-cli task +create`：创建任务
- `task:task:write` / `task:task:writeonly`：创建任务所需权限
- 任务可分配给用户或应用；当前默认分配给当前登录用户“我”
- 任务描述里会写入 Codex context、妙记 token、推荐执行动作和安全边界

## 安全默认值

- 默认 dry-run，不会真实修改日程录制设置。
- 只有显式传 `--apply-recording` 才会写入 `auto_record=true`。
- 不会给别人创建影子会议，不会偷偷录系统音频，不会绕过 owner 权限。

## 常用命令

预览今天会议，不真实改录制：

```bash
python3 scripts/meeting_codex_sync.py --start 2026-07-17 --end 2026-07-18
```

对可编辑会议真实开启自动录制，并尝试拉取已有妙记：

```bash
python3 scripts/meeting_codex_sync.py --start 2026-07-17 --end 2026-07-18 --apply-recording --process-minutes
```

创建飞书任务 dry-run：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题" --create-task
```

真实创建飞书任务：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题" --create-task --apply-task
```

生成飞书 IM 推送 dry-run：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题" --push-feishu
```

真实推送给当前登录用户：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题" --push-feishu --apply-push
```

真实推送到指定群聊：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题" --push-feishu --apply-push --push-chat-id oc_xxxx
```

扫描当天会议、拉取妙记、创建任务并推送：

```bash
python3 scripts/meeting_codex_sync.py --start 2026-07-17 --end 2026-07-18 --apply-recording --process-minutes --create-task --apply-task --push-feishu --apply-push
```

已有妙记 token 时，直接生成 Codex context：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题"
```

只生成 context，不生成桥接推送稿：

```bash
python3 scripts/meeting_codex_sync.py --minute-token obcnxxxx --title "会议标题" --no-bridge-handoff
```

## 可能需要的飞书授权

按日程查询录制产物需要：

```bash
lark-cli auth login --scope "vc:record:readonly"
```

搜索妙记候选需要：

```bash
lark-cli auth login --scope "minutes:minutes.search:read"
```

创建/更新日程自动录制需要日历更新权限，且你必须对对应日程有编辑权限。

创建飞书任务需要：

```bash
lark-cli auth login --scope "task:task:write"
```

飞书 IM 以 bot 身份推送时，需要在飞书开发者后台开通 bot scope：

```bash
im:message:send_as_bot
```

若改用 `--push-as user`，需要用户身份发消息权限：

```bash
lark-cli auth login --scope "im:message.send_as_user"
lark-cli auth login --scope "im:message"
```
