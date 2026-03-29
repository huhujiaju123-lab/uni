App({
  onLaunch() {
    if (!wx.cloud) {
      console.error('请使用 2.2.3 以上的基础库以使用云能力')
      return
    }
    wx.cloud.init({
      env: 'cloud1-9giiouev9cd49714',
      traceUser: true
    })
  },

  globalData: {
    envId: 'cloud1-9giiouev9cd49714',
    userInfo: null
  }
})
