const app = getApp()

Page({
  data: {
    url: '',
    loading: true
  },

  onLoad(options) {
    const episodeId = options.id
    const url = app.globalData.baseUrl + '/view/' + episodeId
    this.setData({ url })
  },

  onWebviewLoad() {
    this.setData({ loading: false })
  },

  onWebviewError(e) {
    console.error('webview error', e)
    this.setData({ loading: false })
    wx.showToast({ title: '页面加载失败', icon: 'none' })
  },

  onShareAppMessage() {
    return {
      title: '播客可视化笔记',
      path: '/pages/webview/webview?id=' + this.episodeId
    }
  }
})
