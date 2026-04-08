const api = require('../../utils/api')

Page({
  data: {
    steps: [
      { name: '获取元数据', status: 'pending', detail: '', icon: '📡' },
      { name: '音频转录', status: 'pending', detail: '', icon: '🎙️' },
      { name: 'AI 内容分析', status: 'pending', detail: '', icon: '🧠' },
      { name: '生成可视化', status: 'pending', detail: '', icon: '🎨' }
    ],
    metadata: null,
    error: null,
    done: false
  },

  timer: null,
  taskId: '',

  onLoad(options) {
    this.taskId = options.task_id
    this.pollProgress()
  },

  onShow() {
    // 从后台恢复时重新轮询
    if (this.taskId && !this.data.done) {
      this.pollProgress()
    }
  },

  onHide() {
    clearTimeout(this.timer)
  },

  onUnload() {
    clearTimeout(this.timer)
  },

  pollProgress() {
    clearTimeout(this.timer)
    api.getProgress(this.taskId).then(res => {
      const icons = ['📡', '🎙️', '🧠', '🎨']
      const steps = (res.steps || []).map((s, i) => ({
        ...s,
        icon: icons[i] || ''
      }))

      this.setData({
        steps,
        metadata: res.metadata,
        error: res.error,
        done: res.done
      })

      if (res.done && !res.error && res.episode_id) {
        // 完成，延迟跳转
        setTimeout(() => {
          wx.redirectTo({
            url: '/pages/webview/webview?id=' + res.episode_id
          })
        }, 1000)
      } else if (!res.done) {
        this.timer = setTimeout(() => this.pollProgress(), 2000)
      }
    }).catch(() => {
      // 网络异常，继续重试
      this.timer = setTimeout(() => this.pollProgress(), 3000)
    })
  },

  onBack() {
    wx.navigateBack()
  }
})
