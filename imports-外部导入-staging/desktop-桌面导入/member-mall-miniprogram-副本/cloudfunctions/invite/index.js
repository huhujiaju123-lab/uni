// 云函数入口文件 - 邀请模块
const cloud = require('wx-server-sdk');

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

const db = cloud.database();
const _ = db.command;

// 云函数入口函数
exports.main = async (event, context) => {
  const { action } = event;
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;

  try {
    switch (action) {
      case 'getInviteCode':
        return await getInviteCode(openid);

      case 'verifyInviteCode':
        return await verifyInviteCode(event.code);

      case 'getInviteRecords':
        return await getInviteRecords(openid, event.page, event.page_size);

      default:
        return { success: false, message: '未知操作' };
    }
  } catch (error) {
    console.error('云函数错误:', error);
    return { success: false, message: '服务器错误', error: error.message };
  }
};

// 获取邀请码（仅高级会员可用）
async function getInviteCode(openid) {
  const userResult = await db.collection('users').where({ openid }).get();

  if (userResult.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }

  const user = userResult.data[0];

  if (user.role !== 'premium') {
    return { success: false, message: '仅高级会员可获取邀请码' };
  }

  return {
    success: true,
    data: {
      invite_code: user.invite_code,
      invite_count: user.invited_count || 0
    }
  };
}

// 验证邀请码
async function verifyInviteCode(code) {
  if (!code || code.length !== 6) {
    return { success: true, valid: false };
  }

  const result = await db.collection('users').where({
    invite_code: code.toUpperCase(),
    role: 'premium'
  }).get();

  if (result.data.length === 0) {
    return { success: true, valid: false };
  }

  const inviter = result.data[0];

  return {
    success: true,
    valid: true,
    inviter: {
      nickname: inviter.nickname ? inviter.nickname.substring(0, 1) + '***' : '会员用户',
      avatar: inviter.avatar_url || ''
    }
  };
}

// 获取邀请记录
async function getInviteRecords(openid, page = 1, pageSize = 10) {
  // 先获取当前用户
  const userResult = await db.collection('users').where({ openid }).get();

  if (userResult.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }

  const user = userResult.data[0];

  if (user.role !== 'premium') {
    return { success: false, message: '仅高级会员可查看邀请记录' };
  }

  // 获取邀请记录总数
  const countResult = await db.collection('invite_records')
    .where({ inviter_id: user._id })
    .count();

  // 分页查询
  const skip = (page - 1) * pageSize;
  const recordsResult = await db.collection('invite_records')
    .where({ inviter_id: user._id })
    .orderBy('created_at', 'desc')
    .skip(skip)
    .limit(pageSize)
    .get();

  // 获取被邀请人信息
  const records = recordsResult.data;
  const inviteeIds = records.map(r => r.invitee_id);

  let invitees = [];
  if (inviteeIds.length > 0) {
    const inviteesResult = await db.collection('users')
      .where({ _id: _.in(inviteeIds) })
      .field({ nickname: true, avatar_url: true, created_at: true })
      .get();
    invitees = inviteesResult.data;
  }

  // 合并数据
  const list = records.map(record => {
    const invitee = invitees.find(u => u._id === record.invitee_id) || {};
    return {
      _id: record._id,
      nickname: invitee.nickname || '会员用户',
      avatar_url: invitee.avatar_url || '',
      created_at: record.created_at
    };
  });

  return {
    success: true,
    data: {
      list,
      total: countResult.total,
      page,
      page_size: pageSize
    }
  };
}
