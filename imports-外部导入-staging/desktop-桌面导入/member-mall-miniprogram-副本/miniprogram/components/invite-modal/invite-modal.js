// components/invite-modal/invite-modal.js
const api = require('../../utils/api');

Component({
  properties: {
    show: {
      type: Boolean,
      value: false
    }
  },

  data: {
    inviteCode: '',
    isValidCode: false,
    isLoading: false,
    inviterInfo: null
  },

  observers: {
    'show': function(show) {
      if (!show) {
        // 关闭时重置状态
        this.setData({
          inviteCode: '',
          isValidCode: false,
          isLoading: false,
          inviterInfo: null
        });
      }
    }
  },

  methods: {
    // 输入邀请码
    onInput(e) {
      const value = e.detail.value.toUpperCase();
      const isValidCode = value.length === 6;

      this.setData({
        inviteCode: value,
        isValidCode
      });

      // 输入完6位后自动验证
      if (isValidCode) {
        this.verifyCode(value);
      } else {
        this.setData({ inviterInfo: null });
      }
    },

    // 验证邀请码
    async verifyCode(code) {
      const res = await api.verifyInviteCode(code);

      if (res.success && res.valid) {
        this.setData({
          inviterInfo: res.inviter
        });
      } else {
        this.setData({
          inviterInfo: null
        });
      }
    },

    // 确认升级
    async onConfirm() {
      if (!this.data.isValidCode || this.data.isLoading) return;

      this.setData({ isLoading: true });

      try {
        const res = await api.upgradeToPremium(this.data.inviteCode);

        this.setData({ isLoading: false });

        if (res.success) {
          // 更新全局用户信息
          const app = getApp();
          app.globalData.userInfo = res.data.user;

          // 触发成功事件
          this.triggerEvent('success', res.data);
        } else {
          wx.showToast({
            title: res.message || '邀请码无效',
            icon: 'none'
          });
        }
      } catch (e) {
        this.setData({ isLoading: false });
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    },

    // 关闭弹窗
    onClose() {
      this.triggerEvent('close');
    },

    // 点击遮罩关闭
    onMaskTap() {
      this.onClose();
    },

    // 阻止冒泡
    preventBubble() {
      // 阻止点击内容区域时关闭弹窗
    }
  }
});
