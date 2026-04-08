// app.js
const api = require('./utils/api');

App({
  globalData: {
    userInfo: null,
    isLoggedIn: false,
    systemInfo: null,
    useMock: api.USE_MOCK,  // 是否使用 Mock 模式
    // 【重要】管理员 openid 列表，只有这些人能进入管理后台
    // 登录后在控制台查看自己的 openid，添加到这里
    adminOpenids: [
      'ooHOD16iHGBUllhlP3fI5hSbSguU'
    ]
  },

  onLaunch(options) {
    // 测试模式提示
    if (api.USE_MOCK) {
      console.log('=================================');
      console.log('当前为 Mock 测试模式');
      console.log('有效邀请码: TEST88, VIP666, DEMO01');
      console.log('=================================');
    }

    // 初始化云开发
    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上的基础库以使用云能力');
    } else {
      wx.cloud.init({
        // 【重要】请将下方的环境ID替换为你的云开发环境ID
        // 在微信开发者工具中：云开发控制台 -> 设置 -> 环境ID
        env: 'cloud1-6gna54ku9bfb68ac',
        traceUser: true
      });
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
