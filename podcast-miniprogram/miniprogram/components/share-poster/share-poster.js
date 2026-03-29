/**
 * 分享海报组件
 * 用 canvas 绘制海报 → 保存到相册
 * 对应 Web 版 Phase 1 的社交分享功能（蓝海机会）
 */
Component({
  properties: {
    episode: { type: Object, value: null },
    visible: { type: Boolean, value: false }
  },

  data: {
    generating: false,
    posterPath: ''
  },

  methods: {
    onClose() {
      this.triggerEvent('close')
    },

    async generatePoster() {
      if (this.data.generating) return
      this.setData({ generating: true })

      try {
        const query = this.createSelectorQuery()
        query.select('#poster-canvas')
          .fields({ node: true, size: true })
          .exec(async (res) => {
            const canvas = res[0].node
            const ctx = canvas.getContext('2d')
            const dpr = wx.getWindowInfo().pixelRatio
            const width = 750
            const height = 1000

            canvas.width = width * dpr
            canvas.height = height * dpr
            ctx.scale(dpr, dpr)

            // 绘制背景
            ctx.fillStyle = '#0a0a0f'
            ctx.fillRect(0, 0, width, height)

            // 绘制金色装饰线
            ctx.strokeStyle = '#d4a017'
            ctx.lineWidth = 2
            ctx.strokeRect(30, 30, width - 60, height - 60)

            // 播客名
            const meta = this.data.episode?.meta || {}
            ctx.fillStyle = '#d4a017'
            ctx.font = '24px sans-serif'
            ctx.textAlign = 'center'
            ctx.fillText(meta.podcast_name || '', width / 2, 100)

            // 标题
            ctx.fillStyle = '#e8e0d0'
            ctx.font = 'bold 36px serif'
            this.wrapText(ctx, meta.title || '', width / 2, 180, width - 120, 48)

            // 金句
            const quote = (this.data.episode?.core_quotes || [])[0]
            if (quote) {
              ctx.fillStyle = '#d4a017'
              ctx.font = '28px serif'
              const quoteText = `「${quote}」`
              this.wrapText(ctx, quoteText, width / 2, 400, width - 120, 40)
            }

            // 底部信息
            ctx.fillStyle = '#8a8275'
            ctx.font = '20px sans-serif'
            ctx.fillText('播客可视化 · podcast-viz', width / 2, height - 80)

            // 导出图片
            const tempPath = await new Promise((resolve) => {
              wx.canvasToTempFilePath({
                canvas,
                success: (res) => resolve(res.tempFilePath),
                fail: () => resolve('')
              })
            })

            this.setData({ generating: false, posterPath: tempPath })
          })
      } catch (e) {
        this.setData({ generating: false })
        wx.showToast({ title: '生成失败', icon: 'none' })
      }
    },

    // 文本自动换行
    wrapText(ctx, text, x, y, maxWidth, lineHeight) {
      const chars = text.split('')
      let line = ''
      let currentY = y

      for (const char of chars) {
        const testLine = line + char
        const metrics = ctx.measureText(testLine)
        if (metrics.width > maxWidth && line) {
          ctx.fillText(line, x, currentY)
          line = char
          currentY += lineHeight
        } else {
          line = testLine
        }
      }
      ctx.fillText(line, x, currentY)
    },

    async savePoster() {
      if (!this.data.posterPath) {
        await this.generatePoster()
      }
      if (!this.data.posterPath) return

      wx.saveImageToPhotosAlbum({
        filePath: this.data.posterPath,
        success: () => {
          wx.showToast({ title: '已保存到相册', icon: 'success' })
        },
        fail: (err) => {
          if (err.errMsg.includes('auth deny')) {
            wx.showToast({ title: '请允许保存到相册', icon: 'none' })
          }
        }
      })
    }
  }
})
