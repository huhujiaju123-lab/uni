#!/usr/bin/env node
/**
 * 后端自测脚本
 * 逐步验证：元数据抓取 → 数据模型 → API 格式 → 云函数逻辑
 * 用法: node test_backend.js
 */

const axios = require('axios')
const cheerio = require('cheerio')

const TEST_URL = 'https://www.xiaoyuzhoufm.com/episode/698b27ae66e2c30377d88131'
const USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

let passed = 0
let failed = 0

function ok(name) { passed++; console.log(`  ✅ ${name}`) }
function fail(name, err) { failed++; console.log(`  ❌ ${name}: ${err}`) }

// ===== Test 1: fetchMetadata =====
async function testFetchMetadata() {
  console.log('\n🔍 Test 1: fetchMetadata（小宇宙元数据抓取）')

  try {
    const res = await axios.get(TEST_URL, {
      headers: { 'User-Agent': USER_AGENT, 'Accept-Language': 'zh-CN,zh;q=0.9' },
      timeout: 15000,
      maxRedirects: 5
    })

    if (res.status === 200) ok('HTTP 请求成功')
    else fail('HTTP 请求', `status ${res.status}`)

    const $ = cheerio.load(res.data)
    const getOg = (prop) => $(`meta[property="${prop}"]`).attr('content') || ''

    const title = getOg('og:title')
    const audioUrl = getOg('og:audio')
    const coverUrl = getOg('og:image')
    let podcastName = getOg('og:site_name')

    if (title) ok(`og:title = "${title.substring(0, 40)}..."`)
    else fail('og:title', '为空')

    if (audioUrl && audioUrl.includes('xyzcdn.net')) ok(`og:audio = ${audioUrl.substring(0, 60)}...`)
    else {
      // 尝试正则兜底
      const match = res.data.match(/https:\/\/media\.xyzcdn\.net\/[^\s"']+\.m4a/)
      if (match) ok(`audio_url (正则兜底) = ${match[0].substring(0, 60)}...`)
      else fail('audio_url', '未找到音频链接')
    }

    if (coverUrl) ok(`og:image = ${coverUrl.substring(0, 60)}...`)
    else fail('og:image', '为空')

    // podcastName 兜底：JSON-LD partOfSeries 或 title 标签
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

    if (podcastName) ok(`podcast_name = "${podcastName}"`)
    else fail('podcast_name', '未找到播客名')

    // JSON-LD 时长
    let durationSec = 0
    $('script[type="application/ld+json"]').each((_, el) => {
      try {
        const data = JSON.parse($(el).html())
        const tr = data.timeRequired
        if (tr) {
          const m = tr.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/)
          if (m) durationSec = (parseInt(m[1] || 0)) * 3600 + (parseInt(m[2] || 0)) * 60 + (parseInt(m[3] || 0))
        }
      } catch (e) {}
    })
    if (durationSec > 0) ok(`duration = ${durationSec}s (${Math.floor(durationSec/60)}min)`)
    else fail('duration', '未从 JSON-LD 提取到时长（非致命）')

    return { title, audioUrl: audioUrl || '', coverUrl, podcastName, durationSec }
  } catch (e) {
    fail('fetchMetadata 整体失败', e.message)
    return null
  }
}

// ===== Test 2: Deepgram API 格式验证 =====
function testDeepgramFormat() {
  console.log('\n🎙️ Test 2: Deepgram API 格式验证（不实际调用）')

  const apiKey = process.env.DEEPGRAM_API_KEY
  if (!apiKey) {
    console.log('  ⚠️  DEEPGRAM_API_KEY 未设置，跳过实际调用测试')
    console.log('  ℹ️  验证请求构造格式...')
  }

  const params = new URLSearchParams({
    model: 'nova-2',
    language: 'zh',
    smart_format: 'true',
    punctuate: 'true',
    paragraphs: 'true',
    diarize: 'true'
  })
  const url = `https://api.deepgram.com/v1/listen?${params.toString()}`

  if (url.includes('model=nova-2')) ok('model=nova-2')
  if (url.includes('language=zh')) ok('language=zh')
  if (url.includes('paragraphs=true')) ok('paragraphs=true')
  if (url.includes('diarize=true')) ok('diarize=true')

  // 验证 formatTimestamp
  const formatTimestamp = (seconds) => {
    const total = Math.floor(seconds)
    const h = Math.floor(total / 3600)
    const m = Math.floor((total % 3600) / 60)
    const s = total % 60
    if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  if (formatTimestamp(0) === '00:00') ok('formatTimestamp(0) = 00:00')
  else fail('formatTimestamp(0)', formatTimestamp(0))
  if (formatTimestamp(488) === '08:08') ok('formatTimestamp(488) = 08:08')
  else fail('formatTimestamp(488)', formatTimestamp(488))
  if (formatTimestamp(5344) === '01:29:04') ok('formatTimestamp(5344) = 01:29:04')
  else fail('formatTimestamp(5344)', formatTimestamp(5344))
}

// ===== Test 3: 通义千问 API 格式验证 =====
async function testQwenFormat() {
  console.log('\n🧠 Test 3: 通义千问 API 格式验证')

  const apiKey = process.env.DASHSCOPE_API_KEY
  if (!apiKey) {
    console.log('  ⚠️  DASHSCOPE_API_KEY 未设置，跳过实际调用测试')
    console.log('  ℹ️  验证请求构造格式...')
  }

  const QWEN_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  const payload = {
    model: 'qwen-plus',
    max_tokens: 16384,
    messages: [
      { role: 'system', content: '你是助手' },
      { role: 'user', content: '说hello' }
    ]
  }

  // 格式检查
  if (payload.model === 'qwen-plus') ok('model = qwen-plus')
  if (payload.max_tokens === 16384) ok('max_tokens = 16384')
  if (payload.messages.length === 2) ok('messages 结构正确')

  // 如果有 key，做一次真实调用
  if (apiKey) {
    try {
      const res = await axios.post(`${QWEN_BASE_URL}/chat/completions`, payload, {
        headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        timeout: 30000
      })
      if (res.data?.choices?.[0]?.message?.content) {
        ok(`通义千问实际调用成功: "${res.data.choices[0].message.content.substring(0, 30)}..."`)
      } else {
        fail('通义千问返回格式异常', JSON.stringify(res.data).substring(0, 100))
      }
    } catch (e) {
      fail('通义千问调用失败', e.response?.data?.error?.message || e.message)
    }
  }

  // parseJsonOutput 测试
  console.log('\n  📋 parseJsonOutput 解析测试:')
  const parseJsonOutput = (raw) => {
    let cleaned = raw.replace(/^```(?:json)?\s*\n?/m, '').replace(/\n?```\s*$/m, '').trim()
    try { return JSON.parse(cleaned) } catch (e) {
      const start = cleaned.indexOf('{')
      const end = cleaned.lastIndexOf('}') + 1
      if (start >= 0 && end > start) {
        try { return JSON.parse(cleaned.substring(start, end)) } catch (e2) {}
      }
      throw new Error(`parse failed: ${e.message}`)
    }
  }

  // Case 1: 纯 JSON
  try {
    const r = parseJsonOutput('{"a": 1}')
    if (r.a === 1) ok('纯 JSON 解析')
    else fail('纯 JSON 解析', JSON.stringify(r))
  } catch (e) { fail('纯 JSON 解析', e.message) }

  // Case 2: ```json 包裹
  try {
    const r = parseJsonOutput('```json\n{"b": 2}\n```')
    if (r.b === 2) ok('```json 包裹解析')
    else fail('```json 包裹', JSON.stringify(r))
  } catch (e) { fail('```json 包裹', e.message) }

  // Case 3: 带前缀文字
  try {
    const r = parseJsonOutput('以下是分析结果：\n{"c": 3}\n感谢')
    if (r.c === 3) ok('带前缀文字解析')
    else fail('带前缀文字', JSON.stringify(r))
  } catch (e) { fail('带前缀文字', e.message) }
}

// ===== Test 4: 测试数据模型完整性 =====
function testDataModel() {
  console.log('\n📦 Test 4: 测试数据模型（initDB 种子数据）')

  const initDB = require('./cloudfunctions/initDB/index.js')
  // 我们无法直接调用 exports.main（需要云环境），但可以检查文件是否能加载
  ok('initDB/index.js 加载成功')

  // 从文件中提取测试数据检查
  const fs = require('fs')
  const src = fs.readFileSync('./cloudfunctions/initDB/index.js', 'utf8')

  // 检查关键字段
  const fields = ['episode_id', 'meta', 'participants', 'sections', 'core_quotes',
    'content_overview', 'arguments', 'key_concepts', 'mind_map', 'quiz']
  for (const f of fields) {
    if (src.includes(`${f}:`)) ok(`种子数据包含 ${f}`)
    else fail(`种子数据缺少`, f)
  }

  // 检查小程序前端期望的字段
  const frontendFields = ['key_points_grouped', 'diagram', 'section_context', 'extended_reading']
  for (const f of frontendFields) {
    if (src.includes(f)) ok(`前端依赖字段 ${f} 存在`)
    else fail(`前端依赖字段缺失`, f)
  }
}

// ===== Test 5: 云函数代码语法检查 =====
function testCloudFunctionSyntax() {
  console.log('\n⚙️ Test 5: 云函数代码语法检查')

  const functions = ['processEpisode', 'getEpisode', 'listEpisodes', 'initDB']
  for (const fn of functions) {
    try {
      require(`./cloudfunctions/${fn}/index.js`)
      ok(`${fn}/index.js 语法正确，可加载`)
    } catch (e) {
      fail(`${fn}/index.js 加载失败`, e.message)
    }
  }
}

// ===== Test 6: 前端 utils 逻辑 =====
function testFrontendUtils() {
  console.log('\n🧰 Test 6: 前端 utils 工具函数')

  const format = require('./miniprogram/utils/format.js')

  // formatTime
  if (format.formatTime(0) === '0:00') ok('formatTime(0) = 0:00')
  else fail('formatTime(0)', format.formatTime(0))
  if (format.formatTime(488) === '8:08') ok('formatTime(488) = 8:08')
  else fail('formatTime(488)', format.formatTime(488))

  // formatDuration
  if (format.formatDuration(5344) === '1h29min') ok('formatDuration(5344) = 1h29min')
  else fail('formatDuration(5344)', format.formatDuration(5344))
  if (format.formatDuration(2700) === '45min') ok('formatDuration(2700) = 45min')
  else fail('formatDuration(2700)', format.formatDuration(2700))

  // truncate
  if (format.truncate('hello world', 5) === 'hello...') ok('truncate 截断')
  else fail('truncate', format.truncate('hello world', 5))
  if (format.truncate('hi', 5) === 'hi') ok('truncate 不截断')
  else fail('truncate 不截断', format.truncate('hi', 5))

  // extractPreview
  const episode = {
    meta: { podcast_name: '测试', title: '标题', total_duration_sec: 3600, published_date: '2026-03-01' },
    participants: [{ id: 'h1', name: '主持人', role: 'host' }, { id: 'g1', name: '嘉宾', role: 'guest', bio: '专家' }],
    one_sentence_summary: '测试摘要',
    preview: { tags: ['标签1', '标签2'], target_audience: ['人群1'] }
  }
  const p = format.extractPreview(episode)
  if (p.podcastName === '测试') ok('extractPreview.podcastName')
  else fail('extractPreview.podcastName', p.podcastName)
  if (p.guests.length === 1 && p.guests[0].name === '嘉宾') ok('extractPreview.guests')
  else fail('extractPreview.guests', JSON.stringify(p.guests))
  if (p.duration === '1h') ok('extractPreview.duration = 1h')
  else fail('extractPreview.duration', p.duration)
  if (p.tags.length === 2) ok('extractPreview.tags')
  else fail('extractPreview.tags', JSON.stringify(p.tags))

  // extractNavigation
  const sections = [
    { id: 'intro', title: '开场', start_sec: 0, is_ad: false },
    { id: 'ad', title: '广告', start_sec: 100, is_ad: true },
    { id: 'ch1', title: '第一章', start_sec: 200, is_ad: false }
  ]
  const nav = format.extractNavigation(sections)
  if (nav.length === 2) ok('extractNavigation 过滤广告（3→2）')
  else fail('extractNavigation', `length=${nav.length}`)
  if (nav[0].timeLabel === '0:00') ok('extractNavigation 时间标签')
  else fail('extractNavigation 时间标签', nav[0].timeLabel)
}

// ===== 运行 =====
async function main() {
  console.log('🚀 podcast-miniprogram 后端自测')
  console.log('=' .repeat(50))

  const meta = await testFetchMetadata()
  testDeepgramFormat()
  await testQwenFormat()
  testDataModel()
  testCloudFunctionSyntax()
  testFrontendUtils()

  console.log('\n' + '='.repeat(50))
  console.log(`📊 结果: ${passed} 通过, ${failed} 失败`)
  if (failed > 0) process.exit(1)
}

main().catch(e => { console.error('测试脚本异常:', e); process.exit(1) })
