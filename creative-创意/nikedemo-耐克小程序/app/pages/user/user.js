const app = getApp()

Page({
  data: {
    userInfo: {},
    userLevel: 'normal',
    inputCode: ''
  },

  onShow() {
    this.setData({
      userInfo: app.globalData.userInfo,
      userLevel: app.globalData.userInfo.level
    })
  },

  // 监听输入框
  onInputCode(e) {
    this.setData({ inputCode: e.detail.value })
  },

  // 点击升级按钮
  handleUpgrade() {
    if (this.data.inputCode === '888888') {
      // 1. 修改全局数据
      app.globalData.userInfo.level = 'premium';
      
      // 2. 提示成功
      wx.showToast({ title: '升级成功！', icon: 'success' });
      
      // 3. 刷新当前页面显示
      this.onShow();
    } else {
      wx.showToast({ title: '邀请码错误', icon: 'error' });
    }
  },

  // 点击邀请按钮
  handleInvite() {
    wx.showModal({
      title: '邀请好友',
      content: '您的专属邀请码是：A1B2C3\n（模拟生成海报）',
      showCancel: false
    })
  }
})
