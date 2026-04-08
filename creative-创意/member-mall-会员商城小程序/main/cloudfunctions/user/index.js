// 云函数入口文件 - 用户模块
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;

// ============================================================
// 【配置】每个高级会员的邀请上限
// 修改此值可调整所有新高级会员的默认邀请名额
// 注意：已有用户的 invite_limit 需要在数据库中手动修改
// ============================================================
const DEFAULT_INVITE_LIMIT = 5;
// ============================================================

// 生成邀请码（6位）
function generateInviteCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
}

// 生成福利码（6位）
function generateWelfareCode() {
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

  try {
    switch (action) {
      case 'silentLogin':
        return await silentLogin(openid);
      case 'login':
        return await login(openid, event.userInfo, event.invite_code);
      case 'getUserInfo':
        return await getUserInfo(openid);
      case 'upgradeToPremium':
        return await upgradeToPremium(openid, event.invite_code);
      case 'generateWelfareCode':
        return await generateWelfareCodeForUser(openid, event.taobao_nickname);
      case 'getWelfareCode':
        return await getWelfareCode(openid);
      case 'updateProfile':
        return await updateProfile(openid, event.avatar_url, event.nickname);
      default:
        return { success: false, message: '未知操作' };
    }
  } catch (error) {
    console.error('云函数执行错误:', error);
    return { success: false, message: '服务器错误', error: error.message };
  }
};

// 静默登录
async function silentLogin(openid) {
  const userRes = await db.collection('users').where({ openid }).get();
  if (userRes.data.length > 0) {
    return { success: true, data: userRes.data[0] };
  }
  return { success: false, message: '用户未注册' };
}

// 登录/注册
async function login(openid, userInfo, inviteCode) {
  const userRes = await db.collection('users').where({ openid }).get();
  
  if (userRes.data.length > 0) {
    // 已存在用户，更新信息
    const user = userRes.data[0];
    await db.collection('users').doc(user._id).update({
      data: {
        nickname: userInfo.nickName || user.nickname,
        avatar_url: userInfo.avatarUrl || user.avatar_url,
        updated_at: db.serverDate()
      }
    });
    const updatedUser = await db.collection('users').doc(user._id).get();
    return { success: true, data: { user: updatedUser.data, isNewUser: false } };
  }

  // 新用户注册
  let role = 'normal';
  let userInviteCode = null;
  let inviterId = null;

  // 检查邀请码是否有效
  if (inviteCode) {
    // 先检查官方邀请码
    const officialCode = await db.collection('invite_codes').where({
      code: inviteCode.toUpperCase(),
      status: 'active'
    }).get();

    if (officialCode.data.length > 0) {
      role = 'premium';
      userInviteCode = generateInviteCode();
      // 更新官方邀请码使用次数
      await db.collection('invite_codes').doc(officialCode.data[0]._id).update({
        data: { used_count: _.inc(1) }
      });
    } else {
      // 检查用户邀请码
      const inviter = await db.collection('users').where({
        invite_code: inviteCode.toUpperCase(),
        role: 'premium'
      }).get();

      if (inviter.data.length > 0) {
        const inviterData = inviter.data[0];
        const inviteLimit = inviterData.invite_limit || DEFAULT_INVITE_LIMIT;
        const invitedCount = inviterData.invited_count || 0;

        // 检查邀请者是否还有名额（官方邀请码不受限制）
        if (invitedCount >= inviteLimit) {
          // 邀请码已达上限，用户仍可注册但不会成为高级会员
          console.log('邀请码已达使用上限:', inviteCode);
        } else {
          role = 'premium';
          userInviteCode = generateInviteCode();
          inviterId = inviterData._id;
          // 增加邀请者的邀请数量
          await db.collection('users').doc(inviterId).update({
            data: { invited_count: _.inc(1) }
          });
        }
      }
    }
  }

  // 创建新用户
  const newUser = {
    openid,
    nickname: userInfo.nickName || '会员用户',
    avatar_url: userInfo.avatarUrl || '',
    role,
    invite_code: userInviteCode,
    invite_limit: role === 'premium' ? DEFAULT_INVITE_LIMIT : 0,  // 高级会员设置邀请上限
    inviter_id: inviterId,
    invited_count: 0,
    taobao_nickname: null,
    welfare_code: null,
    created_at: db.serverDate(),
    updated_at: db.serverDate()
  };

  const addRes = await db.collection('users').add({ data: newUser });
  newUser._id = addRes._id;

  // 如果是通过用户邀请码注册的，创建邀请记录
  if (inviterId) {
    await db.collection('invite_records').add({
      data: {
        inviter_id: inviterId,
        invitee_id: newUser._id,
        invite_code: inviteCode.toUpperCase(),
        created_at: db.serverDate()
      }
    });
  }

  return { success: true, data: { user: newUser, isNewUser: true } };
}

