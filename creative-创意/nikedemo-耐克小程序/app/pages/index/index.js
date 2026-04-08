const app = getApp()

Page({
  data: {
    userLevel: 'normal', // 默认普通
    products: [
      { id: 1, name: 'Nike Air Force 1', price_origin: 899, price_vip: 699 },
      { id: 2, name: 'Jordan 复古卫衣', price_origin: 499, price_vip: 359 },
      { id: 3, name: 'Dunk Low 熊猫', price_origin: 799, price_vip: 599 }
    ]
  },

  onShow() {
    // 每次显示页面时，都去读取最新的全局等级
    this.setData({
      userLevel: app.globalData.userInfo.level
    })
  }
})
