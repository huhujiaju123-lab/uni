/**
 * API 封装 - 支持云开发和 Mock 模式切换
 */

// ============================================================
// 【重要】测试号请设为 true，正式环境设为 false
// ============================================================
const USE_MOCK = true;
// ============================================================

const mock = USE_MOCK ? require('./mock') : null;

// 调用云函数
const callFunction = async (name, data = {}) => {
  try {
    const res = await wx.cloud.callFunction({
      name,
      data
    });
    return res.result;
  } catch (error) {
    console.error(`云函数 ${name} 调用失败:`, error);
    return {
      success: false,
      message: '网络错误，请稍后重试',
      error
    };
  }
};

// ==================== 用户相关 ====================

// 静默登录
const silentLogin = () => {
  if (USE_MOCK) return mock.userApi.silentLogin();
  return callFunction('user', { action: 'silentLogin' });
};

// 用户登录/注册
const login = (userInfo, inviteCode = '') => {
  if (USE_MOCK) return mock.userApi.login(userInfo, inviteCode);
  return callFunction('user', {
    action: 'login',
    userInfo,
    invite_code: inviteCode
  });
};

// 获取用户信息
const getUserInfo = () => {
  if (USE_MOCK) return mock.userApi.getUserInfo();
  return callFunction('user', { action: 'getUserInfo' });
};

// 升级为高级会员
const upgradeToPremium = (inviteCode) => {
  if (USE_MOCK) return mock.userApi.upgradeToPremium(inviteCode);
  return callFunction('user', {
    action: 'upgradeToPremium',
    invite_code: inviteCode
  });
};

// 生成福利码
const generateWelfareCode = (taobaoNickname) => {
  if (USE_MOCK) return mock.userApi.generateWelfareCode(taobaoNickname);
  return callFunction('user', {
    action: 'generateWelfareCode',
    taobao_nickname: taobaoNickname
  });
};

// 获取福利码
const getWelfareCode = () => {
  if (USE_MOCK) return mock.userApi.getWelfareCode();
  return callFunction('user', { action: 'getWelfareCode' });
};

// ==================== 商品相关 ====================

// 获取分类列表
const getCategories = () => {
  if (USE_MOCK) return mock.productApi.getCategories();
  return callFunction('product', { action: 'getCategories' });
};

// 获取商品列表
const getProducts = (params = {}) => {
  if (USE_MOCK) return mock.productApi.getProducts(params);
  return callFunction('product', {
    action: 'getProducts',
    ...params
  });
};

// 获取商品详情
const getProductDetail = (productId) => {
  if (USE_MOCK) return mock.productApi.getProductDetail(productId);
  return callFunction('product', {
    action: 'getProductDetail',
    product_id: productId
  });
};

// 搜索商品
const searchProducts = (keyword, page = 1, pageSize = 10) => {
  if (USE_MOCK) return mock.productApi.getProducts({ keyword, page, page_size: pageSize });
  return callFunction('product', {
    action: 'getProducts',
    keyword,
    page,
    page_size: pageSize
  });
};

// ==================== 邀请相关 ====================

// 获取邀请码
const getInviteCode = () => {
  if (USE_MOCK) return mock.inviteApi.getInviteCode();
  return callFunction('invite', { action: 'getInviteCode' });
};

// 验证邀请码
const verifyInviteCode = (code) => {
  if (USE_MOCK) return mock.inviteApi.verifyInviteCode(code);
  return callFunction('invite', {
    action: 'verifyInviteCode',
    code
  });
};

// 获取邀请记录
const getInviteRecords = (page = 1, pageSize = 10) => {
  if (USE_MOCK) return mock.inviteApi.getInviteRecords(page, pageSize);
  return callFunction('invite', {
    action: 'getInviteRecords',
    page,
    page_size: pageSize
  });
};

// ==================== 订单相关 ====================

// 创建订单
const createOrder = (items, addressId, remark = '') => {
  // Mock 模式暂不支持创建订单
  if (USE_MOCK) return { success: false, message: '测试模式暂不支持下单' };
  return callFunction('order', {
    action: 'createOrder',
    items,
    address_id: addressId,
    remark
  });
};

// 获取订单列表
const getOrders = (status = '', page = 1, pageSize = 10) => {
  if (USE_MOCK) return mock.orderApi.getOrders(status, page, pageSize);
  return callFunction('order', {
    action: 'getOrders',
    status,
    page,
    page_size: pageSize
  });
};

// 获取订单详情
const getOrderDetail = (orderId) => {
  if (USE_MOCK) return { success: false, message: '测试模式' };
  return callFunction('order', {
    action: 'getOrderDetail',
    order_id: orderId
  });
};

// 取消订单
const cancelOrder = (orderId) => {
  if (USE_MOCK) return mock.orderApi.cancelOrder(orderId);
  return callFunction('order', {
    action: 'cancelOrder',
    order_id: orderId
  });
};

// 确认收货
const confirmOrder = (orderId) => {
  if (USE_MOCK) return mock.orderApi.confirmOrder(orderId);
  return callFunction('order', {
    action: 'confirmOrder',
    order_id: orderId
  });
};

// ==================== 地址相关 ====================

// 获取地址列表
const getAddressList = () => {
  if (USE_MOCK) return { success: true, data: [] };
  return callFunction('user', { action: 'getAddressList' });
};

// 保存地址
const saveAddress = (address) => {
  if (USE_MOCK) return { success: true, message: '保存成功' };
  return callFunction('user', {
    action: 'saveAddress',
    address
  });
};

// 删除地址
const deleteAddress = (addressId) => {
  if (USE_MOCK) return { success: true, message: '删除成功' };
  return callFunction('user', {
    action: 'deleteAddress',
    address_id: addressId
  });
};

// 设为默认地址
const setDefaultAddress = (addressId) => {
  if (USE_MOCK) return { success: true, message: '设置成功' };
  return callFunction('user', {
    action: 'setDefaultAddress',
    address_id: addressId
  });
};

module.exports = {
  USE_MOCK,
  silentLogin,
  login,
  getUserInfo,
  upgradeToPremium,
  generateWelfareCode,
  getWelfareCode,
  getCategories,
  getProducts,
  getProductDetail,
  searchProducts,
  getInviteCode,
  verifyInviteCode,
  getInviteRecords,
  createOrder,
  getOrders,
  getOrderDetail,
  cancelOrder,
  confirmOrder,
  getAddressList,
  saveAddress,
  deleteAddress,
  setDefaultAddress
};
