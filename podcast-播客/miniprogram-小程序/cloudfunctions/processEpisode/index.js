/**
 * processEpisode 云函数（快速入口）
 * 检查缓存 → 创建任务 → 异步触发 runPipeline → 立即返回 taskId
 *
 * 输入: { url: "https://www.xiaoyuzhoufm.com/episode/xxx" }
 * 输出: { taskId, cached?, episodeId? }
 */
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async (event, context) => {
  const { url } = event
  if (!url || !url.includes('xiaoyuzhoufm.com/episode/')) {
    return { error: '请提供有效的小宇宙单集链接' }
  }

  const match = url.match(/episode\/([a-f0-9]+)/)
  if (!match) return { error: '无法解析链接' }
  const episodeId = match[1]

  // 检查缓存
  const cached = await db.collection('episodes').where({ episode_id: episodeId }).get()
  if (cached.data && cached.data.length > 0) {
    return { cached: true, episodeId: cached.data[0]._id }
  }

  // 检查是否已有进行中的任务
  const existing = await db.collection('tasks').where({
    episode_id: episodeId,
    status: 'processing'
  }).get()
  if (existing.data && existing.data.length > 0) {
    return { taskId: existing.data[0]._id }
  }

  // 创建任务记录
  const task = await db.collection('tasks').add({
    data: {
      episode_id: episodeId,
      url,
      status: 'processing',
      steps: [
        { name: '获取播客信息', status: 'pending', detail: '' },
        { name: '音频转录', status: 'pending', detail: '' },
        { name: 'AI 内容分析', status: 'pending', detail: '' },
        { name: '存入数据库', status: 'pending', detail: '' }
      ],
      created_at: db.serverDate(),
      _openid: cloud.getWXContext().OPENID || ''
    }
  })
  const taskId = task._id

  // 异步触发 runPipeline（不等待完成）
  cloud.callFunction({
    name: 'runPipeline',
    data: { taskId, url, episodeId }
  }).catch(err => {
    console.error('触发 runPipeline 失败:', err)
    // 更新任务状态为失败
    db.collection('tasks').doc(taskId).update({
      data: { status: 'error', error: '启动处理流程失败', done: true }
    })
  })

  // 立即返回 taskId
  return { taskId }
}
