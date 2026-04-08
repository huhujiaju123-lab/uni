Component({
  properties: {
    quote: { type: String, value: '' },
    index: { type: Number, value: 0 },
    isFavorite: { type: Boolean, value: false }
  },

  methods: {
    onTap() {
      this.triggerEvent('toggleFavorite', {
        index: this.data.index,
        quote: this.data.quote
      })
    }
  }
})
