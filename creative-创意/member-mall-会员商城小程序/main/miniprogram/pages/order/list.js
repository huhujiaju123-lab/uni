// pages/order/list.js
const api = require('../../utils/api');
const util = require('../../utils/util');

Page({
  data: {
    currentStatus: '',
    orders: [],
    isLoading: false,
    isRefreshing: false,
    hasMore: true,
    page: 1,
    pageSize: 10
  },

  onLoad(options) {
    if (options.status) {
      this.setData({ currentStatus: options.status });
    }
    this.loadOrders();
  },

  // 切换状态
  onTabChange(e) {
    const status = e.currentTarget.dataset.status;
    if (status === this.data.currentStatus) return;

    this.setData({
      currentStatus: status,
      orders: [],
      page: 1,
      hasMore: true
    });
    this.loadOrders();
  },

  // 加载订单
  async loadOrders(isLoadMore = false) {
    if (this.data.isLoading) return;
    if (isLoadMore && !this.data.hasMore) return;

    this.setData({ isLoading: true });

    const page = isLoadMore ? this.data.page + 1 : 1;

    const res = await api.getOrders(this.data.currentStatus, page, this.data.pageSize);

    if (res.success) {
      const newOrders = res.data.list.map(order => this.formatOrder(order));

      const orders = isLoadMore
        ? [...this.data.orders, ...newOrders]
        : newOrders;

      this.setData({
        orders,
        page,
        hasMore: newOrders.length >= this.data.pageSize,
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

  // 格式化订单
  formatOrder(order) {
    const statusMap = {
      pending: '待付款',
      paid: '待发货',
      shipped: '待收货',
      completed: '已完成',
      cancelled: '已取消'
    };

    const totalQuantity = order.items.reduce((sum, item) => sum + item.quantity, 0);

    return {
      ...order,
      statusText: statusMap[order.status] || order.status,
      payAmountText: util.formatPrice(order.pay_amount),
      totalQuantity,
      items: order.items.map(item => ({
        ...item,
        priceText: util.formatPrice(item.price)
      }))
    };
  },

  // 下拉刷新
  onRefresh() {
    this.setData({
      isRefreshing: true,
      page: 1,
      hasMore: true
    });
    this.loadOrders();
  },

  // 加载更多
  onLoadMore() {
    this.loadOrders(true);
  },

  // 取消订单
  async onCancel(e) {
    const orderId = e.currentTarget.dataset.id;

    const confirmed = await util.showConfirm({
      title: '取消订单',
      content: '确定要取消此订单吗？'
    });

    if (!confirmed) return;

    util.showLoading('取消中...');

    const res = await api.cancelOrder(orderId);

    util.hideLoading();

    if (res.success) {
      util.showSuccess('取消成功');
      this.onRefresh();
    } else {
      util.showError(res.message || '取消失败');
    }
  },

  // 去付款
  onPay(e) {
    // TODO: 调起支付
    wx.showToast({
      title: '支付功能开发中',
      icon: 'none'
    });
  },

  // 确认收货
  async onConfirm(e) {
    const orderId = e.currentTarget.dataset.id;

    const confirmed = await util.showConfirm({
      title: '确认收货',
      content: '确定已收到商品？'
    });

    if (!confirmed) return;

    util.showLoading('处理中...');

    const res = await api.confirmOrder(orderId);

    util.hideLoading();

    if (res.success) {
      util.showSuccess('确认成功');
      this.onRefresh();
    } else {
      util.showError(res.message || '操作失败');
    }
  }
});
