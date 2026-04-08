// pages/invite/invite.js
const api = require('../../utils/api');
const util = require('../../utils/util');

Page({
  data: {
    inviteCode: '',
    inviteCount: 0,
    records: []
  },

  onLoad() {
    this.loadInviteInfo();
    this.loadInviteRecords();
  },

  // 加载邀请信息
  async loadInviteInfo() {
    const res = await api.getInviteCode();
    if (res.success) {
      this.setData({
        inviteCode: res.data.invite_code,
        inviteCount: res.data.invite_count
      });
    } else {
      util.showError(res.message || '获取邀请码失败');
    }
  },

  // 加载邀请记录
  async loadInviteRecords() {
    const res = await api.getInviteRecords(1, 20);
    if (res.success) {
      const records = res.data.list.map(item => ({
        ...item,
        timeText: this.formatTime(item.created_at)
      }));
      this.setData({ records });
    }
  },

  // 格式化时间
  formatTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    if (diff < 2592000000) return Math.floor(diff / 86400000) + '天前';

    return util.formatDate(date, 'MM-DD');
  },

  // 复制邀请码
  copyCode() {
    wx.setClipboardData({
      data: this.data.inviteCode,
      success: () => {
        wx.showToast({
          title: '已复制',
          icon: 'success'
        });
      }
    });
  },

  // 分享
  onShareAppMessage() {
    return {
      title: '邀请你成为高级会员，享专属折扣！',
      path: `/pages/index/index?invite_code=${this.data.inviteCode}`
    };
  }
});
