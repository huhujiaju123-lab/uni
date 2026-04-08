/**
 * getEpisode 云函数
 * 多用途函数：获取单集 / 查任务进度 / 收藏管理 / 记录历史
 */
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async (event, context) => {
  const { type } = event
  const openid = cloud.getWXContext().OPENID

  switch (type) {
    case 'task':
      return getTaskProgress(event.taskId)
    case 'toggleFavorite':
      return toggleFavorite(openid, event.episodeId, event.quoteIndex, event.quote)
    case 'favorites':
      return getFavorites(openid)
    case 'recordHistory':
      return recordHistory(openid, event.episodeId)
    default:
      return getEpisodeById(event.episodeId)
  }
}

async function getEpisodeById(episodeId) {
  if (!episodeId) return { error: '缺少 episodeId' }
  const res = await db.collection('episodes').doc(episodeId).get()
  return res.data
}

async function getTaskProgress(taskId) {
  if (!taskId) return { error: '缺少 taskId' }
  const res = await db.collection('tasks').doc(taskId).get()
  const task = res.data
  return {
    steps: task.steps,
    metadata: task.metadata,
    error: task.error,
    done: task.done || task.status === 'done' || task.status === 'error',
    episodeId: task.episode_id
  }
}

async function toggleFavorite(openid, episodeId, quoteIndex, quote) {
  const collection = db.collection('user_favorites')
  const existing = await collection.where({
    _openid: openid,
    episode_id: episodeId,
    quote_index: quoteIndex
  }).get()

  if (existing.data.length > 0) {
    await collection.doc(existing.data[0]._id).remove()
    return { action: 'removed' }
  } else {
    await collection.add({
      data: {
        _openid: openid,
        episode_id: episodeId,
        quote_index: quoteIndex,
        quote: quote,
        created_at: db.serverDate()
      }
    })
    return { action: 'added' }
  }
}

async function getFavorites(openid) {
  const res = await db.collection('user_favorites').where({
    _openid: openid
  }).orderBy('created_at', 'desc').limit(100).get()
  return { list: res.data }
}

async function recordHistory(openid, episodeId) {
  if (!episodeId) return
  const collection = db.collection('user_history')

  // Upsert: 更新已有记录或新建
  const existing = await collection.where({
    _openid: openid,
    episode_id: episodeId
  }).get()

  if (existing.data.length > 0) {
    await collection.doc(existing.data[0]._id).update({
      data: { last_read_at: db.serverDate() }
    })
  } else {
    // 获取集信息用于列表展示
    const ep = await db.collection('episodes').doc(episodeId).get()
    const meta = ep.data?.meta || {}
    await collection.add({
      data: {
        _openid: openid,
        episode_id: episodeId,
        title: meta.title || '',
        podcast_name: meta.podcast_name || '',
        cover_url: meta.cover_url || '',
        last_read_at: db.serverDate()
      }
    })
  }
  return { ok: true }
}
