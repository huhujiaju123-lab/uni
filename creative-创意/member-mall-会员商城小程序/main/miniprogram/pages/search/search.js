// pages/search/search.js
const api = require('../../utils/api');
const util = require('../../utils/util');

const HISTORY_KEY = 'search_history';
const MAX_HISTORY = 10;

Page({
  data: {
    keyword: '',
    hasSearched: false,
    products: [],
    isLoading: false,
    hasMore: true,
    page: 1,
    pageSize: 10,
    history: []
  },

  onLoad() {
    this.loadHistory();
  },

  // 加载搜索历史
  loadHistory() {
    const history = wx.getStorageSync(HISTORY_KEY) || [];
    this.setData({ history });
  },

  // 保存搜索历史
  saveHistory(keyword) {
    let history = wx.getStorageSync(HISTORY_KEY) || [];

    // 移除重复
    history = history.filter(item => item !== keyword);

    // 添加到开头
    history.unshift(keyword);

    // 限制数量
    if (history.length > MAX_HISTORY) {
      history = history.slice(0, MAX_HISTORY);
    }

    wx.setStorageSync(HISTORY_KEY, history);
    this.setData({ history });
  },

  // 清空历史
  clearHistory() {
    wx.removeStorageSync(HISTORY_KEY);
    this.setData({ history: [] });
  },

  // 输入
  onInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  // 清空输入
  onClear() {
    this.setData({
      keyword: '',
      hasSearched: false,
      products: []
    });
  },

  // 取消
  onCancel() {
    wx.navigateBack();
  },

  // 搜索
  onSearch() {
    const { keyword } = this.data;
    if (!keyword.trim()) return;

    this.saveHistory(keyword.trim());
    this.setData({
      hasSearched: true,
      products: [],
      page: 1,
      hasMore: true
    });
    this.loadProducts();
  },

  // 点击历史
  onHistoryTap(e) {
    const keyword = e.currentTarget.dataset.keyword;
    this.setData({ keyword });
    this.onSearch();
  },

  // 加载商品
  async loadProducts(isLoadMore = false) {
    if (this.data.isLoading) return;
    if (isLoadMore && !this.data.hasMore) return;

    this.setData({ isLoading: true });

    const page = isLoadMore ? this.data.page + 1 : 1;

    const res = await api.searchProducts(this.data.keyword, page, this.data.pageSize);

    if (res.success) {
      const app = getApp();
      const isPremium = app.globalData.userInfo?.role === 'premium';

      const newProducts = res.data.list.map(item => ({
        ...item,
        displayPrice: util.formatPrice(isPremium ? item.price_member : item.price_original)
      }));

      const products = isLoadMore
        ? [...this.data.products, ...newProducts]
        : newProducts;

      this.setData({
        products,
        page,
        hasMore: newProducts.length >= this.data.pageSize,
        isLoading: false
      });
    } else {
      this.setData({ isLoading: false });
    }
  },

  // 加载更多
  onLoadMore() {
    this.loadProducts(true);
  },

  // 跳转详情
  goToDetail(e) {
    const productId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}`
    });
  }
});
