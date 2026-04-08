Component({
  properties: {
    episodes: { type: Array, value: [] }
  },

  methods: {
    onTap(e) {
      const id = e.currentTarget.dataset.id
      this.triggerEvent('tap', { id })
    }
  }
})
