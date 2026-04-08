// 云函数入口文件 - 管理后台模块
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;

// 【重要】管理员 openid 列表 - 部署前必须配置！
// 将你的 openid 添加到这里，只有列表中的人能调用管理接口
const ADMIN_OPENIDS = [
  'ooHOD16iHGBUllhlP3fI5hSbSguU'
];

// 生成邀请码
function generateInviteCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
}

// 云函数入口
exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;
  const { action } = event;

  // 验证管理员权限
  if (ADMIN_OPENIDS.length > 0 && !ADMIN_OPENIDS.includes(openid)) {
    console.log('非管理员尝试访问:', openid);
    return { success: false, message: '无权限访问管理后台' };
  }

  try {
    switch (action) {
      // ========== 商品管理 ==========
      case 'getProductList':
        return await getProductList(event);
      case 'addProduct':
        return await addProduct(event.product);
      case 'updateProduct':
        return await updateProduct(event.product_id, event.product);
      case 'deleteProduct':
        return await deleteProduct(event.product_id);

      // ========== 会员管理 ==========
      case 'getUserList':
        return await getUserList(event);
      case 'getUserDetail':
        return await getUserDetail(event.user_id);

      // ========== 官方邀请码管理 ==========
      case 'getInviteCodeList':
        return await getInviteCodeList(event);
      case 'generateOfficialInviteCode':
        return await generateOfficialInviteCode(event.remark);
      case 'deleteInviteCode':
        return await deleteInviteCode(event.code_id);
      case 'updateInviteCodeStatus':
        return await updateInviteCodeStatus(event.code_id, event.status);

      // ========== 福利码查询 ==========
      case 'getWelfareCodeList':
        return await getWelfareCodeList(event);

      // ========== 统计数据 ==========
      case 'getStatistics':
        return await getStatistics();

      default:
        return { success: false, message: '未知操作' };
    }
  } catch (error) {
    console.error('管理云函数执行错误:', error);
    return { success: false, message: '服务器错误', error: error.message };
  }
};

// ========== 商品管理 ==========

async function getProductList(params) {
  const { page = 1, page_size = 20 } = params;
  
  const countRes = await db.collection('products').count();
  const total = countRes.total;

  const listRes = await db.collection('products')
    .orderBy('created_at', 'desc')
    .skip((page - 1) * page_size)
    .limit(page_size)
    .get();

  return {
    success: true,
    data: {
      list: listRes.data,
      total,
      page,
      page_size
    }
  };
}

async function addProduct(product) {
  const newProduct = {
    ...product,
    status: product.status || 'on',
    created_at: db.serverDate(),
    updated_at: db.serverDate()
  };

  const res = await db.collection('products').add({ data: newProduct });
  return { success: true, data: { _id: res._id }, message: '添加成功' };
}

async function updateProduct(productId, product) {
  await db.collection('products').doc(productId).update({
    data: {
      ...product,
      updated_at: db.serverDate()
    }
  });
  return { success: true, message: '更新成功' };
}

async function deleteProduct(productId) {
  await db.collection('products').doc(productId).remove();
  return { success: true, message: '删除成功' };
}

// ========== 会员管理 ==========

async function getUserList(params) {
  const { page = 1, page_size = 20, role } = params;
  
  let query = db.collection('users');
  if (role) {
    query = query.where({ role });
  }

  const countRes = await query.count();
  const total = countRes.total;

  const listRes = await query
    .orderBy('created_at', 'desc')
    .skip((page - 1) * page_size)
    .limit(page_size)
    .get();

  return {
    success: true,
    data: {
      list: listRes.data,
      total,
      page,
      page_size
    }
  };
}

async function getUserDetail(userId) {
  const res = await db.collection('users').doc(userId).get();
  if (res.data) {
    return { success: true, data: res.data };
  }
  return { success: false, message: '用户不存在' };
}

// ========== 官方邀请码管理 ==========

async function getInviteCodeList(params) {
  const { page = 1, page_size = 20 } = params;
  
  const countRes = await db.collection('invite_codes').count();
  const total = countRes.total;

  const listRes = await db.collection('invite_codes')
    .orderBy('created_at', 'desc')
    .skip((page - 1) * page_size)
    .limit(page_size)
    .get();

  return {
    success: true,
    data: {
      list: listRes.data,
      total,
      page,
      page_size
    }
  };
}

async function generateOfficialInviteCode(remark = '') {
  // 生成唯一邀请码
  let code = generateInviteCode();
  let checkRes = await db.collection('invite_codes').where({ code }).get();
  while (checkRes.data.length > 0) {
    code = generateInviteCode();
    checkRes = await db.collection('invite_codes').where({ code }).get();
  }

  // 也检查用户邀请码是否重复
  let userCheck = await db.collection('users').where({ invite_code: code }).get();
  while (userCheck.data.length > 0) {
    code = generateInviteCode();
    userCheck = await db.collection('users').where({ invite_code: code }).get();
  }

  const newCode = {
    code,
    remark,
    status: 'active',
    used_count: 0,
    created_at: db.serverDate()
  };

  const res = await db.collection('invite_codes').add({ data: newCode });
  newCode._id = res._id;

  return { success: true, data: newCode, message: '生成成功' };
}

async function deleteInviteCode(codeId) {
  await db.collection('invite_codes').doc(codeId).remove();
  return { success: true, message: '删除成功' };
}

async function updateInviteCodeStatus(codeId, status) {
  await db.collection('invite_codes').doc(codeId).update({
    data: { status }
  });
  return { success: true, message: '更新成功' };
}

// ========== 福利码查询 ==========

async function getWelfareCodeList(params) {
  const { page = 1, page_size = 20 } = params;
  
  const query = db.collection('users').where({
    welfare_code: _.neq(null)
  });

  const countRes = await query.count();
  const total = countRes.total;

  const listRes = await query
    .field({
      _id: true,
      nickname: true,
      welfare_code: true,
      taobao_nickname: true,
      created_at: true
    })
    .orderBy('created_at', 'desc')
    .skip((page - 1) * page_size)
    .limit(page_size)
    .get();

  return {
    success: true,
    data: {
      list: listRes.data,
      total,
      page,
      page_size
    }
  };
}

// ========== 统计数据 ==========

async function getStatistics() {
  const [totalUsers, premiumUsers, totalProducts, activeInviteCodes, welfareUsers] = await Promise.all([
    db.collection('users').count(),
    db.collection('users').where({ role: 'premium' }).count(),
    db.collection('products').where({ status: 'on' }).count(),
    db.collection('invite_codes').where({ status: 'active' }).count(),
    db.collection('users').where({ welfare_code: _.neq(null) }).count()
  ]);

  return {
    success: true,
    data: {
      totalUsers: totalUsers.total,
      premiumUsers: premiumUsers.total,
      normalUsers: totalUsers.total - premiumUsers.total,
      totalProducts: totalProducts.total,
      activeInviteCodes: activeInviteCodes.total,
      welfareUsers: welfareUsers.total
    }
  };
}
