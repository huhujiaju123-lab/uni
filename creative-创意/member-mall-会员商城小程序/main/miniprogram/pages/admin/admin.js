// pages/admin/admin.js
const api = require('../../utils/api');

Page({
  data: {
    currentTab: 0,
    tabs: ['概览', '商品', '会员', '邀请码', '福利码'],
    // 统计数据
    statistics: {
      totalUsers: 0,
      premiumUsers: 0,
      normalUsers: 0,
      totalProducts: 0,
      activeInviteCodes: 0,
      welfareUsers: 0
    },
    // 商品列表
    products: [],
    // 会员列表
    users: [],
    userFilter: '',
    // 邀请码列表
    inviteCodes: [],
    // 福利码列表
    welfareCodes: [],
    // 加载状态
    isLoading: false,
    // 弹窗
    showProductModal: false,
    showInviteCodeModal: false,
    editingProduct: null,
    newProduct: {
      name: '',
      description: '',
      images: [],
      price_original: '',
      price_member: '',
      stock: '',
      status: 'on'
    },
    inviteCodeRemark: ''
  },

  onLoad() {
    this.loadStatistics();
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab });

    switch (tab) {
      case 0: this.loadStatistics(); break;
      case 1: this.loadProducts(); break;
      case 2: this.loadUsers(); break;
      case 3: this.loadInviteCodes(); break;
      case 4: this.loadWelfareCodes(); break;
    }
  },

  async loadStatistics() {
    this.setData({ isLoading: true });
    const res = await api.getStatistics();
    this.setData({ isLoading: false });
    if (res.success) {
      this.setData({ statistics: res.data });
    }
  },

  async loadProducts() {
    this.setData({ isLoading: true });
    const res = await api.getProductListAdmin();
    this.setData({ isLoading: false });
    if (res.success) {
      this.setData({ products: res.data.list });
    }
  },

  showAddProduct() {
    this.setData({
      showProductModal: true,
      editingProduct: null,
      newProduct: { name: '', description: '', images: [], price_original: '', price_member: '', stock: '', status: 'on' }
    });
  },

  showEditProduct(e) {
    const product = e.currentTarget.dataset.product;
    this.setData({
      showProductModal: true,
      editingProduct: product,
      newProduct: {
        name: product.name,
        description: product.description || '',
        images: product.images || [],
        price_original: (product.price_original / 100).toString(),
        price_member: (product.price_member / 100).toString(),
        stock: product.stock.toString(),
        status: product.status
      }
    });
  },

  closeProductModal() {
    this.setData({ showProductModal: false });
  },

  onProductInput(e) {
    const field = e.currentTarget.dataset.field;
    const key = 'newProduct.' + field;
    this.setData({ [key]: e.detail.value });
  },

  async chooseImage() {
    const res = await wx.chooseMedia({ count: 5, mediaType: ['image'], sizeType: ['compressed'] });
    if (res.tempFiles && res.tempFiles.length > 0) {
      wx.showLoading({ title: '上传中...' });
      const images = [...this.data.newProduct.images];
      for (const file of res.tempFiles) {
        try {
          const ts = new Date().getTime();
          const rand = Math.random().toString(36).substr(2, 9);
          const uploadRes = await wx.cloud.uploadFile({
            cloudPath: 'products/' + ts + '_' + rand + '.jpg',
            filePath: file.tempFilePath
          });
          images.push(uploadRes.fileID);
        } catch (err) {
          console.error('上传失败', err);
        }
      }
      wx.hideLoading();
      this.setData({ 'newProduct.images': images });
    }
  },

  removeImage(e) {
    const index = e.currentTarget.dataset.index;
    const images = [...this.data.newProduct.images];
    images.splice(index, 1);
    this.setData({ 'newProduct.images': images });
  },

  async saveProduct() {
    const { newProduct, editingProduct } = this.data;
    if (!newProduct.name) { wx.showToast({ title: '请输入商品名称', icon: 'none' }); return; }
    if (!newProduct.price_original || !newProduct.price_member) { wx.showToast({ title: '请输入价格', icon: 'none' }); return; }

    const productData = {
      name: newProduct.name,
      description: newProduct.description,
      images: newProduct.images,
      price_original: Math.round(parseFloat(newProduct.price_original) * 100),
      price_member: Math.round(parseFloat(newProduct.price_member) * 100),
      stock: parseInt(newProduct.stock) || 0,
      status: newProduct.status
    };

    wx.showLoading({ title: '保存中...' });
    let res;
    if (editingProduct) {
      res = await api.updateProduct(editingProduct._id, productData);
    } else {
      res = await api.addProduct(productData);
    }
    wx.hideLoading();

    if (res.success) {
      wx.showToast({ title: '保存成功', icon: 'success' });
      this.closeProductModal();
      this.loadProducts();
    } else {
      wx.showToast({ title: res.message || '保存失败', icon: 'none' });
    }
  },

  async deleteProduct(e) {
    const productId = e.currentTarget.dataset.id;
    const confirm = await wx.showModal({ title: '确认删除', content: '确定要删除这个商品吗？' });
    if (confirm.confirm) {
      wx.showLoading({ title: '删除中...' });
      const res = await api.deleteProduct(productId);
      wx.hideLoading();
      if (res.success) {
        wx.showToast({ title: '删除成功', icon: 'success' });
        this.loadProducts();
      }
    }
  },

  async loadUsers() {
    this.setData({ isLoading: true });
    const res = await api.getUserListAdmin(1, 50, this.data.userFilter);
    this.setData({ isLoading: false });
    if (res.success) {
      this.setData({ users: res.data.list });
    }
  },

  filterUsers(e) {
    const filter = e.currentTarget.dataset.filter;
    this.setData({ userFilter: filter });
    this.loadUsers();
  },

  copyCode(e) {
    const code = e.currentTarget.dataset.code;
    if (code) {
      wx.setClipboardData({ data: code, success: () => wx.showToast({ title: '已复制', icon: 'success' }) });
    }
  },

  async loadInviteCodes() {
    this.setData({ isLoading: true });
    const res = await api.getInviteCodeListAdmin();
    this.setData({ isLoading: false });
    if (res.success) {
      this.setData({ inviteCodes: res.data.list });
    }
  },

  showAddInviteCode() {
    this.setData({ showInviteCodeModal: true, inviteCodeRemark: '' });
  },

  closeInviteCodeModal() {
    this.setData({ showInviteCodeModal: false });
  },

  onRemarkInput(e) {
    this.setData({ inviteCodeRemark: e.detail.value });
  },

  async generateInviteCode() {
    wx.showLoading({ title: '生成中...' });
    const res = await api.generateOfficialInviteCode(this.data.inviteCodeRemark);
    wx.hideLoading();
    if (res.success) {
      wx.showToast({ title: '生成成功', icon: 'success' });
      this.closeInviteCodeModal();
      this.loadInviteCodes();
    } else {
      wx.showToast({ title: res.message || '生成失败', icon: 'none' });
    }
  },

  async toggleInviteCodeStatus(e) {
    const { id, status } = e.currentTarget.dataset;
    const newStatus = status === 'active' ? 'inactive' : 'active';
    wx.showLoading({ title: '更新中...' });
    const res = await api.updateInviteCodeStatus(id, newStatus);
    wx.hideLoading();
    if (res.success) { this.loadInviteCodes(); }
  },

  async deleteInviteCode(e) {
    const codeId = e.currentTarget.dataset.id;
    const confirm = await wx.showModal({ title: '确认删除', content: '确定要删除这个邀请码吗？' });
    if (confirm.confirm) {
      wx.showLoading({ title: '删除中...' });
      const res = await api.deleteInviteCodeAdmin(codeId);
      wx.hideLoading();
      if (res.success) {
        wx.showToast({ title: '删除成功', icon: 'success' });
        this.loadInviteCodes();
      }
    }
  },

  async loadWelfareCodes() {
    this.setData({ isLoading: true });
    const res = await api.getWelfareCodeListAdmin();
    this.setData({ isLoading: false });
    if (res.success) {
      this.setData({ welfareCodes: res.data.list });
    }
  }
});
