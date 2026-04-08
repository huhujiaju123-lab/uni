// pages/benefits/benefits.js
const api = require('../../utils/api');

Page({
  data: {
    isPremium: false,
    inviteCode: '',
    userInviteCode: '',
    invitedCount: 0,
    isLoading: false,
    products: [],
    // 福利码相关
    welfareCode: '',
    taobaoNickname: '',
    inputTaobaoNickname: '',
    showWelfareModal: false
  },

  onLoad(options) {
    // 如果有邀请码参数，保存并跳转到个人中心登录
    if (options.invite_code) {
      const app = getApp();
      app.globalData.inviteCode = options.invite_code;

      // 如果未登录，跳转到个人中心并触发登录
      if (!app.globalData.isLoggedIn) {
        wx.switchTab({
          url: '/pages/profile/profile',
          success: () => {
            setTimeout(() => {
              const pages = getCurrentPages();
              const profilePage = pages[pages.length - 1];
              if (profilePage && profilePage.onLogin) {
                profilePage.onLogin();
              }
            }, 300);
          }
        });
        return;
      }
    }

    this.checkUserStatus();
    this.loadProducts();
  },

  async onShow() {
    // 刷新用户信息后再更新页面状态
    const app = getApp();
    if (app.globalData.isLoggedIn) {
      await app.refreshUserInfo();
    }
    this.checkUserStatus();
  },

  // 加载商品列表
  async loadProducts() {
    const res = await api.getProducts({ limit: 3 });
    if (res.success) {
      this.setData({
        products: res.data.list || []
      });
    }
  },

  // 检查用户状态
  checkUserStatus() {
    const app = getApp();
    const userInfo = app.globalData.userInfo;
    const isPremium = userInfo?.role === 'premium';

    this.setData({
      isPremium,
      nickname: userInfo?.nickname || '高级会员',
      userInviteCode: userInfo?.invite_code || '',
      invitedCount: userInfo?.invited_count || 0,
      welfareCode: userInfo?.welfare_code || '',
      taobaoNickname: userInfo?.taobao_nickname || ''
    });

    // 高级会员加载福利码
    if (isPremium) {
      this.loadWelfareCode();
    }
  },

  // 输入邀请码
  onInputCode(e) {
    this.setData({
      inviteCode: e.detail.value.toUpperCase()
    });
  },

  // 确认升级
  async onUpgrade() {
    const { inviteCode, isLoading } = this.data;

    if (inviteCode.length !== 6) {
      wx.showToast({
        title: '请输入6位邀请码',
        icon: 'none'
      });
      return;
    }

    if (isLoading) return;

    // 检查是否已登录
    const app = getApp();
    if (!app.globalData.isLoggedIn) {
      // 未登录，先登录
      if (api.USE_MOCK) {
        const mockUserInfo = { nickName: '测试用户', avatarUrl: '' };
        await app.login(mockUserInfo);
      } else {
        wx.showToast({
          title: '请先在"我的"页面登录',
          icon: 'none'
        });
        return;
      }
    }

    this.setData({ isLoading: true });

    wx.showLoading({ title: '验证中...' });

    const res = await api.upgradeToPremium(inviteCode);

    wx.hideLoading();
    this.setData({ isLoading: false });

    if (res.success) {
      // 更新全局用户信息
      app.globalData.userInfo = res.data.user;
      app.globalData.isLoggedIn = true;

      wx.showToast({
        title: '升级成功！',
        icon: 'success'
      });

      // 刷新页面状态
      this.checkUserStatus();
    } else {
      wx.showToast({
        title: res.message || '邀请码无效',
        icon: 'none'
      });
    }
  },

  // 跳转邀请页面
  goToInvite() {
    wx.navigateTo({
      url: '/pages/invite/invite'
    });
  },

  // 跳转小店页面
  goToShop() {
    wx.navigateTo({
      url: '/pages/shop/index'
    });
  },

  // 跳转商品详情页
  goToProductDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/product/detail?id=${id}`
    });
  },

  // 加载福利码
  async loadWelfareCode() {
    const res = await api.getWelfareCode();
    if (res.success && res.data) {
      this.setData({
        welfareCode: res.data.welfare_code || '',
        taobaoNickname: res.data.taobao_nickname || ''
      });
    }
  },

  // 打开福利码生成弹窗
  openWelfareModal() {
    this.setData({
      showWelfareModal: true,
      inputTaobaoNickname: ''
    });
  },

  // 关闭福利码弹窗
  closeWelfareModal() {
    this.setData({
      showWelfareModal: false
    });
  },

  // 输入淘宝昵称
  onInputTaobaoNickname(e) {
    this.setData({
      inputTaobaoNickname: e.detail.value
    });
  },

  // 生成福利码
  async generateWelfareCode() {
    const { inputTaobaoNickname, isLoading } = this.data;

    if (!inputTaobaoNickname || inputTaobaoNickname.trim().length === 0) {
      wx.showToast({
        title: '请输入淘宝昵称',
        icon: 'none'
      });
      return;
    }

    if (isLoading) return;

    this.setData({ isLoading: true });
    wx.showLoading({ title: '生成中...' });

    const res = await api.generateWelfareCode(inputTaobaoNickname);

    wx.hideLoading();
    this.setData({ isLoading: false });

    if (res.success) {
      this.setData({
        welfareCode: res.data.welfare_code,
        taobaoNickname: res.data.taobao_nickname,
        showWelfareModal: false
      });

      wx.showToast({
        title: '生成成功！',
        icon: 'success'
      });
    } else {
      wx.showToast({
        title: res.message || '生成失败',
        icon: 'none'
      });
    }
  },

  // 复制福利码
  copyWelfareCode() {
    const { welfareCode } = this.data;
    if (welfareCode) {
      wx.setClipboardData({
        data: welfareCode,
        success: () => {
          wx.showToast({
            title: '已复制',
            icon: 'success'
          });
        }
      });
    }
  },

  // 分享
  onShareAppMessage() {
    const { isPremium, userInviteCode } = this.data;

    if (isPremium && userInviteCode) {
      return {
        title: '邀请你成为高级会员，享专属福利！',
        path: `/pages/benefits/benefits?invite_code=${userInviteCode}`
      };
    }

    return {
      title: '会员中心',
      path: '/pages/benefits/benefits'
    };
  }
});
