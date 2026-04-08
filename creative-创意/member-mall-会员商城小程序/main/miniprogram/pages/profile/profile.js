// pages/profile/profile.js
const api = require('../../utils/api');

Page({
  data: {
    isLoggedIn: false,
    isPremium: false,
    userInfo: null,
    showInviteModal: false,
    useMock: api.USE_MOCK,
    isAdmin: false,
    orderCounts: {
      pending: 0,
      paid: 0,
      shipped: 0
    },
    // 设置头像昵称弹窗
    showProfileModal: false,
    tempAvatarUrl: '',
    tempAvatarFileID: '',
    tempNickname: ''
  },

  onLoad() {
    this.checkLoginStatus();
  },

  async onShow() {
    // 刷新用户信息后再更新页面状态
    const app = getApp();
    if (app.globalData.isLoggedIn) {
      await app.refreshUserInfo();
    }
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

    // 检查是否是管理员
    const adminOpenids = app.globalData.adminOpenids || [];
    const isAdmin = userInfo && adminOpenids.includes(userInfo.openid);

    this.setData({
      isLoggedIn,
      userInfo,
      isPremium: userInfo?.role === 'premium',
      isAdmin
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

    // 正式模式：直接登录，然后引导设置头像昵称
    try {
      // 使用空的用户信息登录（云函数会用 openid 识别）
      const result = await app.login({ nickName: '', avatarUrl: '' });

      if (result.success) {
        const user = result.data.user;
        this.setData({
          isLoggedIn: true,
          userInfo: user,
          isPremium: user.role === 'premium'
        });

        // 检查管理员身份
        this.checkLoginStatus();

        wx.showToast({
          title: result.data.isNewUser ? '注册成功' : '登录成功',
          icon: 'success'
        });

        // 引导用户设置头像和昵称
        setTimeout(() => {
          this.promptSetProfile();
        }, 1500);
      } else {
        wx.showToast({
          title: result.message || '登录失败',
          icon: 'none'
        });
      }
    } catch (e) {
      console.log('登录失败', e);
      wx.showToast({
        title: '登录失败，请重试',
        icon: 'none'
      });
    }
  },

  // 引导设置头像和昵称
  promptSetProfile() {
    const { userInfo } = this.data;
    // 如果没有头像或昵称，自动打开设置弹窗
    if (!userInfo.avatar_url || !userInfo.nickname || userInfo.nickname === '会员用户') {
      this.openProfileModal();
    }
  },

  // 打开设置弹窗
  openProfileModal() {
    this.setData({
      showProfileModal: true,
      tempAvatarUrl: '',
      tempAvatarFileID: '',
      tempNickname: this.data.userInfo?.nickname || ''
    });
  },

  // 关闭设置弹窗
  closeProfileModal() {
    this.setData({ showProfileModal: false });
  },

  // 阻止冒泡
  preventBubble() {},

  // 选择头像（在弹窗中）
  async onChooseAvatar(e) {
    const avatarUrl = e.detail.avatarUrl;
    if (!avatarUrl) return;

    wx.showLoading({ title: '上传中...' });

    try {
      const ts = new Date().getTime();
      const rand = Math.random().toString(36).substr(2, 9);
      const uploadRes = await wx.cloud.uploadFile({
        cloudPath: `avatars/${ts}_${rand}.jpg`,
        filePath: avatarUrl
      });

      wx.hideLoading();

      if (uploadRes.fileID) {
        this.setData({
          tempAvatarUrl: avatarUrl,
          tempAvatarFileID: uploadRes.fileID
        });
        wx.showToast({ title: '头像已选择', icon: 'success' });
      }
    } catch (err) {
      wx.hideLoading();
      console.error('上传头像失败:', err);
      wx.showToast({ title: '上传失败', icon: 'none' });
    }
  },

  // 输入昵称（在弹窗中）
  onNicknameInput(e) {
    const nickname = e.detail.value;
    console.log('昵称输入:', nickname);
    if (nickname) {
      this.setData({ tempNickname: nickname });
    }
  },

  // 保存头像和昵称
  async saveProfile() {
    const { tempAvatarFileID, tempNickname, userInfo } = this.data;

    console.log('保存资料:', { tempAvatarFileID, tempNickname, currentNickname: userInfo?.nickname });

    // 检查是否有变更
    const hasAvatarChange = tempAvatarFileID && tempAvatarFileID !== userInfo?.avatar_url;
    const hasNicknameChange = tempNickname && tempNickname !== userInfo?.nickname && tempNickname !== '会员用户';

    console.log('变更检查:', { hasAvatarChange, hasNicknameChange });

    if (!hasAvatarChange && !hasNicknameChange) {
      this.closeProfileModal();
      return;
    }

    wx.showLoading({ title: '保存中...' });

    const avatarToSave = hasAvatarChange ? tempAvatarFileID : null;
    const nicknameToSave = hasNicknameChange ? tempNickname : null;
    console.log('准备保存:', { avatarToSave, nicknameToSave });

    const res = await api.updateProfile(avatarToSave, nicknameToSave);
    console.log('保存结果:', res);

    wx.hideLoading();

    if (res.success) {
      const app = getApp();
      app.globalData.userInfo = res.data;
      this.setData({ userInfo: res.data });
      this.closeProfileModal();
      wx.showToast({ title: '保存成功', icon: 'success' });
    } else {
      wx.showToast({ title: res.message || '保存失败', icon: 'none' });
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

  // 关于我们（显示 openid）
  goToAbout() {
    const { userInfo } = this.data;
    const openid = userInfo?.openid || '未登录';

    wx.showModal({
      title: '你的 openid',
      content: openid,
      showCancel: true,
      cancelText: '关闭',
      confirmText: '复制',
      success: (res) => {
        if (res.confirm && userInfo?.openid) {
          wx.setClipboardData({
            data: userInfo.openid,
            success: () => {
              wx.showToast({ title: '已复制', icon: 'success' });
            }
          });
        }
      }
    });
  },

  // 管理后台
  goToAdmin() {
    wx.navigateTo({
      url: '/pages/admin/admin'
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
        path: `/pages/benefits/benefits?invite_code=${this.data.userInfo.invite_code}`
      };
    }
    return {
      title: '会员商城 - 精选好物',
      path: '/pages/benefits/benefits'
    };
  }
});
