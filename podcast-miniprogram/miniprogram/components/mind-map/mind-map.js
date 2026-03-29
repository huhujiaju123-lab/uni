/**
 * 思维导图组件
 * 用缩进列表方式渲染树状结构（非 canvas）
 * 数据结构: { center: string, children: [{ label, children: [...] }] }
 */
Component({
  properties: {
    data: { type: Object, value: null }
  },

  data: {
    flatNodes: []  // 展平后的节点列表 [{ label, depth, hasChildren }]
  },

  observers: {
    'data': function(data) {
      if (data) {
        this.setData({ flatNodes: this.flattenTree(data) })
      }
    }
  },

  methods: {
    flattenTree(node, depth = 0) {
      const result = []
      if (!node) return result

      const label = node.center || node.label || node.text || ''
      if (label) {
        result.push({
          label,
          depth,
          hasChildren: !!(node.children && node.children.length > 0)
        })
      }

      if (node.children) {
        node.children.forEach(child => {
          result.push(...this.flattenTree(child, depth + 1))
        })
      }
      return result
    }
  }
})
