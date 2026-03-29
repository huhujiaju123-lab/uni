/**
 * runPipeline 云函数（长时间运行）
 * 由 processEpisode 异步触发，执行实际的处理流水线
 *
 * 输入: { taskId, url, episodeId }
 *
 * 环境变量（在云开发控制台配置）：
 *   DEEPGRAM_API_KEY  — Deepgram 转录 API Key
 *   DASHSCOPE_API_KEY — 通义千问 API Key
 */
const cloud = require('wx-server-sdk')
const axios = require('axios')
const cheerio = require('cheerio')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

// ===== 配置 =====
const QWEN_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
const QWEN_MODEL = 'qwen-plus'
const DEEPGRAM_API = 'https://api.deepgram.com/v1/listen'

const USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

// ===== 主入口 =====
exports.main = async (event, context) => {
  const { taskId, url, episodeId } = event
  if (!taskId || !url) {
    return { error: '缺少 taskId 或 url' }
  }

  try {
    // Step 1: 获取元数据
    await updateTaskStep(taskId, 0, 'running', '')
    const metadata = await fetchMetadata(url)
    await updateTaskStep(taskId, 0, 'done', metadata.title)
    await updateTaskStep(taskId, 1, 'running', '转录中（预计 2-5 分钟）...')
    await db.collection('tasks').doc(taskId).update({
      data: { metadata: { title: metadata.title, cover_url: metadata.cover_url, podcast_name: metadata.podcast_name } }
    })

    // Step 2: 转录
    const transcript = await transcribeAudio(metadata.audio_url)
    await updateTaskStep(taskId, 1, 'done', `${transcript.charCount} 字`)
    await updateTaskStep(taskId, 2, 'running', '分析中（预计 1-2 分钟）...')

    // Step 3: AI 分析（两个 prompt 并发）
    const episode = await analyzeContent(transcript.text, metadata)
    await updateTaskStep(taskId, 2, 'done', `${(episode.sections || []).length} 个章节`)
    await updateTaskStep(taskId, 3, 'running', '存储中...')

    // Step 4: 存入数据库
    const doc = await db.collection('episodes').add({
      data: {
        episode_id: episodeId,
        ...episode,
        source_url: url,
        created_at: db.serverDate()
      }
    })

    await updateTaskStep(taskId, 3, 'done', '')
    await db.collection('tasks').doc(taskId).update({
      data: { status: 'done', done: true, episode_id: doc._id }
    })

    return { success: true, episodeId: doc._id }
  } catch (err) {
    console.error('runPipeline error:', err)
    await db.collection('tasks').doc(taskId).update({
      data: { status: 'error', error: err.message || '处理失败', done: true }
    })
    return { error: err.message || '处理失败' }
  }
}

// ===== 辅助函数 =====

async function updateTaskStep(taskId, stepIndex, status, detail) {
  await db.collection('tasks').doc(taskId).update({
    data: {
      [`steps.${stepIndex}.status`]: status,
      [`steps.${stepIndex}.detail`]: detail || ''
    }
  })
}

// ===== Step 1: 获取小宇宙元数据 =====

