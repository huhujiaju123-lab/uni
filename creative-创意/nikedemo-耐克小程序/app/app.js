App({
  globalData: {
    userInfo: {
      nickName: "新晋用户",
      avatarUrl: "https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwBHJr4sKraE7iaw/0", // 微信默认灰头像
      level: 'normal' // 初始等级：normal (普通), premium (高级)
    }
  },
  onLaunch() {
    console.log('小程序启动，当前身份：', this.globalData.userInfo.level);
  }
})
