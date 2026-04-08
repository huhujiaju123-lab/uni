// components/member-badge/member-badge.js
Component({
  properties: {
    role: {
      type: String,
      value: 'normal'
    }
  },

  data: {
    isPremium: false
  },

  observers: {
    'role': function(role) {
      this.setData({
        isPremium: role === 'premium'
      });
    }
  }
});
