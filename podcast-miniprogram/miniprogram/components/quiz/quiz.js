/**
 * 互动自测组件
 * 支持 choice 和 slider 两种题型
 */
Component({
  properties: {
    data: { type: Object, value: null }
  },

  data: {
    answers: {},      // { questionId: selectedIndex }
    submitted: false,
    totalScore: 0,
    avgScore: 0,
    resultLevel: null
  },

  methods: {
    onSelectOption(e) {
      if (this.data.submitted) return
      const { qid, optIdx, score } = e.currentTarget.dataset
      const key = `answers.${qid}`
      this.setData({ [key]: { optIdx, score } })
    },

    onSliderChange(e) {
      if (this.data.submitted) return
      const qid = e.currentTarget.dataset.qid
      const value = e.detail.value
      const key = `answers.${qid}`
      this.setData({ [key]: { optIdx: -1, score: value } })
    },

    onSubmit() {
      const questions = this.data.data.questions || []
      const answers = this.data.answers

      // 检查是否全部作答
      if (Object.keys(answers).length < questions.length) {
        wx.showToast({ title: '请完成所有题目', icon: 'none' })
        return
      }

      let total = 0
      questions.forEach(q => {
        const a = answers[q.id]
        if (a) total += (a.score || 0)
      })

      const avg = questions.length > 0 ? total / questions.length : 0

      // 查找结果等级
      const levels = this.data.data.result_levels || []
      let result = levels[levels.length - 1]
      for (const level of levels) {
        if (avg <= level.max_avg_score) {
          result = level
          break
        }
      }

      this.setData({
        submitted: true,
        totalScore: total,
        avgScore: avg.toFixed(1),
        resultLevel: result
      })

      wx.vibrateShort({ type: 'medium' })
    },

    onReset() {
      this.setData({
        answers: {},
        submitted: false,
        totalScore: 0,
        avgScore: 0,
        resultLevel: null
      })
    }
  }
})
