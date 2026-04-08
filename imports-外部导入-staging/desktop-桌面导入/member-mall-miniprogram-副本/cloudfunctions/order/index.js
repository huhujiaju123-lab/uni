// 云函数入口文件 - 订单模块
const cloud = require('wx-server-sdk');

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
});

const db = cloud.database();
const _ = db.command;

// 生成订单号
function generateOrderNo() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
  return `${year}${month}${day}${hours}${minutes}${seconds}${random}`;
}

// 云函数入口函数
exports.main = async (event, context) => {
  const { action } = event;
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;

  try {
    switch (action) {
      case 'createOrder':
        return await createOrder(openid, event);

      case 'getOrders':
        return await getOrders(openid, event);

      case 'getOrderDetail':
        return await getOrderDetail(openid, event.order_id);

      case 'cancelOrder':
        return await cancelOrder(openid, event.order_id);

      case 'confirmOrder':
        return await confirmOrder(openid, event.order_id);

      default:
        return { success: false, message: '未知操作' };
    }
  } catch (error) {
    console.error('云函数错误:', error);
    return { success: false, message: '服务器错误', error: error.message };
  }
};

// 创建订单
async function createOrder(openid, params) {
  const { items, address_id, remark } = params;

  if (!items || items.length === 0) {
    return { success: false, message: '请选择商品' };
  }

  if (!address_id) {
    return { success: false, message: '请选择收货地址' };
  }

  // 获取用户信息
  const userResult = await db.collection('users').where({ openid }).get();
  if (userResult.data.length === 0) {
    return { success: false, message: '用户不存在' };
  }
  const user = userResult.data[0];
  const isPremium = user.role === 'premium';

  // 获取收货地址
  const addressResult = await db.collection('addresses').doc(address_id).get();
  if (!addressResult.data) {
    return { success: false, message: '收货地址不存在' };
  }
  const address = addressResult.data;

  // 获取商品信息并计算价格
  const productIds = items.map(item => item.product_id);
  const productsResult = await db.collection('products')
    .where({ _id: _.in(productIds) })
    .get();

  const products = productsResult.data;
  let totalAmount = 0;
  const orderItems = [];

  for (const item of items) {
    const product = products.find(p => p._id === item.product_id);
    if (!product) {
      return { success: false, message: `商品不存在: ${item.product_id}` };
    }

    if (product.stock < item.quantity) {
      return { success: false, message: `商品库存不足: ${product.name}` };
    }

    // 根据会员等级计算价格
    const price = isPremium ? product.price_member : product.price_original;
    const itemTotal = price * item.quantity;
    totalAmount += itemTotal;

    orderItems.push({
      product_id: product._id,
      product_name: product.name,
      product_image: product.images[0] || '',
      price: price,
      quantity: item.quantity
    });
  }

  // 创建订单
  const orderNo = generateOrderNo();
  const order = {
    order_no: orderNo,
    user_id: user._id,
    openid: openid,
    items: orderItems,
    total_amount: totalAmount,
    pay_amount: totalAmount,
    status: 'pending',
    address: {
      name: address.name,
      phone: address.phone,
      province: address.province,
      city: address.city,
      district: address.district,
      detail: address.detail
    },
    remark: remark || '',
    created_at: db.serverDate(),
    updated_at: db.serverDate()
  };

  const createResult = await db.collection('orders').add({ data: order });

  // 扣减库存
  for (const item of items) {
    await db.collection('products').doc(item.product_id).update({
      data: {
        stock: _.inc(-item.quantity),
        sales: _.inc(item.quantity)
      }
    });
  }

  return {
    success: true,
    data: {
      order_id: createResult._id,
      order_no: orderNo,
      pay_amount: totalAmount
      // 实际项目中这里需要调用微信支付接口，返回支付参数
    }
  };
}

// 获取订单列表
async function getOrders(openid, params) {
  const { status, page = 1, page_size = 10 } = params;

  let query = { openid };
  if (status) {
    query.status = status;
  }

  // 获取总数
  const countResult = await db.collection('orders').where(query).count();

  // 分页查询
  const skip = (page - 1) * page_size;
  const result = await db.collection('orders')
    .where(query)
    .orderBy('created_at', 'desc')
    .skip(skip)
    .limit(page_size)
    .get();

  return {
    success: true,
    data: {
      list: result.data,
      total: countResult.total,
      page,
      page_size
    }
  };
}

// 获取订单详情
async function getOrderDetail(openid, orderId) {
  const result = await db.collection('orders').doc(orderId).get();

  if (!result.data) {
    return { success: false, message: '订单不存在' };
  }

  // 验证订单归属
  if (result.data.openid !== openid) {
    return { success: false, message: '无权查看此订单' };
  }

  return { success: true, data: result.data };
}

// 取消订单
async function cancelOrder(openid, orderId) {
  const orderResult = await db.collection('orders').doc(orderId).get();

  if (!orderResult.data) {
    return { success: false, message: '订单不存在' };
  }

  const order = orderResult.data;

  if (order.openid !== openid) {
    return { success: false, message: '无权操作此订单' };
  }

  if (order.status !== 'pending') {
    return { success: false, message: '只能取消待付款订单' };
  }

  // 更新订单状态
  await db.collection('orders').doc(orderId).update({
    data: {
      status: 'cancelled',
      updated_at: db.serverDate()
    }
  });

  // 恢复库存
  for (const item of order.items) {
    await db.collection('products').doc(item.product_id).update({
      data: {
        stock: _.inc(item.quantity),
        sales: _.inc(-item.quantity)
      }
    });
  }

  return { success: true, message: '取消成功' };
}

// 确认收货
async function confirmOrder(openid, orderId) {
  const orderResult = await db.collection('orders').doc(orderId).get();

  if (!orderResult.data) {
    return { success: false, message: '订单不存在' };
  }

  const order = orderResult.data;

  if (order.openid !== openid) {
    return { success: false, message: '无权操作此订单' };
  }

  if (order.status !== 'shipped') {
    return { success: false, message: '只能确认已发货订单' };
  }

  await db.collection('orders').doc(orderId).update({
    data: {
      status: 'completed',
      completed_at: db.serverDate(),
      updated_at: db.serverDate()
    }
  });

  return { success: true, message: '确认收货成功' };
}
