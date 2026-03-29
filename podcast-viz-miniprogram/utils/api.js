/**
 * API 请求封装
 */
const app = getApp()

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.baseUrl + path,
      method: options.method || 'GET',
      data: options.data,
      header: { 'Content-Type': 'application/json' },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res.data || { error: '请求失败' })
        }
      },
      fail(err) {
        reject({ error: '网络异常，请检查网络连接' })
      }
    })
  })
}

module.exports = {
  getHistory() {
    return request('/api/history')
  },
  submitUrl(url) {
    return request('/api/process', { method: 'POST', data: { url } })
  },
  getProgress(taskId) {
    return request('/api/status/' + taskId)
  },
  getEpisode(episodeId) {
    return request('/api/episode/' + episodeId)
  }
}