async function fetchMetadata(url) {
  const res = await axios.get(url, {
    headers: { 'User-Agent': USER_AGENT, 'Accept-Language': 'zh-CN,zh;q=0.9' },
    timeout: 30000,
    maxRedirects: 5
  })

  const $ = cheerio.load(res.data)
  const getOg = (prop) => $(`meta[property="${prop}"]`).attr('content') || ''

  let title = getOg('og:title')
  let audioUrl = getOg('og:audio')
  let coverUrl = getOg('og:image')
  let podcastName = getOg('og:site_name')
  const description = getOg('og:description')

  // 备选：从 JSON-LD 提取音频
  if (!audioUrl) {
    $('script[type="application/ld+json"]').each((_, el) => {
      try {
        const data = JSON.parse($(el).html())
        if (data.contentUrl) audioUrl = data.contentUrl
        if (data['@graph']) {
          for (const item of data['@graph']) {
            if (item.contentUrl) audioUrl = item.contentUrl
          }
        }
      } catch (e) {}
    })
  }

  // 备选：podcastName 从 JSON-LD 或 title
  if (!podcastName) {
    $('script[type="application/ld+json"]').each((_, el) => {
      try {
        const data = JSON.parse($(el).html())
        if (data.partOfSeries && data.partOfSeries.name) podcastName = data.partOfSeries.name
      } catch (e) {}
    })
  }
  if (!podcastName) {
    const titleText = $('title').text().trim()
    const dashIdx = titleText.lastIndexOf(' - ')
    if (dashIdx > 0) podcastName = titleText.substring(dashIdx + 3).trim()
  }

  if (!title) {
    title = $('title').text().trim()
  }

  // 备选：正则匹配音频链接
  if (!audioUrl) {
    const audioMatch = res.data.match(/https:\/\/media\.xyzcdn\.net\/[^\s"']+\.m4a/)
    if (audioMatch) audioUrl = audioMatch[0]
  }

  // 从 JSON-LD 提取时长
  let durationSec = 0
  $('script[type="application/ld+json"]').each((_, el) => {
    try {
      const data = JSON.parse($(el).html())
      const tr = data.timeRequired || (data['@graph'] || []).find(i => i.timeRequired)?.timeRequired
      if (tr) {
        const m = tr.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/)
        if (m) {
          durationSec = (parseInt(m[1] || 0)) * 3600 + (parseInt(m[2] || 0)) * 60 + (parseInt(m[3] || 0))
        }
      }
    } catch (e) {}
  })

  if (!audioUrl) {
    throw new Error('未找到音频直链，可能为付费内容')
  }

  return {
    episode_id: url.match(/episode\/([a-f0-9]+)/)[1],
    title,
    description,
    audio_url: audioUrl,
    cover_url: coverUrl,
    podcast_name: podcastName,
    source_url: url,
    duration_sec: durationSec
  }
}

// ===== Step 2: Deepgram 音频转录 =====

async function transcribeAudio(audioUrl) {
  const apiKey = process.env.DEEPGRAM_API_KEY
  if (!apiKey) throw new Error('DEEPGRAM_API_KEY 环境变量未设置')

  const params = new URLSearchParams({
    model: 'nova-2',
    language: 'zh',
    smart_format: 'true',
    punctuate: 'true',
    paragraphs: 'true',
    diarize: 'true'
  })

  const res = await axios.post(
    `${DEEPGRAM_API}?${params.toString()}`,
    { url: audioUrl },
    {
      headers: {
        'Authorization': `Token ${apiKey}`,
        'Content-Type': 'application/json'
      },
      timeout: 600000
    }
  )

  const result = res.data
  const channels = result?.results?.channels || []
  if (!channels.length) throw new Error('转录结果为空')

  const alt = channels[0].alternatives?.[0] || {}
  const transcript = alt.transcript || ''
  const paragraphs = alt.paragraphs?.paragraphs || []

  let formattedText = ''
  if (paragraphs.length > 0) {
    for (const para of paragraphs) {
      const speaker = para.speaker ?? '?'
      const startTs = formatTimestamp(para.start || 0)
      const endTs = formatTimestamp(para.end || 0)
      const sentences = para.sentences || []
      const text = sentences.map(s => s.text || '').join('')
      formattedText += `[${startTs} - ${endTs}] 说话人${speaker}\n${text}\n\n`
    }
  } else {
    formattedText = transcript
  }

  return {
    text: formattedText,
    charCount: transcript.length,
    paraCount: paragraphs.length,
    confidence: alt.confidence || 0,
    durationSec: result?.metadata?.duration || 0
  }
}

function formatTimestamp(seconds) {
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// ===== Step 3: AI 内容分析（通义千问） =====

const SYSTEM_PROMPT = `你是一位播客内容整理编辑，负责将播客转录文本整理为结构化内容。

## 核心原则

1. **忠于原文**：所有观点、数据、概念、案例必须来自播客原文，禁止编造、推测或补充原文没有的内容
2. **保留语感**：保持播客原有的表达风格和语气，可以精简和重组句子，但读者应能感受到原作的影子，避免学术化改写
3. **直接陈述**：大部分观点直接写结论，不用"他们认为""嘉宾提到"等间接引述；仅在需要区分不同说话人立场时标注人名
4. **区分原文与延伸**：原文中的观点正常呈现；编辑补充的背景知识或延伸解读必须在 extended_reading 模块中，不要混入 sections/arguments/key_concepts

你的任务：分析播客转录文本，输出严格的 JSON 格式数据。

## 输出格式

必须输出合法的 JSON，不加任何多余文字，严格按照以下结构：

{
  "meta": { "podcast_name": "", "episode_number": null, "title": "", "subtitle": "", "total_duration_sec": 0, "language": "zh" },
  "participants": [{ "id": "host1", "name": "", "role": "host", "bio": "" }],
  "featured_work": { "type": "book", "title": "", "author": "" },
  "sections": [{
    "id": "", "title": "", "subtitle": "", "start_sec": 0, "end_sec": 0, "is_ad": false,
    "key_points": [], "quotes": [], "stories": [{ "narrator_id": "", "text": "" }],
    "key_points_grouped": [{ "label": "", "visual_type": "list", "points": [{ "text": "", "detail": "" }] }],
    "diagram": { "type": "flow|comparison|icon-list|slope|layers|timeline|cycle|matrix|stats", "title": "", "steps": [] },
    "section_context": ""
  }],
  "core_quotes": [],
  "recommendations": [],
  "quiz": { "intro": "", "questions": [{ "id": "q1", "text": "", "type": "choice", "options": [{ "label": "", "score": 0 }] }], "result_levels": [{ "max_avg_score": 1.0, "level_label": "", "description": "" }] },
  "content_overview": { "one_sentence_summary": "", "content_blocks": [{ "id": "", "title": "", "summary": "", "section_ids": [], "icon": "" }], "block_connections": [{ "from": "", "to": "", "relation": "", "description": "" }] },
  "arguments": [{ "id": "", "claim": "", "evidence_type": "", "evidence": "", "source_section_id": "", "strength": "strong" }],
  "key_concepts": [{ "id": "", "term": "", "definition": "", "explanation": "", "examples": [], "related_concepts": [], "source_section_id": "" }],
  "extended_reading": [{ "id": "", "topic": "", "context": "", "deep_dive": "", "related_concept_ids": [], "further_resources": "" }],
  "mind_map": { "central_theme": "", "nodes": [{ "id": "", "label": "", "type": "theme", "parent_id": null, "detail": "" }] }
}

## 注意事项

1. 时间戳：[MM:SS - MM:SS] 转为秒数
2. 章节划分：按话题自然划分，6-10 个。广告标 is_ad: true
3. 参与者姓名只能从标题/简介/转录中提取，禁止猜测
4. key_points：每章 3-6 条原文观点
5. core_quotes：全集最精彩 5-10 句原话
6. quiz：5 道与主题相关的自测题
7. key_points_grouped 的 text 必须是完整观点句（20-50字）
8. diagram：3-5 个，包含完整数据字段
9. content_overview 的 block_connections 必须填 relation 和 description
10. arguments：8-12 个核心观点
11. key_concepts：6-10 个反复出现的概念
12. mind_map：2-3 层树状结构
13. 输出纯 JSON，不要加代码块标记`

const SYSTEM_PROMPT_EXTENDED = `你是播客内容整理编辑。基于播客转录文本，输出2个扩展模块的 JSON 数据。

必须输出合法 JSON，顶层包含 detailed_timeline 和 knowledge_cards 两个字段。

detailed_timeline: 每5-10分钟一段，narrative 50-100字，像备忘录不像书评
knowledge_cards: 12-20张，extension 可延伸但不编造学术引用

核心原则：忠于原文、保留语感、纠正错别字、过滤广告
输出纯 JSON，不要加代码块标记`

async function analyzeContent(transcript, metadata) {
  const apiKey = process.env.DASHSCOPE_API_KEY
  if (!apiKey) throw new Error('DASHSCOPE_API_KEY 环境变量未设置')

  const metaHint = metadata ? `
## 已知元数据
- 播客名称：${metadata.podcast_name || '未知'}
- 本期标题：${metadata.title || '未知'}
- 简介：${(metadata.description || '无').substring(0, 200)}

⚠️ 参与者名字从标题/简介/转录中提取，禁止猜测。

` : ''

  const userMessage = `${metaHint}## 转录文本

${transcript}

请分析以上转录文本，输出符合要求的 JSON 结构。`

  const [mainResult, extResult] = await Promise.all([
    callQwen(apiKey, SYSTEM_PROMPT, userMessage),
    callQwen(apiKey, SYSTEM_PROMPT_EXTENDED, userMessage)
  ])

  const episode = { ...mainResult, ...extResult }

  if (metadata) {
    if (!episode.meta) episode.meta = {}
    if (metadata.cover_url) episode.meta.cover_url = metadata.cover_url
    if (metadata.audio_url) episode.meta.audio_url = metadata.audio_url
    if (metadata.source_url) {
      episode.meta.platform_links = { xiaoyuzhou: metadata.source_url }
    }
  }

  return episode
}

async function callQwen(apiKey, systemPrompt, userMessage) {
  const res = await axios.post(
    `${QWEN_BASE_URL}/chat/completions`,
    {
      model: QWEN_MODEL,
      max_tokens: 16384,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage }
      ]
    },
    {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      timeout: 300000
    }
  )

  const raw = res.data?.choices?.[0]?.message?.content?.trim()
  if (!raw) throw new Error('通义千问返回为空')

  return parseJsonOutput(raw)
}

function parseJsonOutput(raw) {
  let cleaned = raw.replace(/^```(?:json)?\s*\n?/m, '').replace(/\n?```\s*$/m, '').trim()

  try {
    return JSON.parse(cleaned)
  } catch (e) {
    const start = cleaned.indexOf('{')
    const end = cleaned.lastIndexOf('}') + 1
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(cleaned.substring(start, end))
      } catch (e2) {}
    }
    throw new Error(`无法解析 AI 输出为 JSON: ${e.message}\n前200字: ${raw.substring(0, 200)}`)
  }
}
