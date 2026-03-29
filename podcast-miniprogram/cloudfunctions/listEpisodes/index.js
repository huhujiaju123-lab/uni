/**
 * listEpisodes 云函数
 * 获取集列表（全部 / 搜索 / 用户历史）
 */
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

exports.main = async (event, context) => {
  const { type, page = 1, pageSize = 20, keyword } = event
  const openid = cloud.getWXContext().OPENID
  const skip = (page - 1) * pageSize

  if (type === 'history') {
    return getHistory(openid, skip, pageSize)
  }

  // 默认：获取全部集（按创建时间倒序）
  let query = db.collection('episodes')

  if (keyword) {
    // 简单关键词搜索（匹配标题）
    query = query.where({
      'meta.title': db.RegExp({ regexp: keyword, options: 'i' })
    })
  }

  const res = await query
    .orderBy('created_at', 'desc')
    .skip(skip)
    .limit(pageSize)
    .field({
      _id: true,
      episode_id: true,
      meta: true,
      created_at: true
    })
    .get()

  return { list: res.data, page, pageSize }
}

async function getHistory(openid, skip, pageSize) {
  const res = await db.collection('user_history').where({
    _openid: openid
  })
    .orderBy('last_read_at', 'desc')
    .skip(skip)
    .limit(pageSize)
    .get()

  return { list: res.data }
}