// 获取用户信息
async function getUserInfo(openid) {
  const userRes = await db.collection('users').where({ openid }).get();
  if (userRes.data.length > 0) {
    return { success: true, data: userRes.data[0] };
  }
  return { success: false, message: '用户不存在' };
}

// 升级为高级会员
async function upgradeToPremium(openid, inviteCode) {
  if (!inviteCode || inviteCode.length !== 6) {
    return { success: false, message: '请输入6位邀请码' };
  }

  const userRes = await db.collection('users').where({ openid }).get();
  if (userRes.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }

  const user = userRes.data[0];
  if (user.role === 'premium') {
    return { success: false, message: '您已经是高级会员' };
  }

  // 检查官方邀请码
  const officialCode = await db.collection('invite_codes').where({
    code: inviteCode.toUpperCase(),
    status: 'active'
  }).get();

  let inviterId = null;

  if (officialCode.data.length > 0) {
    // 使用官方邀请码
    await db.collection('invite_codes').doc(officialCode.data[0]._id).update({
      data: { used_count: _.inc(1) }
    });
  } else {
    // 检查用户邀请码
    const inviter = await db.collection('users').where({
      invite_code: inviteCode.toUpperCase(),
      role: 'premium'
    }).get();

    if (inviter.data.length === 0) {
      return { success: false, message: '邀请码无效' };
    }

    const inviterData = inviter.data[0];
    const inviteLimit = inviterData.invite_limit || DEFAULT_INVITE_LIMIT;
    const invitedCount = inviterData.invited_count || 0;

    // 检查邀请者是否还有名额
    if (invitedCount >= inviteLimit) {
      return { success: false, message: '该邀请码已达使用上限' };
    }

    inviterId = inviterData._id;
    // 增加邀请者的邀请数量
    await db.collection('users').doc(inviterId).update({
      data: { invited_count: _.inc(1) }
    });

    // 创建邀请记录
    await db.collection('invite_records').add({
      data: {
        inviter_id: inviterId,
        invitee_id: user._id,
        invite_code: inviteCode.toUpperCase(),
        created_at: db.serverDate()
      }
    });
  }

  // 升级用户
  const newInviteCode = generateInviteCode();
  await db.collection('users').doc(user._id).update({
    data: {
      role: 'premium',
      invite_code: newInviteCode,
      invite_limit: DEFAULT_INVITE_LIMIT,  // 设置邀请上限
      inviter_id: inviterId,
      updated_at: db.serverDate()
    }
  });

  const updatedUser = await db.collection('users').doc(user._id).get();
  return { success: true, message: '升级成功', data: { user: updatedUser.data } };
}

// 生成福利码
async function generateWelfareCodeForUser(openid, taobaoNickname) {
  const userRes = await db.collection('users').where({ openid }).get();
  if (userRes.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }

  const user = userRes.data[0];
  if (user.role !== 'premium') {
    return { success: false, message: '仅高级会员可生成福利码' };
  }

  if (!taobaoNickname || taobaoNickname.trim().length === 0) {
    return { success: false, message: '请填写淘宝昵称' };
  }

  // 如果已有福利码，直接返回
  if (user.welfare_code) {
    return {
      success: true,
      data: {
        welfare_code: user.welfare_code,
        taobao_nickname: user.taobao_nickname
      }
    };
  }

  // 生成唯一福利码
  let welfareCode = generateWelfareCode();
  // 检查是否重复
  let checkRes = await db.collection('users').where({ welfare_code: welfareCode }).get();
  while (checkRes.data.length > 0) {
    welfareCode = generateWelfareCode();
    checkRes = await db.collection('users').where({ welfare_code: welfareCode }).get();
  }

  await db.collection('users').doc(user._id).update({
    data: {
      taobao_nickname: taobaoNickname.trim(),
      welfare_code: welfareCode,
      updated_at: db.serverDate()
    }
  });

  return {
    success: true,
    data: {
      welfare_code: welfareCode,
      taobao_nickname: taobaoNickname.trim()
    }
  };
}

// 获取福利码
async function getWelfareCode(openid) {
  const userRes = await db.collection('users').where({ openid }).get();
  if (userRes.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }

  const user = userRes.data[0];
  return {
    success: true,
    data: {
      welfare_code: user.welfare_code,
      taobao_nickname: user.taobao_nickname
    }
  };
}

// 更新用户头像和昵称
async function updateProfile(openid, avatarUrl, nickname) {
  const userRes = await db.collection('users').where({ openid }).get();
  if (userRes.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }

  const user = userRes.data[0];
  const updateData = { updated_at: db.serverDate() };

  // 支持云存储文件ID (cloud://) 或 http 链接
  if (avatarUrl && (avatarUrl.startsWith('cloud://') || avatarUrl.startsWith('http'))) {
    updateData.avatar_url = avatarUrl;
  }

  if (nickname) {
    updateData.nickname = nickname;
  }

  await db.collection('users').doc(user._id).update({ data: updateData });

  const updatedUser = await db.collection('users').doc(user._id).get();
  return { success: true, data: updatedUser.data };
}
