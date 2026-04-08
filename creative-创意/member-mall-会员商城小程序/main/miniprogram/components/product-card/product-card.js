// components/product-card/product-card.js
Component({
  properties: {
    product: {
      type: Object,
      value: {}
    },
    userRole: {
      type: String,
      value: 'normal'
    }
  },

  data: {
    originalPrice: '0.00',
    memberPrice: '0.00'
  },

  observers: {
    'product': function(product) {
      if (product && product.price_original) {
        this.setData({
          originalPrice: (product.price_original / 100).toFixed(2),
          memberPrice: (product.price_member / 100).toFixed(2)
        });
      }
    }
  },

  methods: {
    onTap() {
      this.triggerEvent('tap', { product: this.properties.product });
    }
  }
});
