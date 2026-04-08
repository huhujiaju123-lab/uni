const api = require('../../utils/api')

Page({
  data: {
    url: '',
    history: [],
    loading: false,
    error: ''
  },

  onShow() {
    this.loadHistory()
  },

  loadHistory() {
    api.getHistory().then(res => {
      this.setData({ history: res.episodes || [] })
    })
  },

  onInputChange(e) {
    this.setData({ url: e.detail.value })
  },

  onPaste() {
    wx.getClipboardData({
      success: res => {
        if (res.data && res.data.includes('xiaoyuzhoufm.com')) {
          this.setData({ url: res.data.trim() })
        }
      }
    })
  },

  onSubmit() {
    const url = this.data.url.trim()
    if (!url) {
      this.setData({ error: '请输入播客链接' })
      return
    }
    if (!url.startsWith('https://www.xiaoyuzhoufm.com/episode/')) {
      this.setData({ error: '请输入有效的小宇宙单集链接' })
      return
    }

    this.setData({ loading: true, error: '' })
    api.submitUrl(url).then(res => {
      this.setData({ loading: false })
      if (res.cached) {
        // 已有缓存，直接跳转查看
        wx.navigateTo({ url: '/pages/webview/webview?id=' + res.episode_id })
      } else {
        // 新任务，跳转进度页
        wx.navigateTo({ url: '/pages/progress/progress?task_id=' + res.task_id })
      }
    }).catch(err => {
      this.setData({ loading: false, error: err.error || '提交失败' })
    })
  },

  onTapHistory(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/webview/webview?id=' + id })
  }
})
