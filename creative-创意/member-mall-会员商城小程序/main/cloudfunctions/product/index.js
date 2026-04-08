// 云函数入口文件 - 商品模块
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

// 云函数入口
exports.main = async (event, context) => {
  const { action } = event;

  try {
    switch (action) {
      case 'getCategories':
        return await getCategories();
      case 'getProducts':
        return await getProducts(event);
      case 'getProductDetail':
        return await getProductDetail(event.product_id);
      default:
        return { success: false, message: '未知操作' };
    }
  } catch (error) {
    console.error('云函数执行错误:', error);
    return { success: false, message: '服务器错误', error: error.message };
  }
};

// 获取分类
async function getCategories() {
  const res = await db.collection('categories')
    .where({ status: 'on' })
    .orderBy('sort_order', 'asc')
    .get();
  return { success: true, data: res.data };
}

// 获取商品列表
async function getProducts(params) {
  const { category_id, keyword, page = 1, page_size = 10, limit } = params;
  
  let query = db.collection('products').where({ status: 'on' });

  if (category_id) {
    query = db.collection('products').where({
      status: 'on',
      category_id
    });
  }

  // 获取总数
  const countRes = await query.count();
  const total = countRes.total;

  // 分页获取
  const actualLimit = limit || page_size;
  const skip = (page - 1) * actualLimit;
  
  const listRes = await query
    .orderBy('created_at', 'desc')
    .skip(skip)
    .limit(actualLimit)
    .get();

  // 格式化价格
  const list = listRes.data.map(item => ({
    ...item,
    originalPrice: (item.price_original / 100).toFixed(2),
    memberPrice: (item.price_member / 100).toFixed(2)
  }));

  return {
    success: true,
    data: {
      list,
      total,
      page,
      page_size: actualLimit
    }
  };
}

// 获取商品详情
async function getProductDetail(productId) {
  const res = await db.collection('products').doc(productId).get();
  
  if (res.data) {
    const product = {
      ...res.data,
      originalPrice: (res.data.price_original / 100).toFixed(2),
      memberPrice: (res.data.price_member / 100).toFixed(2)
    };
    return { success: true, data: product };
  }
  
  return { success: false, message: '商品不存在' };
}
