// pages/profile/profile.js
const api = require('../../utils/api');

Page({
  data: {
    isLoggedIn: false,
    isPremium: false,
    userInfo: null,
    showInviteModal: false,
    useMock: api.USE_MOCK,
    orderCounts: {
      pending: 0,
      paid: 0,
      shipped: 0
    }
  },

  onLoad() {
    this.checkLoginStatus();
  },

  onShow() {
    this.checkLoginStatus();
    if (this.data.isLoggedIn) {
      this.loadOrderCounts();
    }
  },

  // 检查登录状态
  checkLoginStatus() {
    const app = getApp();
    const userInfo = app.globalData.userInfo;
    const isLoggedIn = app.globalData.isLoggedIn;

    this.setData({
      isLoggedIn,
      userInfo,
      isPremium: userInfo?.role === 'premium'
    });
  },

  // 加载订单数量
  async loadOrderCounts() {
    const res = await api.getOrders('', 1, 1);
    if (res.success) {
      this.setData({
        orderCounts: {
          pending: 0,
          paid: 0,
          shipped: 0
        }
      });
    }
  },

  // 登录
  async onLogin() {
    const app = getApp();

    // Mock 模式：直接使用模拟用户信息
    if (api.USE_MOCK) {
      const mockUserInfo = {
        nickName: '测试用户',
        avatarUrl: ''
      };

      const result = await app.login(mockUserInfo);

      if (result.success) {
        this.setData({
          isLoggedIn: true,
          userInfo: result.data.user,
          isPremium: result.data.user.role === 'premium'
        });

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        });

        // 提示测试邀请码
        setTimeout(() => {
          wx.showModal({
            title: '测试模式',
            content: '有效邀请码：TEST88、VIP666、DEMO01\n\n输入邀请码可升级为高级会员',
            showCancel: false,
            confirmText: '知道了'
          });
        }, 1500);
      }
      return;
    }

    // 正式模式：使用 getUserProfile
    try {
      const { userInfo } = await wx.getUserProfile({
        desc: '用于完善会员资料'
      });

      const result = await app.login(userInfo);

      if (result.success) {
        this.setData({
          isLoggedIn: true,
          userInfo: result.data.user,
          isPremium: result.data.user.role === 'premium'
        });

        wx.showToast({
          title: result.data.isNewUser ? '注册成功' : '登录成功',
          icon: 'success'
        });
      } else {
        wx.showToast({
          title: result.message || '登录失败',
          icon: 'none'
        });
      }
    } catch (e) {
      console.log('用户取消登录', e);
    }
  },

  // 升级会员
  onUpgrade() {
    if (!this.data.isLoggedIn) {
      this.onLogin();
      return;
    }
    this.setData({ showInviteModal: true });
  },

  // 邀请好友
  onInvite() {
    wx.navigateTo({
      url: '/pages/invite/invite'
    });
  },

  // 关闭弹窗
  onModalClose() {
    this.setData({ showInviteModal: false });
  },

  // 升级成功
  async onUpgradeSuccess() {
    this.setData({ showInviteModal: false });

    // 刷新用户信息
    const app = getApp();
    const userInfo = await app.refreshUserInfo();

    if (userInfo) {
      this.setData({
        userInfo,
        isPremium: userInfo.role === 'premium'
      });
    }

    wx.showToast({
      title: '升级成功！',
      icon: 'success'
    });
  },

  // 跳转订单列表
  goToOrders(e) {
    if (!this.data.isLoggedIn) {
      this.onLogin();
      return;
    }

    const status = e.currentTarget.dataset.status || '';
    wx.navigateTo({
      url: `/pages/order/list?status=${status}`
    });
  },

  // 跳转地址管理
  goToAddress() {
    if (!this.data.isLoggedIn) {
      this.onLogin();
      return;
    }

    wx.showToast({
      title: '测试模式暂不支持',
      icon: 'none'
    });
  },

  // 联系客服
  onContactService() {
    wx.showModal({
      title: '联系客服',
      content: '客服微信: service_wechat\n工作时间: 9:00-18:00',
      showCancel: false,
      confirmText: '知道了'
    });
  },

  // 关于我们
  goToAbout() {
    const modeText = api.USE_MOCK ? '\n\n【当前为测试模式】' : '';
    wx.showModal({
      title: '关于我们',
      content: '会员商城 v1.0.0\n\n专注为会员提供优质商品和专属服务' + modeText,
      showCancel: false,
      confirmText: '知道了'
    });
  },

  // 退出登录
  onLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      confirmColor: '#FA5400',
      success: (res) => {
        if (res.confirm) {
          const app = getApp();
          app.logout();

          this.setData({
            isLoggedIn: false,
            userInfo: null,
            isPremium: false
          });

          wx.showToast({
            title: '已退出登录',
            icon: 'success'
          });
        }
      }
    });
  },

  // 分享
  onShareAppMessage() {
    if (this.data.isPremium && this.data.userInfo?.invite_code) {
      return {
        title: '邀请你成为高级会员，享专属折扣！',
        path: `/pages/index/index?invite_code=${this.data.userInfo.invite_code}`
      };
    }
    return {
      title: '会员商城 - 精选好物',
      path: '/pages/index/index'
    };
  }
});
