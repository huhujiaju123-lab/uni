/**
 * 内联图表组件
 * 对应 Web 版 9 种图表类型
 * 数据预处理在 JS 层完成，WXML 只做简单渲染
 */
Component({
  properties: {
    data: { type: Object, value: null }
  },

  data: {
    type: 'list',
    items: [],
    // comparison 专用
    compLeft: '',
    compRight: '',
    compEntries: []
  },

  observers: {
    'data': function(data) {
      if (!data) return
      const type = data.type || data.visual_type || 'list'
      const items = data.items || data.steps || data.layers || data.events || data.entries || []

      const updates = { type, items }

      if (type === 'comparison') {
        updates.compLeft = (data.left && data.left.label) || '左'
        updates.compRight = (data.right && data.right.label) || '右'
        updates.compEntries = data.entries || data.items || data.rows || []
      }

      this.setData(updates)
    }
  }
})
