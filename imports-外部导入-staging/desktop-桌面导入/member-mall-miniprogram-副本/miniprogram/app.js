// app.js
const api = require('./utils/api');

App({
  globalData: {
    userInfo: null,
    isLoggedIn: false,
    systemInfo: null,
    useMock: api.USE_MOCK  // 是否使用 Mock 模式
  },

  onLaunch(options) {
    // 测试模式提示
    if (api.USE_MOCK) {
      console.log('=================================');
      console.log('当前为 Mock 测试模式');
      console.log('有效邀请码: TEST88, VIP666, DEMO01');
      console.log('=================================');
    }

    // 仅在非 Mock 模式下初始化云开发
    if (!api.USE_MOCK) {
      if (!wx.cloud) {
        console.error('请使用 2.2.3 或以上的基础库以使用云能力');
      } else {
        wx.cloud.init({
          env: 'your-env-id', // TODO: 替换为你的云环境ID
          traceUser: true
        });
      }
    }

    // 获取系统信息
    this.getSystemInfo();

    // 处理邀请码参数
    if (options.query && options.query.invite_code) {
      this.globalData.inviteCode = options.query.invite_code;
    }

    // 尝试静默登录
    this.silentLogin();
  },

  // 获取系统信息
  getSystemInfo() {
    try {
      const systemInfo = wx.getSystemInfoSync();
      this.globalData.systemInfo = systemInfo;

      // 计算安全区域
      const menuButton = wx.getMenuButtonBoundingClientRect();
      this.globalData.statusBarHeight = systemInfo.statusBarHeight;
      this.globalData.navBarHeight = (menuButton.top - systemInfo.statusBarHeight) * 2 + menuButton.height;
      this.globalData.menuButton = menuButton;
    } catch (e) {
      console.error('获取系统信息失败', e);
    }
  },

  // 静默登录
  async silentLogin() {
    try {
      const result = await api.silentLogin();

      if (result.success && result.data) {
        this.globalData.userInfo = result.data;
        this.globalData.isLoggedIn = true;

        // 通知页面更新
        if (this.userInfoReadyCallback) {
          this.userInfoReadyCallback(result.data);
        }
      }
    } catch (e) {
      console.log('静默登录失败或用户未注册', e);
    }
  },

  // 用户登录
  async login(userProfile) {
    try {
      wx.showLoading({ title: '登录中...' });

      const inviteCode = this.globalData.inviteCode || '';

      const result = await api.login(userProfile, inviteCode);

      wx.hideLoading();

      if (result.success) {
        this.globalData.userInfo = result.data.user;
        this.globalData.isLoggedIn = true;

        // 清除邀请码
        this.globalData.inviteCode = null;

        return { success: true, data: result.data };
      } else {
        return { success: false, message: result.message };
      }
    } catch (e) {
      wx.hideLoading();
      console.error('登录失败', e);
      return { success: false, message: '网络错误，请重试' };
    }
  },

  // 刷新用户信息
  async refreshUserInfo() {
    try {
      const result = await api.getUserInfo();

      if (result.success) {
        this.globalData.userInfo = result.data;
        return result.data;
      }
    } catch (e) {
      console.error('刷新用户信息失败', e);
    }
    return null;
  },

  // 退出登录
  logout() {
    // 清除全局数据
    this.globalData.userInfo = null;
    this.globalData.isLoggedIn = false;

    // 清除本地存储
    wx.removeStorageSync('mock_user');
  }
});
