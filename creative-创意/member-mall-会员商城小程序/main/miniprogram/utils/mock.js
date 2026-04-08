/**
 * Mock 数据 - 用于测试号环境
 */

// 模拟用户数据
let mockUser = {
  _id: 'mock_user_001',
  openid: 'mock_openid_001',
  nickname: '测试用户',
  avatar_url: '',
  role: 'normal',  // 'normal' | 'premium'
  invite_code: null,
  inviter_id: null,
  invited_count: 0,
  taobao_nickname: null,  // 淘宝昵称
  welfare_code: null      // 福利码
};

// 模拟分类数据
const mockCategories = [
  { _id: 'cat_001', name: '鞋类', icon: '', sort_order: 1, status: 'on' },
  { _id: 'cat_002', name: '服饰', icon: '', sort_order: 2, status: 'on' },
  { _id: 'cat_003', name: '配件', icon: '', sort_order: 3, status: 'on' },
  { _id: 'cat_004', name: '运动', icon: '', sort_order: 4, status: 'on' }
];

// 模拟商品数据
const mockProducts = [
  {
    _id: 'prod_001',
    name: '经典运动跑鞋 Air Max',
    description: '轻量化设计，舒适透气，适合日常运动和跑步。采用最新气垫科技，提供卓越缓震性能。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Shoes1'],
    category_id: 'cat_001',
    price_original: 99900,
    price_member: 79900,
    stock: 100,
    sales: 58,
    status: 'on'
  },
  {
    _id: 'prod_002',
    name: '复古篮球鞋 Jordan 1',
    description: '经典复刻款式，街头潮流必备单品。优质皮革鞋面，经久耐穿。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Shoes2'],
    category_id: 'cat_001',
    price_original: 129900,
    price_member: 99900,
    stock: 50,
    sales: 120,
    status: 'on'
  },
  {
    _id: 'prod_003',
    name: '运动卫衣 Tech Fleece',
    description: '科技面料，保暖透气，运动休闲两相宜。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Hoodie'],
    category_id: 'cat_002',
    price_original: 59900,
    price_member: 45900,
    stock: 200,
    sales: 89,
    status: 'on'
  },
  {
    _id: 'prod_004',
    name: '运动短裤 Dri-FIT',
    description: '速干面料，轻盈舒适，运动必备。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Shorts'],
    category_id: 'cat_002',
    price_original: 29900,
    price_member: 22900,
    stock: 300,
    sales: 156,
    status: 'on'
  },
  {
    _id: 'prod_005',
    name: '运动双肩包',
    description: '大容量设计，多隔层收纳，轻便耐用。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Bag'],
    category_id: 'cat_003',
    price_original: 39900,
    price_member: 29900,
    stock: 150,
    sales: 67,
    status: 'on'
  },
  {
    _id: 'prod_006',
    name: '运动袜 3双装',
    description: '吸汗透气，加厚底部，运动保护。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Socks'],
    category_id: 'cat_003',
    price_original: 9900,
    price_member: 6900,
    stock: 500,
    sales: 289,
    status: 'on'
  },
  {
    _id: 'prod_007',
    name: '瑜伽垫 专业款',
    description: '加厚防滑，环保材质，适合各类运动。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=YogaMat'],
    category_id: 'cat_004',
    price_original: 19900,
    price_member: 15900,
    stock: 80,
    sales: 45,
    status: 'on'
  },
  {
    _id: 'prod_008',
    name: '跳绳 竞速款',
    description: '轴承设计，顺滑不缠绕，燃脂利器。',
    images: ['https://via.placeholder.com/400x400/f5f5f5/333333?text=Rope'],
    category_id: 'cat_004',
    price_original: 4900,
    price_member: 3500,
    stock: 200,
    sales: 178,
    status: 'on'
  }
];

// 模拟订单数据
let mockOrders = [];

// 模拟邀请记录
let mockInviteRecords = [];

// 有效的邀请码（用于测试）
const validInviteCodes = ['TEST88', 'VIP666', 'DEMO01'];

// ==================== Mock API ====================

// 延迟模拟网络请求
const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms));

