// pages/shop/index.js
// 小店商品页面 - 使用微信原生组件展示小店商品和优惠券

// 小店配置
const SHOP_CONFIG = {
  appid: 'wxe06dd093e031f8d9',      // 小店appid
  couponId: '150055794',            // 8折优惠券ID
  productIds: ['10000379885174']    // 要展示的商品ID列表
};

Page({
  data: {
    shopAppid: SHOP_CONFIG.appid,
    couponId: SHOP_CONFIG.couponId,
    productIds: SHOP_CONFIG.productIds,
    isPremium: false,
    isLoggedIn: false,
    // 商品卡片自定义样式
    productStyle: {
      card: {
        'background-color': '#FFFFFF',
        'border-radius': '16rpx'
      },
      title: {
        color: '#000000'
      },
      price: {
        color: '#FA5400'
      },
      'buy-button': {
        'background-color': '#FA5400',
        color: '#FFFFFF'
      }
    },
    // 优惠券自定义样式
    couponStyle: {
      card: {
        'background-color': '#FFF8F5'
      },
      'discount-fee': {
        color: '#FA5400'
      },
      'coupon-button': {
        'background-color': '#FA5400'
      }
    }
  },

  onLoad() {
    this.checkUserStatus();
  },

  onShow() {
    this.checkUserStatus();
  },

  // 检查用户状态
  checkUserStatus() {
    const app = getApp();
    const userInfo = app.globalData.userInfo;
    const isLoggedIn = app.globalData.isLoggedIn;
    const isPremium = userInfo?.role === 'premium';

    this.setData({
      isLoggedIn,
      isPremium
    });
  },

  // 商品跳转成功
  onProductEnterSuccess() {},

  // 商品跳转失败
  onProductEnterError() {
    wx.showToast({
      title: '打开商品失败',
      icon: 'none'
    });
  },

  // 优惠券跳转成功
  onCouponEnterSuccess() {},

  // 优惠券跳转失败
  onCouponEnterError(e) {
    wx.showToast({
      title: e.detail?.message || '领取失败',
      icon: 'none'
    });
  },

  // 跳转升级页面
  goToUpgrade() {
    wx.navigateTo({
      url: '/pages/benefits/benefits'
    });
  },

  // 分享
  onShareAppMessage() {
    return {
      title: '精选好物，会员专享8折',
      path: '/pages/shop/index'
    };
  }
});
