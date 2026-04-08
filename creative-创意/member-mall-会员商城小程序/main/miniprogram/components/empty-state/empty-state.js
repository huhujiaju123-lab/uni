// components/empty-state/empty-state.js
Component({
  properties: {
    image: {
      type: String,
      value: ''
    },
    text: {
      type: String,
      value: '暂无数据'
    },
    buttonText: {
      type: String,
      value: ''
    }
  },

  methods: {
    onButtonTap() {
      this.triggerEvent('buttonTap');
    }
  }
});
