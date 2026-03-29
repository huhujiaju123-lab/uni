const cloud = require('../../utils/cloud')

Page({
  data: {
    activeTab: 'history',  // history | favorites
    history: [],
    favorites: [],
    loading: true
  },

  onShow() {
    this.loadData()
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const [historyRes, favRes] = await Promise.all([
        cloud.callFunction('listEpisodes', { type: 'history' }),
        cloud.getFavorites()
      ])
      this.setData({
        history: historyRes.list || [],
        favorites: favRes.list || [],
        loading: false
      })
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  onTapEpisode(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/episode/episode?id=' + id })
  },

  // 导出收藏金句为文本
  exportFavorites() {
    const quotes = this.data.favorites
    if (quotes.length === 0) {
      wx.showToast({ title: '暂无收藏', icon: 'none' })
      return
    }

    let text = '## 收藏的金句\n\n'
    quotes.forEach(q => {
      text += `> ${q.quote}\n`
      if (q.episodeTitle) text += `> — ${q.episodeTitle}\n`
      text += '\n'
    })
    text += `\n_来源：播客可视化_`

    wx.setClipboardData({
      data: text,
      success: () => {
        wx.showToast({ title: '已复制到剪贴板', icon: 'success' })
      }
    })
  }
})
