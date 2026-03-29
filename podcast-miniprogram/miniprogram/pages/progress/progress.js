const cloud = require('../../utils/cloud')

Page({
  data: {
    steps: [
      { name: '获取播客信息', icon: '📡', status: 'pending', detail: '' },
      { name: '音频转录', icon: '🎙️', status: 'pending', detail: '' },
      { name: 'AI 内容分析', icon: '🧠', status: 'pending', detail: '' },
      { name: '生成可视化', icon: '🎨', status: 'pending', detail: '' }
    ],
    metadata: null,
    error: null,
    done: false
  },

  taskId: '',
  timer: null,

  onLoad(options) {
    this.taskId = options.task_id
    this.pollProgress()
  },

  onShow() {
    if (this.taskId && !this.data.done) {
      this.pollProgress()
    }
  },

  onHide() {
    this.stopPolling()
  },

  onUnload() {
    this.stopPolling()
  },

  stopPolling() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  },

  async pollProgress() {
    this.stopPolling()
    try {
      const res = await cloud.getTaskProgress(this.taskId)
      const icons = ['📡', '🎙️', '🧠', '🎨']
      const steps = (res.steps || this.data.steps).map((s, i) => ({
        ...s,
        icon: icons[i] || ''
      }))

      this.setData({
        steps,
        metadata: res.metadata || this.data.metadata,
        error: res.error || null,
        done: !!res.done
      })

      if (res.done && !res.error && res.episodeId) {
        setTimeout(() => {
          wx.redirectTo({
            url: '/pages/episode/episode?id=' + res.episodeId
          })
        }, 800)
      } else if (!res.done) {
        this.timer = setTimeout(() => this.pollProgress(), 2000)
      }
    } catch (e) {
      // 网络异常继续重试
      this.timer = setTimeout(() => this.pollProgress(), 3000)
    }
  },

  onBack() {
    wx.navigateBack()
  }
})
