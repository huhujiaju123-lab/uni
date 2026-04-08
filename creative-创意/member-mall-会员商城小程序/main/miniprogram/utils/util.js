/**
 * 通用工具函数
 */

/**
 * 格式化价格 (分转元)
 * @param {Number} price - 价格(分)
 * @returns {String} 格式化后的价格
 */
const formatPrice = (price) => {
  if (typeof price !== 'number') return '0.00';
  return (price / 100).toFixed(2);
};

/**
 * 根据用户角色获取价格显示配置
 * @param {Object} product - 商品对象
 * @param {String} userRole - 用户角色 'normal' | 'premium'
 * @returns {Object} 价格显示配置
 */
const getPriceDisplay = (product, userRole) => {
  const originalPrice = formatPrice(product.price_original);
  const memberPrice = formatPrice(product.price_member);

  if (userRole === 'premium') {
    return {
      mainPrice: memberPrice,
      mainPriceClass: 'price-member',  // 橙色
      showOriginal: true,
      originalPrice: originalPrice,
      showMemberHint: false
    };
  } else {
    return {
      mainPrice: originalPrice,
      mainPriceClass: 'price-normal',  // 黑色
      showOriginal: false,
      originalPrice: originalPrice,
      showMemberHint: true,
      memberHintPrice: memberPrice
    };
  }
};

/**
 * 格式化日期
 * @param {Date|String|Number} date - 日期
 * @param {String} format - 格式，默认 'YYYY-MM-DD HH:mm:ss'
 * @returns {String} 格式化后的日期字符串
 */
const formatDate = (date, format = 'YYYY-MM-DD HH:mm:ss') => {
  if (!date) return '';

  const d = new Date(date);
  if (isNaN(d.getTime())) return '';

  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
};

/**
 * 生成订单号
 * @returns {String} 订单号
 */
const generateOrderNo = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0');

  return `${year}${month}${day}${hours}${minutes}${seconds}${random}`;
};

/**
 * 防抖函数
 * @param {Function} fn - 要执行的函数
 * @param {Number} delay - 延迟时间(毫秒)
 * @returns {Function} 防抖后的函数
 */
const debounce = (fn, delay = 300) => {
  let timer = null;
  return function (...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
};

/**
 * 节流函数
 * @param {Function} fn - 要执行的函数
 * @param {Number} interval - 间隔时间(毫秒)
 * @returns {Function} 节流后的函数
 */
const throttle = (fn, interval = 300) => {
  let lastTime = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastTime >= interval) {
      lastTime = now;
      fn.apply(this, args);
    }
  };
};

/**
 * 显示加载提示
 * @param {String} title - 提示文字
 */
const showLoading = (title = '加载中...') => {
  wx.showLoading({
    title,
    mask: true
  });
};

/**
 * 隐藏加载提示
 */
const hideLoading = () => {
  wx.hideLoading();
};

/**
 * 显示成功提示
 * @param {String} title - 提示文字
 */
const showSuccess = (title) => {
  wx.showToast({
    title,
    icon: 'success',
    duration: 2000
  });
};

/**
 * 显示错误提示
 * @param {String} title - 提示文字
 */
const showError = (title) => {
  wx.showToast({
    title,
    icon: 'none',
    duration: 2000
  });
};

/**
 * 显示确认弹窗
 * @param {Object} options - 配置项
 * @returns {Promise} 用户选择结果
 */
const showConfirm = (options) => {
  return new Promise((resolve) => {
    wx.showModal({
      title: options.title || '提示',
      content: options.content || '',
      showCancel: options.showCancel !== false,
      cancelText: options.cancelText || '取消',
      confirmText: options.confirmText || '确定',
      confirmColor: options.confirmColor || '#000000',
      success: (res) => {
        resolve(res.confirm);
      }
    });
  });
};

/**
 * 订单状态映射
 */
const ORDER_STATUS = {
  pending: { text: '待付款', color: '#FA5400' },
  paid: { text: '待发货', color: '#000000' },
  shipped: { text: '待收货', color: '#07C160' },
  completed: { text: '已完成', color: '#999999' },
  cancelled: { text: '已取消', color: '#999999' }
};

/**
 * 获取订单状态显示
 * @param {String} status - 订单状态
 * @returns {Object} 状态显示配置
 */
const getOrderStatus = (status) => {
  return ORDER_STATUS[status] || { text: '未知', color: '#999999' };
};

/**
 * 检查是否登录
 * @returns {Boolean} 是否登录
 */
const checkLogin = () => {
  const app = getApp();
  if (!app.globalData.isLoggedIn) {
    wx.showToast({
      title: '请先登录',
      icon: 'none'
    });
    return false;
  }
  return true;
};

/**
 * 获取用户角色
 * @returns {String} 用户角色 'normal' | 'premium' | null
 */
const getUserRole = () => {
  const app = getApp();
  return app.globalData.userInfo?.role || null;
};

/**
 * 是否为高级会员
 * @returns {Boolean}
 */
const isPremiumUser = () => {
  return getUserRole() === 'premium';
};

module.exports = {
  formatPrice,
  getPriceDisplay,
  formatDate,
  generateOrderNo,
  debounce,
  throttle,
  showLoading,
  hideLoading,
  showSuccess,
  showError,
  showConfirm,
  ORDER_STATUS,
  getOrderStatus,
  checkLogin,
  getUserRole,
  isPremiumUser
};
