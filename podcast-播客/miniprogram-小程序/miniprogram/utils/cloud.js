/**
 * 云函数调用封装
 * 统一错误处理、重试、超时
 */

/**
 * 调用云函数
 * @param {string} name - 云函数名
 * @param {object} data - 参数
 * @param {object} opts - 选项 { timeout, retry }
 */
function callFunction(name, data = {}, opts = {}) {
  const timeout = opts.timeout || 10000
  const retry = opts.retry || 0

  return new Promise((resolve, reject) => {
    wx.cloud.callFunction({
      name,
      data,
      timeout,
      success: res => {
        if (res.result && res.result.error) {
          reject(res.result)
        } else {
          resolve(res.result)
        }
      },
      fail: err => {
        if (retry > 0) {
          callFunction(name, data, { ...opts, retry: retry - 1 })
            .then(resolve)
            .catch(reject)
        } else {
          reject({ error: '网络异常，请重试', detail: err })
        }
      }
    })
  })
}

/**
 * 提交播客处理任务（异步云函数）
 */
function submitEpisode(url) {
  return callFunction('processEpisode', { url }, { timeout: 15000 })
}

/**
 * 获取单集数据
 */
function getEpisode(episodeId) {
  return callFunction('getEpisode', { episodeId })
}

/**
 * 获取集列表
 * @param {object} opts - { page, pageSize, keyword }
 */
function listEpisodes(opts = {}) {
  return callFunction('listEpisodes', opts)
}

/**
 * 获取任务进度
 */
function getTaskProgress(taskId) {
  return callFunction('getEpisode', { taskId, type: 'task' })
}

/**
 * 收藏/取消收藏金句
 */
function toggleFavorite(episodeId, quoteIndex, quote) {
  return callFunction('getEpisode', {
    type: 'toggleFavorite',
    episodeId,
    quoteIndex,
    quote
  })
}

/**
 * 获取用户收藏列表
 */
function getFavorites() {
  return callFunction('getEpisode', { type: 'favorites' })
}

/**
 * 记录浏览历史
 */
function recordHistory(episodeId) {
  return callFunction('getEpisode', { type: 'recordHistory', episodeId })
}

module.exports = {
  callFunction,
  submitEpisode,
  getEpisode,
  listEpisodes,
  getTaskProgress,
  toggleFavorite,
  getFavorites,
  recordHistory
}
