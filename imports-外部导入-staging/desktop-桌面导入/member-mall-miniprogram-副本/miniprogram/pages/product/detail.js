// pages/product/detail.js
const api = require('../../utils/api');

Page({
  data: {
    product: null,
    currentImageIndex: 0,
    isPremium: false
  },

  onLoad(options) {
    if (options.id) {
      this.loadProduct(options.id);
    }
    this.checkUserStatus();
  },

  // 检查用户状态
  checkUserStatus() {
    const app = getApp();
    const userInfo = app.globalData.userInfo;
    this.setData({
      isPremium: userInfo?.role === 'premium'
    });
  },

  // 加载商品详情
  async loadProduct(id) {
    wx.showLoading({ title: '加载中...' });

    const res = await api.getProductDetail(id);

    wx.hideLoading();

    if (res.success) {
      this.setData({
        product: res.data
      });
      // 设置页面标题
      wx.setNavigationBarTitle({
        title: res.data.name || '商品详情'
      });
    } else {
      wx.showToast({
        title: '商品不存在',
        icon: 'none'
      });
    }
  },

  // 切换轮播图
  onSwiperChange(e) {
    this.setData({
      currentImageIndex: e.detail.current
    });
  },

  // 预览图片
  previewImage(e) {
    const { product, currentImageIndex } = this.data;
    if (product && product.images) {
      wx.previewImage({
        current: product.images[currentImageIndex],
        urls: product.images
      });
    }
  },

  // 返回福利页面升级
  goToBenefits() {
    wx.switchTab({
      url: '/pages/benefits/benefits'
    });
  }
});
