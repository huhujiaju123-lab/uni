# 预计算缓存策略 — podcast-viz

> 一次计算，无限次变现。热门播客预先跑完存云端，用户请求秒出结果，边际成本趋近于零。

## 一、策略概述

### 核心思路

```
┌──────────────────────────────────────────────────┐
│                  用户请求                          │
│            (小宇宙 Episode URL)                   │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  查云端缓存    │
              └──┬───────┬───┘
            命中 │       │ 未命中
                 ▼       ▼
          ┌──────────┐  ┌─────────────────────┐
          │ 直接返回   │  │ 加入队列，异步处理    │
          │ 成本 ≈ ¥0  │  │ Whisper + Qwen      │
          │ 响应 <1s   │  │ 完成后通知用户        │
          └──────────┘  └─────────────────────┘

┌──────────────────────────────────────────────────┐
│            后台预计算引擎（本地 Mac）                │
│  • 每日抓取小宇宙 TOP 100 新 episode               │
│  • faster-whisper 本地转录（免费）                  │
│  • Qwen 分析（¥0.05/集）                          │
│  • 结果同步至云端服务器                              │
└──────────────────────────────────────────────────┘
```

### 经济账

|  | 当前方案（Deepgram） | 预计算方案（Whisper 本地） |
|--|---------------------|------------------------|
| 转录成本/集 | ¥3.0 | ¥0 |
| AI 分析/集 | ¥0.05 | ¥0.05 |
| 每集边际成本 | ¥3.05 | ¥0.05 |
| 预计算 TOP 100 月增量（~250 集） | ¥762/月 | ¥12.5/月 |
| 缓存命中请求成本 | — | ¥0 |

### 缓存命中率预估

| 缓存范围 | 预估命中率 | 月预计算量 |
|---------|-----------|-----------|
| TOP 100 播客 | 60-70% | ~250 集 |
| TOP 100 + 热榜追踪 | 70-80% | ~300 集 |
| TOP 500 播客 | 80-85% | ~1,000 集 |

---

## 二、成本分析与降本路径（未来优化项）

> **当前状态**：仍使用 Deepgram API 转录，暂不切换。以下为调研结论，待未来提效降本时实施。

### 2.0.1 当前成本结构（Deepgram）

以实际跑过的 4 集播客回测：

| Episode | 播客 | 时长 | Deepgram 费 | AI 分析费 | 总成本 | Deepgram 占比 |
|---------|------|------|------------|----------|--------|-------------|
| EP.91 给年轻女孩的9条人生建议 | 自习室 | 77 分 44 秒 | ¥3.13 | ¥0.047 | ¥3.18 | 98.5% |
| EP.80 贝叶斯定理 | 自习室 | 74 分 47 秒 | ¥2.99 | ¥0（未分析） | ¥2.99 | 100% |
| Vol.232 达美乐 | 商业就是这样 | 37 分 58 秒 | ¥1.52 | ¥0.028 | ¥1.55 | 98.2% |
| EP.59 一生之敌 | 进步是一件性感的事 | 89 分 39 秒 | ¥3.58 | ¥0.053 | ¥3.63 | 98.5% |
| **合计** | | **280 分钟** | **¥11.22** | **¥0.13** | **¥11.35** | **98.9%** |

**结论：Deepgram 转录占边际成本 98%+，AI 分析（通义千问 qwen-plus）几乎免费。降本 = 替换 Deepgram。**

计费公式：
- Deepgram Nova-2：$0.0043/分钟（base）+ $0.0013/分钟（diarize）= **$0.0056/分钟**
- 通义千问 qwen-plus：输入 ¥0.0008/千token + 输出 ¥0.002/千token

### 2.0.2 Whisper vs Deepgram 关键对比

