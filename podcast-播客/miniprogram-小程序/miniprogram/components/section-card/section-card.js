const { formatTime, getDiagramType } = require('../../utils/format')

Component({
  properties: {
    section: { type: Object, value: null },
    sectionIndex: { type: Number, value: 0 },
    participants: { type: Array, value: [] },
    favorites: { type: Object, value: {} }
  },

  data: {
    timeLabel: '',
    diagramType: null,
    expanded: true
  },

  observers: {
    'section': function(section) {
      if (section) {
        this.setData({
          timeLabel: formatTime(section.start_sec),
          diagramType: getDiagramType(section.diagram)
        })
      }
    }
  },

  methods: {
    toggleExpand() {
      this.setData({ expanded: !this.data.expanded })
    },

    onTapQuote(e) {
      const index = e.currentTarget.dataset.index
      const quote = e.currentTarget.dataset.quote
      this.triggerEvent('toggleFavorite', { index, quote })
    },

    getParticipantName(id) {
      const p = this.data.participants.find(p => p.id === id)
      return p ? p.name : ''
    }
  }
})
