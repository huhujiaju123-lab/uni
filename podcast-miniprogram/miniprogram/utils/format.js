/**
 * 数据格式化工具
 * 将 episode.json 数据转为小程序渲染所需格式
 */

/**
 * 秒数转 mm:ss 格式
 */
function formatTime(seconds) {
  if (!seconds && seconds !== 0) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

/**
 * 秒数转时长描述 "1h23min" / "45min"
 */
function formatDuration(seconds) {
  if (!seconds) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h${m > 0 ? m + 'min' : ''}`
  return `${m}min`
}

/**
 * 日期格式化 "2026-03-01" → "3月1日"
 */
function formatDate(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parseInt(parts[1])}月${parseInt(parts[2])}日`
}

/**
 * 截断文本
 */
function truncate(text, maxLen = 50) {
  if (!text || text.length <= maxLen) return text
  return text.substring(0, maxLen) + '...'
}

/**
 * 从 episode.json 提取预览卡数据
 */
function extractPreview(episode) {
  if (!episode) return null
  const meta = episode.meta || {}
  const participants = episode.participants || []
  const guests = participants.filter(p => p.role === 'guest')
  const hosts = participants.filter(p => p.role === 'host')

  return {
    podcastName: meta.podcast_name || '',
    episodeNumber: meta.episode_number,
    title: meta.title || '',
    subtitle: meta.subtitle || '',
    coverUrl: meta.cover_url || '',
    duration: formatDuration(meta.total_duration_sec),
    publishDate: formatDate(meta.published_date),
    tags: (episode.preview && episode.preview.tags) || [],
    guests: guests.map(g => ({ name: g.name, bio: g.bio || '' })),
    hosts: hosts.map(h => h.name),
    oneSentence: episode.one_sentence_summary || meta.subtitle || '',
    targetAudience: (episode.preview && episode.preview.target_audience) || []
  }
}

/**
 * 从 sections 提取章节导航数据
 */
function extractNavigation(sections) {
  if (!sections) return []
  return sections
    .filter(s => !s.is_ad)
    .map((s, i) => ({
      id: s.id,
      index: i,
      title: s.title,
      subtitle: s.subtitle || '',
      timeLabel: formatTime(s.start_sec),
      startSec: s.start_sec
    }))
}

/**
 * 将 diagram 类型映射为组件渲染模式
 */
function getDiagramType(diagram) {
  if (!diagram) return null
  // Web 版支持 9 种: flow, comparison, icon-list, icon-grid, slope,
  // layers, timeline, quadrant, spectrum
  const type = diagram.type || diagram.visual_type || 'list'
  return type
}

module.exports = {
  formatTime,
  formatDuration,
  formatDate,
  truncate,
  extractPreview,
  extractNavigation,
  getDiagramType
}