| 维度 | Deepgram Nova-2 | faster-whisper large-v3 |
|------|-----------------|------------------------|
| **中文质量** | 有已知 bug，质量不稳定 | CER ~4%，**更可靠** |
| **英文质量** | WER 5-7%，行业领先 | WER ~10-12% |
| **说话人识别** | 内置，开箱即用 | 需 WhisperX + pyannote，配置复杂 |
| **标点/分段** | Smart Formatting，质量好 | 中文标点质量一般，需后处理 |
| **速度（75分钟）** | ~1-2 分钟（API） | Mac M2: ~5-10 分钟 / T4 GPU: ~3-5 分钟 |
| **成本（75分钟）** | **¥3.0** | **¥0**（本地）/ ¥0.1-0.5（云 GPU） |

### 2.0.3 Whisper 部署方案评估

| 方案 | 速度 | 易用性 | 说话人识别 | 需 GPU | 推荐场景 |
|------|------|--------|-----------|--------|---------|
| **faster-whisper**（推荐） | 4x 加速 | 高 | 无 | 建议 | 生产部署首选 |
| WhisperX | 快+功能全 | 低 | 有 | 是 | 多人播客必选 |
| whisper.cpp | CPU 最快 | 中 | 无 | 否 | Mac 无 GPU 场景 |
| 原版 OpenAI Whisper | 慢 | 高 | 无 | 建议 | 仅原型验证 |

### 2.0.4 Mac 本地运行预估

| Mac 型号 | 模型 | 75 分钟播客耗时 |
|---------|------|---------------|
| M1 Pro 16GB | large-v3 INT8 | ~8-15 分钟 |
| M2 Pro/Max 32GB | large-v3 FP16 | ~5-10 分钟 |
| M3/M4 Pro | large-v3 FP16 | ~3-8 分钟 |
| Intel Mac | medium | ~30-60 分钟（不推荐跑 large） |
| **CPU 跑 large-v3** | — | **12-25 小时（不可行）** |

### 2.0.5 降本后的盈利空间变化

| 定价 | Deepgram 方案毛利 | Whisper 方案毛利 |
|------|------------------|-----------------|
| ¥5/集 | 40% | **90%+** |
| ¥10/集 | 70% | **97%+** |
| ¥3/集 | 0%（亏本） | **83%** |

**切换 Whisper 后，即使定价 ¥3/集也有 83% 毛利，定价空间彻底打开。**

### 2.0.6 实施前提

- [ ] Mac 上安装 faster-whisper + large-v3 模型（~3GB 下载）
- [ ] 输出格式适配（与现有 transcript.txt 格式兼容）
- [ ] 中文标点后处理方案
- [ ] 说话人识别方案（WhisperX or 暂不支持）
- [ ] 本地 → 云端同步机制

---

## 三、本地预计算引擎

### 2.1 技术选型：faster-whisper

选择 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 作为本地转录引擎：

| 维度 | faster-whisper | 原版 Whisper | whisper.cpp |
|------|---------------|-------------|-------------|
| 速度 | **4x 加速**（CTranslate2） | 基准 | CPU 最优 |
| 内存 | 比原版减少 50%（INT8） | 高 | 低 |
| Python 集成 | 原生 API | 原生 | 需 binding |
| 说话人识别 | 无（需配合 WhisperX） | 无 | 无 |
| 中文质量 | large-v3 CER ~4% | 同 | 同 |

**推荐配置**：faster-whisper + large-v3 模型 + Apple Silicon GPU 加速（mlx 或 CoreML）。

