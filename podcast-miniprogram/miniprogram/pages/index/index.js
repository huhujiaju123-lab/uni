const cloud = require('../../utils/cloud')
const { truncate, formatDuration } = require('../../utils/format')

Page({
  data: {
    episodes: [],
    loading: true,
    inputUrl: '',
    showInput: false,
    submitting: false,
    error: '',
    debugMode: true  // TODO: 上线前改为 false
  },

  onShow() {
    this.loadEpisodes()
  },

  async loadEpisodes() {
    try {
      const res = await cloud.listEpisodes({ page: 1, pageSize: 20 })
      this.setData({
        episodes: (res.list || []).map(ep => ({
          ...ep,
          titleShort: truncate(ep.meta?.title, 30),
          podcastName: ep.meta?.podcast_name || '',
          durationText: formatDuration(ep.meta?.total_duration_sec)
        })),
        loading: false
      })
    } catch (e) {
      this.setData({ loading: false })
      console.error('加载列表失败', e)
    }
  },

  onPullDownRefresh() {
    this.loadEpisodes().then(() => wx.stopPullDownRefresh())
  },

  toggleInput() {
    this.setData({ showInput: !this.data.showInput, error: '' })
  },

  onInputChange(e) {
    this.setData({ inputUrl: e.detail.value })
  },

  onPaste() {
    wx.getClipboardData({
      success: res => {
        if (res.data && res.data.includes('xiaoyuzhoufm.com')) {
          this.setData({ inputUrl: res.data.trim() })
        }
      }
    })
  },

  async onSubmit() {
    const url = this.data.inputUrl.trim()
    if (!url) {
      this.setData({ error: '请输入播客链接' })
      return
    }
    if (!url.includes('xiaoyuzhoufm.com/episode/')) {
      this.setData({ error: '请输入小宇宙单集链接' })
      return
    }

    this.setData({ submitting: true, error: '' })
    try {
      const res = await cloud.submitEpisode(url)
      this.setData({ submitting: false, showInput: false, inputUrl: '' })

      if (res.cached && res.episodeId) {
        wx.navigateTo({ url: '/pages/episode/episode?id=' + res.episodeId })
      } else if (res.taskId) {
        wx.navigateTo({ url: '/pages/progress/progress?task_id=' + res.taskId })
      }
    } catch (e) {
      this.setData({ submitting: false, error: e.error || '提交失败，请重试' })
    }
  },

  onTapEpisode(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/episode/episode?id=' + id })
  },

  // ===== 调试功能 =====

  async onInitDB() {
    wx.showLoading({ title: '初始化中...' })
    try {
      const res = await cloud.callFunction('initDB')
      wx.hideLoading()
      console.log('initDB result:', res)
      wx.showModal({
        title: res.success ? '初始化成功' : '初始化失败',
        content: (res.results || []).join('\n'),
        showCancel: false
      })
      // 刷新列表
      this.loadEpisodes()
    } catch (e) {
      wx.hideLoading()
      console.error('initDB error:', e)
      wx.showModal({ title: '初始化失败', content: JSON.stringify(e), showCancel: false })
    }
  },

  async onTestGetEpisode() {
    wx.showLoading({ title: '测试中...' })
    try {
      // 先获取列表中第一个 episode
      const list = await cloud.listEpisodes({ page: 1, pageSize: 1 })
      if (!list.list || list.list.length === 0) {
        wx.hideLoading()
        wx.showToast({ title: '没有数据，先初始化', icon: 'none' })
        return
      }
      const id = list.list[0]._id
      const episode = await cloud.getEpisode(id)
      wx.hideLoading()
      console.log('getEpisode result:', episode)
      wx.showModal({
        title: '读取成功',
        content: `标题: ${episode.meta?.title}\n章节数: ${(episode.sections || []).length}\n金句数: ${(episode.core_quotes || []).length}`,
        showCancel: false
      })
    } catch (e) {
      wx.hideLoading()
      console.error('getEpisode error:', e)
      wx.showModal({ title: '测试失败', content: JSON.stringify(e), showCancel: false })
    }
  },

  async onTestNavToEpisode() {
    try {
      const list = await cloud.listEpisodes({ page: 1, pageSize: 1 })
      if (!list.list || list.list.length === 0) {
        wx.showToast({ title: '没有数据，先初始化', icon: 'none' })
        return
      }
      const id = list.list[0]._id
      wx.navigateTo({ url: '/pages/episode/episode?id=' + id })
    } catch (e) {
      wx.showToast({ title: '跳转失败', icon: 'none' })
    }
  }
})
