// pages/index/index.js
const api = require('../../utils/api');
const util = require('../../utils/util');

Page({
  data: {
    categories: [],
    currentCategory: '',
    products: [],
    userRole: 'normal',
    isLoading: false,
    isRefreshing: false,
    hasMore: true,
    page: 1,
    pageSize: 10
  },

  onLoad() {
    this.initData();
  },

  onShow() {
    // 更新用户角色
    const app = getApp();
    if (app.globalData.userInfo) {
      this.setData({
        userRole: app.globalData.userInfo.role || 'normal'
      });
    }
  },

  // 初始化数据
  async initData() {
    await this.loadCategories();
    await this.loadProducts();
  },

  // 加载分类
  async loadCategories() {
    const res = await api.getCategories();
    if (res.success && res.data.length > 0) {
      this.setData({
        categories: res.data,
        currentCategory: res.data[0]._id
      });
    }
  },

  // 加载商品列表
  async loadProducts(isLoadMore = false) {
    if (this.data.isLoading) return;
    if (isLoadMore && !this.data.hasMore) return;

    this.setData({ isLoading: true });

    const page = isLoadMore ? this.data.page + 1 : 1;

    const res = await api.getProducts({
      category_id: this.data.currentCategory,
      page: page,
      page_size: this.data.pageSize
    });

    if (res.success) {
      const newProducts = res.data.list.map(item => ({
        ...item,
        originalPrice: util.formatPrice(item.price_original),
        memberPrice: util.formatPrice(item.price_member)
      }));

      const products = isLoadMore
        ? [...this.data.products, ...newProducts]
        : newProducts;

      this.setData({
        products,
        page,
        hasMore: newProducts.length >= this.data.pageSize,
        isLoading: false,
        isRefreshing: false
      });
    } else {
      this.setData({
        isLoading: false,
        isRefreshing: false
      });
      util.showError(res.message || '加载失败');
    }
  },

  // 切换分类
  onCategoryTap(e) {
    const categoryId = e.currentTarget.dataset.id;
    if (categoryId === this.data.currentCategory) return;

    this.setData({
      currentCategory: categoryId,
      products: [],
      page: 1,
      hasMore: true
    });

    this.loadProducts();
  },

  // 下拉刷新
  onRefresh() {
    this.setData({
      isRefreshing: true,
      page: 1,
      hasMore: true
    });
    this.loadProducts();
  },

  // 加载更多
  onLoadMore() {
    this.loadProducts(true);
  },

  // 跳转搜索页
  goToSearch() {
    wx.navigateTo({
      url: '/pages/search/search'
    });
  },

  // 跳转商品详情
  goToDetail(e) {
    const productId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}`
    });
  },

  // 分享
  onShareAppMessage() {
    return {
      title: '会员商城 - 精选好物',
      path: '/pages/index/index'
    };
  }
});