如需说话人识别（多人播客），后续可升级为 [WhisperX](https://github.com/m-bain/whisperX)（faster-whisper + pyannote 说话人分离）。

### 2.2 在 Mac 上的预估性能

| Mac 型号 | 模型 | 预估处理 75 分钟播客 | 说明 |
|---------|------|-------------------|------|
| M1 Pro 16GB | large-v3（INT8） | ~8-15 分钟 | Metal 加速 |
| M2 Pro/Max 32GB | large-v3（FP16） | ~5-10 分钟 | 统一内存充裕 |
| M3/M4 Pro | large-v3（FP16） | ~3-8 分钟 | 最新芯片 |
| Intel Mac | medium | ~30-60 分钟 | 不推荐跑 large |

预计算不追求实时，跑慢一点完全可以接受。250 集/月 ≈ 每天 8 集，Mac 开着后台跑即可。

### 2.3 输出格式兼容

**关键约束**：faster-whisper 的输出必须与现有 `transcribe.py`（Deepgram）的输出格式兼容，保证下游 `analyzer.py` 和 `generator.py` 无需修改。

现有 `transcript.txt` 格式（Deepgram 输出）：

```
[00:00:00 - 00:01:23] 说话人0
大家好，欢迎来到本期节目...

[00:01:23 - 00:03:45] 说话人1
今天我们来聊一个很有意思的话题...
```

faster-whisper 输出适配方案：

```python
from faster_whisper import WhisperModel

def transcribe_local(audio_path, output_dir, language="zh"):
    """本地 Whisper 转录，输出格式与 Deepgram 兼容"""
    model = WhisperModel("large-v3", device="auto", compute_type="auto")
    segments, info = model.transcribe(audio_path, language=language)

    lines = []
    for seg in segments:
        start = format_timestamp(seg.start)
        end = format_timestamp(seg.end)
        # 无说话人识别时统一为 "说话人0"
        lines.append(f"[{start} - {end}] 说话人0")
        lines.append(seg.text.strip())
        lines.append("")

    txt_path = output_dir / "transcript.txt"
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    # transcript.json 仅保留轻量版（不存 Deepgram 原始响应，省 9MB/集）
    json_data = {
        "metadata": {"duration": info.duration, "language": info.language},
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in segments
        ]
    }
    json_path = output_dir / "transcript.json"
    json_path.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    return txt_path
```

### 2.4 音频下载

Deepgram 支持直接传 URL 转录，但本地 Whisper 需要先下载音频文件。

```python
import httpx

def download_audio(audio_url, output_dir):
    """下载播客音频到本地"""
    audio_path = output_dir / "audio.mp3"
    if audio_path.exists():
        return audio_path
    with httpx.stream("GET", audio_url, follow_redirects=True, timeout=300) as r:
        with open(audio_path, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
    return audio_path
```

注意：音频文件较大（75 分钟 ≈ 70-100 MB），转录完成后应删除本地音频，只保留转录结果。

---

## 四、预计算流水线

### 3.1 整体流程

```
┌────────────────────────────────────────────────────────┐
│                   预计算调度器 (precompute.py)            │
│                                                        │
│  1. 抓取小宇宙热门列表 → 新 episode URL 列表              │
│  2. 过滤已处理的（本地 output/ 已有）                      │
│  3. 逐集处理：                                           │
│     a. fetch_metadata()          ← 复用现有 fetcher.py   │
│     b. download_audio()          ← 新增                  │
│     c. transcribe_local()        ← 新增（faster-whisper） │
│     d. analyze_transcript()      ← 复用现有 analyzer.py   │
│     e. render()                  ← 复用现有 generator.py   │
│  4. 同步结果至云端服务器                                    │
│  5. 清理本地音频文件                                       │
└────────────────────────────────────────────────────────┘
```

### 3.2 小宇宙热门列表获取

小宇宙没有公开的热门 API，可通过以下方式获取：

**方案 A：爬取 xyzrank.top 排行榜**（推荐）

[xyzrank.top](https://xyzrank.top/) 是第三方小宇宙排行榜，提供 JSON API，维护 TOP 播客列表。

```python
import httpx

def fetch_top_podcasts(limit=100):
    """从 xyzrank 获取热门播客列表"""
    resp = httpx.get("https://xyzrank.top/api/podcasts", params={"limit": limit})
    podcasts = resp.json()
    return [p["rss_url"] or p["xyz_url"] for p in podcasts]
```

**方案 B：爬取小宇宙发现页/热榜**

小宇宙 App 的发现页有编辑推荐和热门榜单，可通过抓包获取 API。需要维护登录态，稳定性较差。

**方案 C：维护人工播客列表**

初期最简单——手动维护一个 `top_podcasts.json`：

```json
[
  {"name": "文化有限", "xyz_id": "..."},
  {"name": "忽左忽右", "xyz_id": "..."},
  {"name": "商业就是这样", "xyz_id": "..."}
]
```

### 3.3 获取播客最新 episode

拿到播客主页 URL 后，需要获取其下所有/最新 episode 列表：

```python
def fetch_episode_list(podcast_url):
    """从小宇宙播客主页获取 episode 列表"""
    resp = httpx.get(podcast_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    episodes = []
    for link in soup.select('a[href*="/episode/"]'):
        href = link.get("href", "")
        episode_id = href.split("/episode/")[-1].split("?")[0]
        if is_valid_episode_id(episode_id):
            episodes.append({
                "id": episode_id,
                "url": f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"
            })
    return episodes
```

### 3.4 调度策略

```python
# precompute.py — 主调度逻辑

def run_daily():
    """每日预计算任务"""
    top_podcasts = load_podcast_list()  # 从 top_podcasts.json 或 xyzrank API

    for podcast in top_podcasts:
        episodes = fetch_episode_list(podcast["url"])
        for ep in episodes:
            if is_already_processed(ep["id"]):
                continue
            try:
                process_episode(ep["url"])  # 走本地 Whisper 流水线
                sync_to_cloud(ep["id"])     # 上传至云端服务器
                cleanup_audio(ep["id"])     # 删除本地音频
            except Exception as e:
                log_error(ep["id"], e)
                continue

    log_summary()  # 今日处理统计
```

调度方式（Mac 本地）：
- **简单方案**：`cron` 定时任务，每天凌晨运行
- **进阶方案**：`launchd` plist 守护进程，断点续传

```bash
# crontab -e
0 2 * * * cd /path/to/podcast-tool && python precompute.py >> logs/precompute.log 2>&1
```

---

## 四、云端同步与服务

### 4.1 同步方案

本地预计算完成后，将结果上传至腾讯云服务器（134.175.228.73）。

```bash
# 只同步用户可见的文件（不传 transcript.json 原始数据，省空间）
rsync -avz --include='*/' \
  --include='metadata.json' \
  --include='episode.json' \
  --include='visualization.html' \
  --exclude='*' \
  output/ root@134.175.228.73:/opt/podcast-viz-v2/output/
```

每集同步量：~80-110 KB（metadata + episode.json + HTML），极快。

### 4.2 云端存储规划

| 阶段 | 集数 | 存储量（仅成品） | 说明 |
|------|------|----------------|------|
| 初始冷启动 | 5,000 集 | ~500 MB | TOP 100 近 50 集 |
| 稳定运行 | 20,000 集 | ~2 GB | TOP 100 全量历史 |
| 月增量 | +250 集 | +25 MB | 日常增量 |

腾讯云轻量服务器磁盘通常 40-80 GB，完全够用。

### 4.3 服务端缓存逻辑改造

现有 `core.py` 的 `check_cache()` 已经能识别预计算的结果（因为文件结构完全一致），**无需改动**。

唯一需要新增的：区分「缓存命中」和「需要实时计算」的请求，用于计费和统计。

```python
def check_cache(url):
    """检查缓存，返回 (episode_id, source) 或 (None, None)"""
    episode_id = extract_episode_id(url)
    if episode_id:
        viz_path = OUTPUT_DIR / episode_id / "visualization.html"
        if viz_path.exists():
            return episode_id, "cache"    # 缓存命中，标记来源
    return None, None
```

---

## 五、本地 transcript.json 精简

现有 Deepgram 的 `transcript.json` 平均 9.7 MB/集（包含词级时间戳和完整 API 响应），**下游从未使用**（只用 transcript.txt）。

### 精简策略

| 方案 | 保留大小 | 说明 |
|------|---------|------|
| 完全不生成 | 0 | 下游不依赖，最省空间 |
| 轻量版（推荐） | ~50 KB | 仅保留段级时间戳，备用 |
| 原始版 | ~10 MB | 当前状态，无必要 |

轻量版 transcript.json 结构：

```json
{
  "metadata": {
    "duration": 4664,
    "language": "zh",
    "engine": "faster-whisper",
    "model": "large-v3"
  },
  "segments": [
    {"start": 0.0, "end": 83.2, "text": "大家好..."},
    {"start": 83.2, "end": 165.8, "text": "今天..."}
  ]
}
```

---

## 六、实现阶段

### Phase 1：Whisper 本地转录集成（替代 Deepgram）

**目标**：在现有流水线中支持 Whisper 转录，与 Deepgram 并存，可切换。

**改动范围**：
- 新增 `transcribe_local.py`：faster-whisper 转录，输出格式兼容 transcript.txt
- 修改 `core.py`：增加转录引擎选择逻辑（环境变量 `TRANSCRIBE_ENGINE=whisper|deepgram`）
- 新增依赖：`faster-whisper>=1.0.0`

**验收标准**：
- 本地 Mac 能跑通完整流水线（URL → 可视化 HTML）
- 输出质量与 Deepgram 版本对比，中文准确率可接受

### Phase 2：预计算调度器

**目标**：自动化批量预计算热门播客。

**改动范围**：
- 新增 `precompute.py`：调度器主程序
- 新增 `top_podcasts.json`：热门播客列表（手动维护）
- 新增 `sync.sh`：rsync 同步脚本

**验收标准**：
- 能一键跑完指定播客列表的全部 episode
- 支持断点续传（已有 transcript.txt 的跳过转录）
- 结果能 rsync 到云端且被线上服务正确识别

### Phase 3：云端服务改造

**目标**：区分缓存命中和实时计算，支持计费统计。

**改动范围**：
- 修改 `core.py`：`check_cache()` 返回命中来源
- 新增请求日志：记录每次请求的 episode_id、是否命中缓存、处理耗时
- 新增统计接口：缓存命中率、热门 episode 排行

### Phase 4：说话人识别（可选）

**目标**：多人播客支持区分说话人。

**改动范围**：
- 从 faster-whisper 升级为 WhisperX
- 集成 pyannote-audio 说话人分离
- transcript.txt 输出区分不同说话人

---

## 七、风险与注意事项

### 小宇宙反爬

- 批量抓取元数据和音频可能触发风控
- 对策：控制频率（每集间隔 30s+），使用随机 User-Agent，必要时走代理

### 音频版权

- 预计算本质上是下载并处理他人的音频内容
- 对策：只存储分析结果（episode.json + HTML），不存储/分发原始音频
- transcript.txt 是否构成侵权存在灰色地带，建议只保留 AI 分析后的结构化内容

### Whisper 中文标点

- Whisper 的中文标点质量不如 Deepgram Smart Formatting
- 对策：后处理标点修正（规则 + 简单 NLP），或交给下游 AI 分析时自动修正

### Mac 长时间运行

- 预计算每天跑 8 集 × 10 分钟 ≈ 80 分钟 GPU 满载
- 对策：使用 `caffeinate` 防止休眠，设置温度监控

```bash
caffeinate -i python precompute.py
```

---

## 八、文件清单（新增/修改）

```
podcast-tool/
├── transcribe_local.py    # [新增] faster-whisper 本地转录
├── precompute.py          # [新增] 预计算调度器
├── top_podcasts.json      # [新增] 热门播客列表
├── sync.sh                # [新增] 云端同步脚本
├── core.py                # [修改] 转录引擎切换 + 缓存来源标记
├── requirements.txt       # [修改] 添加 faster-whisper 依赖
└── PRECOMPUTE_STRATEGY.md # [本文档]
```
