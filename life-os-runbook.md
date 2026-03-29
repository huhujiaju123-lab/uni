# LifeOS Runbook

## 每日流程（10-15 分钟）

1. 早晨（Rem）
   - 输入触发：`早上好` 或 `/rem`
   - 产出：今日 1 个焦点，写入 `focus-queue.md`

2. 晚间（Alfred）
   - 输入触发：`复盘` 或 `/alfred`
   - 产出：
     - 精力评分（1-10）
     - 1-3 个标签
     - 简短备注
     - 追加到 `energy-log.jsonl`

## 每周流程（30-45 分钟）

1. 触发 Tyrion：`周策略` 或 `/tyrion`
2. 复盘输出包含：
   - 精力均值与走势
   - 高分/低分触发因素
   - 本周变化对比
   - 下周关键问题（1个）

## 同步流程（learning-engine）

1. 执行：
   - `python3 learning-engine/scripts-脚本/sync_lifeos-同步精力数据.py`
2. 验证：
   - 查看 `learning-engine/state-状态/learner_state-学习者状态.json`
   - 核对 `energy.today_score / today_tags / weekly_avg` 是否更新

## 异常处理

1. `energy-log.jsonl` 不存在
   - 先完成一次 Alfred 复盘，生成首条记录
2. 同步报错
   - 检查脚本路径和状态文件路径是否存在
3. 周报无数据
   - 确保最近 7-14 天至少有连续日志

