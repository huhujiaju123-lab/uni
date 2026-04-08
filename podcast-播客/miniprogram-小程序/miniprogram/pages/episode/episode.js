const cloud = require('../../utils/cloud')
const { extractPreview, extractNavigation, formatTime } = require('../../utils/format')

Page({
  data: {
    episode: null,
    preview: null,
    navigation: [],
    activeSection: 0,
    loading: true,
    error: null,
    favorites: {},       // { quoteIndex: true }
    showNavPanel: false,
    scrollToSection: ''
  },

  episodeId: '',

  onLoad(options) {
    this.episodeId = options.id
    this.loadEpisode()
  },

  async loadEpisode() {
    try {
      const episode = await cloud.getEpisode(this.episodeId)
      const preview = extractPreview(episode)
      const navigation = extractNavigation(episode.sections)

      // 过滤广告段
      const sections = (episode.sections || []).filter(s => !s.is_ad)

      this.setData({
        episode: { ...episode, sections },
        preview,
        navigation,
        loading: false
      })

      // 记录浏览历史
      cloud.recordHistory(this.episodeId).catch(() => {})
    } catch (e) {
      this.setData({ loading: false, error: e.error || '加载失败' })
    }
  },

  // 章节导航
  toggleNav() {
    this.setData({ showNavPanel: !this.data.showNavPanel })
  },

  scrollToChapter(e) {
    const id = e.currentTarget.dataset.id
    this.setData({
      scrollToSection: id,
      showNavPanel: false
    })
  },

  // 金句收藏
  onToggleFavorite(e) {
    const { index, quote } = e.detail
    const key = `favorites.${index}`
    const isFav = !this.data.favorites[index]
    this.setData({ [key]: isFav })

    wx.vibrateShort({ type: 'light' })

    cloud.toggleFavorite(this.episodeId, index, quote).catch(() => {
      // 回滚
      this.setData({ [key]: !isFav })
    })
  },

  // 阻止遮罩层滚动穿透
  preventMove() {},

  // 分享
  onShareAppMessage() {
    const meta = this.data.episode?.meta || {}
    return {
      title: meta.title || '播客可视化笔记',
      path: '/pages/episode/episode?id=' + this.episodeId,
      imageUrl: meta.cover_url || ''
    }
  },

  onShareTimeline() {
    const meta = this.data.episode?.meta || {}
    return {
      title: meta.title || '播客可视化笔记',
      imageUrl: meta.cover_url || ''
    }
  }
})