// 用户模块
const userApi = {
  // 静默登录
  async silentLogin() {
    await delay(200);
    // 从本地存储读取用户状态
    const savedUser = wx.getStorageSync('mock_user');
    if (savedUser) {
      mockUser = savedUser;
      return { success: true, data: mockUser };
    }
    return { success: false, message: '用户未登录' };
  },

  // 登录
  async login(userInfo, inviteCode) {
    await delay(500);

    mockUser.nickname = userInfo.nickName || '测试用户';
    mockUser.avatar_url = userInfo.avatarUrl || '';

    // 检查邀请码
    if (inviteCode && validInviteCodes.includes(inviteCode.toUpperCase())) {
      mockUser.role = 'premium';
      mockUser.invite_code = 'MY' + Math.random().toString(36).substr(2, 4).toUpperCase();
    }

    // 保存到本地
    wx.setStorageSync('mock_user', mockUser);

    return {
      success: true,
      data: {
        user: { ...mockUser },
        isNewUser: true
      }
    };
  },

  // 获取用户信息
  async getUserInfo() {
    await delay(200);
    const savedUser = wx.getStorageSync('mock_user');
    if (savedUser) {
      mockUser = savedUser;
    }
    return { success: true, data: { ...mockUser } };
  },

  // 升级为高级会员
  async upgradeToPremium(inviteCode) {
    await delay(500);

    if (!inviteCode || inviteCode.length !== 6) {
      return { success: false, message: '请输入6位邀请码' };
    }

    if (!validInviteCodes.includes(inviteCode.toUpperCase())) {
      return { success: false, message: '邀请码无效' };
    }

    if (mockUser.role === 'premium') {
      return { success: false, message: '您已经是高级会员' };
    }

    // 升级
    mockUser.role = 'premium';
    mockUser.invite_code = 'MY' + Math.random().toString(36).substr(2, 4).toUpperCase();

    // 保存
    wx.setStorageSync('mock_user', mockUser);

    return {
      success: true,
      message: '升级成功',
      data: { user: { ...mockUser } }
    };
  },

  // 生成福利码
  async generateWelfareCode(taobaoNickname) {
    await delay(500);

    if (mockUser.role !== 'premium') {
      return { success: false, message: '仅高级会员可生成福利码' };
    }

    if (!taobaoNickname || taobaoNickname.trim().length === 0) {
      return { success: false, message: '请填写淘宝昵称' };
    }

    // 如果已有福利码，直接返回
    if (mockUser.welfare_code) {
      return {
        success: true,
        data: {
          welfare_code: mockUser.welfare_code,
          taobao_nickname: mockUser.taobao_nickname
        }
      };
    }

    // 生成唯一福利码（7位以内，无特殊字符）
    // 使用字母+数字组合
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let welfareCode = '';
    for (let i = 0; i < 6; i++) {
      welfareCode += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    mockUser.taobao_nickname = taobaoNickname.trim();
    mockUser.welfare_code = welfareCode;

    // 保存
    wx.setStorageSync('mock_user', mockUser);

    return {
      success: true,
      data: {
        welfare_code: welfareCode,
        taobao_nickname: mockUser.taobao_nickname
      }
    };
  },

  // 获取福利码信息
  async getWelfareCode() {
    await delay(200);

    if (mockUser.role !== 'premium') {
      return { success: false, message: '仅高级会员可查看福利码' };
    }

    return {
      success: true,
      data: {
        welfare_code: mockUser.welfare_code,
        taobao_nickname: mockUser.taobao_nickname
      }
    };
  }
};

// 商品模块
const productApi = {
  // 获取分类
  async getCategories() {
    await delay(200);
    return { success: true, data: mockCategories };
  },

  // 获取商品列表
  async getProducts(params = {}) {
    await delay(300);

    let list = [...mockProducts];

    // 分类筛选
    if (params.category_id) {
      list = list.filter(p => p.category_id === params.category_id);
    }

    // 关键词搜索
    if (params.keyword) {
      const keyword = params.keyword.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(keyword));
    }

    // 分页
    const page = params.page || 1;
    const pageSize = params.page_size || 10;
    const start = (page - 1) * pageSize;
    const pagedList = list.slice(start, start + pageSize);

    return {
      success: true,
      data: {
        list: pagedList,
        total: list.length,
        page,
        page_size: pageSize
      }
    };
  },

  // 获取商品详情
  async getProductDetail(productId) {
    await delay(200);

    const product = mockProducts.find(p => p._id === productId);
    if (product) {
      return { success: true, data: product };
    }
    return { success: false, message: '商品不存在' };
  }
};

// 邀请模块
const inviteApi = {
  // 获取邀请码
  async getInviteCode() {
    await delay(200);

    if (mockUser.role !== 'premium') {
      return { success: false, message: '仅高级会员可获取邀请码' };
    }

    return {
      success: true,
      data: {
        invite_code: mockUser.invite_code,
        invite_count: mockUser.invited_count || 0
      }
    };
  },

  // 验证邀请码
  async verifyInviteCode(code) {
    await delay(300);

    if (!code || code.length !== 6) {
      return { success: true, valid: false };
    }

    const valid = validInviteCodes.includes(code.toUpperCase());

    return {
      success: true,
      valid,
      inviter: valid ? {
        nickname: '会***',
        avatar: ''
      } : null
    };
  },

  // 获取邀请记录
  async getInviteRecords(page = 1, pageSize = 10) {
    await delay(200);

    return {
      success: true,
      data: {
        list: mockInviteRecords,
        total: mockInviteRecords.length,
        page,
        page_size: pageSize
      }
    };
  }
};

// 订单模块
const orderApi = {
  // 获取订单列表
  async getOrders(status = '', page = 1, pageSize = 10) {
    await delay(300);

    let list = [...mockOrders];
    if (status) {
      list = list.filter(o => o.status === status);
    }

    return {
      success: true,
      data: {
        list: list.slice((page - 1) * pageSize, page * pageSize),
        total: list.length,
        page,
        page_size: pageSize
      }
    };
  },

  // 取消订单
  async cancelOrder(orderId) {
    await delay(300);
    const order = mockOrders.find(o => o._id === orderId);
    if (order) {
      order.status = 'cancelled';
    }
    return { success: true, message: '取消成功' };
  },

  // 确认收货
  async confirmOrder(orderId) {
    await delay(300);
    const order = mockOrders.find(o => o._id === orderId);
    if (order) {
      order.status = 'completed';
    }
    return { success: true, message: '确认成功' };
  }
};

module.exports = {
  userApi,
  productApi,
  inviteApi,
  orderApi,
  // 测试用：重置用户状态
  resetUser() {
    mockUser = {
      _id: 'mock_user_001',
      openid: 'mock_openid_001',
      nickname: '测试用户',
      avatar_url: '',
      role: 'normal',
      invite_code: null,
      inviter_id: null,
      invited_count: 0,
      taobao_nickname: null,
      welfare_code: null
    };
    wx.removeStorageSync('mock_user');
  },
  // 有效邀请码提示
  getValidCodes() {
    return validInviteCodes;
  }
};
