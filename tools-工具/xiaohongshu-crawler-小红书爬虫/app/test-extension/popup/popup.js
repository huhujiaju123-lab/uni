// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
  const crawlBtn = document.getElementById('crawlBtn');
  const crawlDetailBtn = document.getElementById('crawlDetailBtn');
  const downloadBtn = document.getElementById('downloadBtn');
  const toggleMonitorBtn = document.getElementById('toggleMonitorBtn');
  const statusText = document.getElementById('statusText');
  const pageTypeText = document.getElementById('pageTypeText');
  const dataBody = document.getElementById('dataBody');
  const detailBody = document.getElementById('detailBody');
  const tabListBtn = document.getElementById('tabListBtn');
  const tabDetailBtn = document.getElementById('tabDetailBtn');
  const listDataSection = document.getElementById('listDataSection');
  const detailDataSection = document.getElementById('detailDataSection');

  // ========== 1. 初始化：加载已保存的数据并显示 ==========
  loadSavedData();
  loadDetailData();
  updateMonitorStatus();

  // ========== 2. 抓取列表页按钮点击事件 ==========
  crawlBtn.addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab.url.includes('xiaohongshu.com')) {
        alert('请先打开小红书页面（https://www.xiaohongshu.com）！');
        return;
      }

      // 显示加载提示
      crawlBtn.textContent = '抓取中，请稍候...';
      crawlBtn.disabled = true;

      // 向内容脚本发送消息，请求抓取数据
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'crawlData' });

      // 恢复按钮状态
      crawlBtn.textContent = '抓取列表页笔记';
      crawlBtn.disabled = false;

      if (response.status === 'success' && response.data.length > 0) {
        // 将新抓取的数据保存到本地存储（调用saveDataToStorage函数）
        await saveDataToStorage(response.data);
        // 重新加载并显示数据
        loadSavedData();
        alert(`✓ 成功抓取到 ${response.data.length} 条笔记数据！`);
      } else {
        alert('未抓取到任何笔记数据，请检查页面是否加载完成！');
      }
    } catch (e) {
      console.error('抓取数据失败：', e);
      crawlBtn.textContent = '抓取列表页笔记';
      crawlBtn.disabled = false;
      alert('抓取数据失败，请刷新小红书页面后重试！');
    }
  });

  // ========== 3. 抓取详情页按钮点击事件 ==========
  crawlDetailBtn.addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab.url.includes('xiaohongshu.com')) {
        alert('请先打开小红书页面（https://www.xiaohongshu.com）！');
        return;
      }

      // 显示加载提示
      crawlDetailBtn.textContent = '抓取中...';
      crawlDetailBtn.disabled = true;

      // 向内容脚本发送消息，请求抓取详情页数据
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'crawlDetail' });

      // 恢复按钮状态
      crawlDetailBtn.textContent = '抓取当前详情页';
      crawlDetailBtn.disabled = false;

      if (response.status === 'success') {
        // 保存详情数据
        await saveDetailData(response.data);
        // 重新加载并显示数据
        loadDetailData();
        // 自动切换到详情数据标签
        showDetailTab();
        alert(`✓ 成功抓取详情页数据！\n标题：${response.data.contentTitle}\n评论数：${response.data.commentsCount}`);
      } else {
        alert(response.message || '当前不在详情页或抓取失败！');
      }
    } catch (e) {
      console.error('抓取详情页失败：', e);
      crawlDetailBtn.textContent = '抓取当前详情页';
      crawlDetailBtn.disabled = false;
      alert('抓取详情页失败，请确保在笔记详情页并刷新后重试！');
    }
  });

  // ========== 4. 标签切换事件 ==========
  tabListBtn.addEventListener('click', () => {
    tabListBtn.classList.add('active');
    tabDetailBtn.classList.remove('active');
    listDataSection.style.display = 'block';
    detailDataSection.style.display = 'none';
  });

  tabDetailBtn.addEventListener('click', () => {
    tabDetailBtn.classList.add('active');
    tabListBtn.classList.remove('active');
    listDataSection.style.display = 'none';
    detailDataSection.style.display = 'block';
  });

  // ========== 1.5. 自动监控开关事件 ==========
  toggleMonitorBtn.addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab.url.includes('xiaohongshu.com')) {
        alert('请先打开小红书页面！');
        return;
      }

      // 获取当前状态
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'getMonitorStatus' });

      if (response.enabled) {
        // 当前是开启状态，点击后关闭
        await chrome.tabs.sendMessage(tab.id, { action: 'stopAutoMonitor' });
        updateMonitorStatus();
        alert('✓ 自动监控已停止');
      } else {
        // 当前是关闭状态，点击后开启
        await chrome.tabs.sendMessage(tab.id, { action: 'startAutoMonitor' });
        updateMonitorStatus();
        alert('✓ 自动监控已启动！\n\n现在你可以：\n1. 在列表页浏览笔记，自动抓取笔记信息\n2. 点击笔记进入详情页，自动抓取正文和评论\n\n所有数据会自动保存，你可以随时查看和导出。');
      }
    } catch (e) {
      console.error('切换监控状态失败：', e);
      alert('操作失败，请刷新页面后重试！');
    }
  });

  // 更新监控状态显示
  async function updateMonitorStatus() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab.url.includes('xiaohongshu.com')) {
        statusText.textContent = '自动监控：未启动';
        pageTypeText.textContent = '';
        toggleMonitorBtn.textContent = '🚀 启动自动监控';
        toggleMonitorBtn.className = 'monitor-btn';
        return;
      }

      const response = await chrome.tabs.sendMessage(tab.id, { action: 'getMonitorStatus' });

      if (response.enabled) {
        statusText.textContent = '自动监控：运行中';
        statusText.style.color = '#52c41a';

        if (response.pageType === 'detail') {
          pageTypeText.textContent = '📄 详情页';
        } else if (response.pageType === 'list') {
          pageTypeText.textContent = '📋 列表页';
        }

        toggleMonitorBtn.textContent = '⏸️ 停止监控';
        toggleMonitorBtn.className = 'monitor-btn active';
      } else {
        statusText.textContent = '自动监控：未启动';
        statusText.style.color = '#999';
        pageTypeText.textContent = '';
        toggleMonitorBtn.textContent = '🚀 启动自动监控';
        toggleMonitorBtn.className = 'monitor-btn';
      }
    } catch (e) {
      // 页面可能还没加载完成
      statusText.textContent = '自动监控：未启动';
      pageTypeText.textContent = '';
      toggleMonitorBtn.textContent = '🚀 启动自动监控';
      toggleMonitorBtn.className = 'monitor-btn';
    }
  }

  // 定时更新状态
  setInterval(updateMonitorStatus, 2000);

  // ========== 5. 下载按钮点击事件 ==========
  downloadBtn.addEventListener('click', async () => {
    const savedData = await getSavedData();
    const detailData = await getDetailData();

    if (savedData.length === 0 && detailData.length === 0) {
      alert('暂无数据可下载！');
      return;
    }

    // 创建包含两个sheet的数据
    let csvContent = '';

    // Sheet 1: 列表数据
    if (savedData.length > 0) {
      csvContent += '=== 列表页数据 ===\n';
      csvContent += convertToCSV(savedData);
      csvContent += '\n\n';
    }

    // Sheet 2: 详情数据
    if (detailData.length > 0) {
      csvContent += '=== 详情页数据 ===\n';
      csvContent += convertDetailToCSV(detailData);
    }

    // 创建下载链接并触发下载
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `小红书笔记数据_${new Date().getTime()}.csv`);
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  // ========== 工具函数：获取本地存储的列表数据 ==========
  async function getSavedData() {
    const result = await chrome.storage.local.get('noteData');
    return result.noteData || [];
  }

  // ========== 工具函数：获取详情数据 ==========
  async function getDetailData() {
    const result = await chrome.storage.local.get('detailData');
    return result.detailData || [];
  }

  // ========== 工具函数：保存列表数据到本地存储（追加+去重） ==========
  async function saveDataToStorage(newData) {
    const savedData = await getSavedData();
    // 合并数据并去重（根据链接判断）
    const combinedData = [...savedData, ...newData];
    const uniqueData = Array.from(new Map(combinedData.map(item => [item.link, item])).values());
    // 保存到本地存储
    await chrome.storage.local.set({ noteData: uniqueData });
  }

  // ========== 工具函数：保存详情数据（追加+去重） ==========
  async function saveDetailData(newData) {
    const savedData = await getDetailData();
    // 合并数据并去重（根据URL判断）
    const combinedData = [...savedData, newData];
    const uniqueData = Array.from(new Map(combinedData.map(item => [item.url, item])).values());
    // 保存到本地存储
    await chrome.storage.local.set({ detailData: uniqueData });
  }

  // ========== 工具函数：加载并显示列表数据 ==========
  async function loadSavedData() {
    const savedData = await getSavedData();
    // 清空表格
    dataBody.innerHTML = '';
    // 遍历数据，添加到表格
    savedData.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${item.author}</td>
        <td>${item.like}</td>
        <td>${item.title}</td>
        <td><a href="${item.link}" target="_blank">${item.link}</a></td>
      `;
      dataBody.appendChild(tr);
    });
  }

  // ========== 工具函数：加载并显示详情数据 ==========
  async function loadDetailData() {
    const detailData = await getDetailData();
    // 清空表格
    detailBody.innerHTML = '';
    // 遍历数据，添加到表格
    detailData.forEach((item, index) => {
      const tr = document.createElement('tr');
      const contentPreview = item.content.length > 50
        ? item.content.substring(0, 50) + '...'
        : item.content;

      tr.innerHTML = `
        <td>${item.contentTitle}</td>
        <td title="${item.content}">${contentPreview}</td>
        <td>${item.commentsCount}</td>
        <td>
          <button class="view-btn" data-index="${index}">查看评论</button>
        </td>
      `;
      detailBody.appendChild(tr);
    });

    // 为查看评论按钮添加事件监听
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = e.target.dataset.index;
        showComments(detailData[index]);
      });
    });
  }

  // ========== 工具函数：显示评论弹窗（优化换行） ==========
  function showComments(detailItem) {
    let commentsList = `📝 评论列表 (共 ${detailItem.comments.length} 条)\n`;
    commentsList += `笔记：${detailItem.contentTitle}\n`;
    commentsList += '━'.repeat(50) + '\n\n';

    if (detailItem.comments.length === 0) {
      commentsList += '暂无评论';
    } else {
      detailItem.comments.forEach(comment => {
        commentsList += `【${comment.index}】 ${comment.username}\n`;
        commentsList += `💬 ${comment.content}\n`;
        commentsList += `👍 ${comment.likes} 赞\n`;
        commentsList += '─'.repeat(40) + '\n\n';
      });
    }
    alert(commentsList);
  }

  // ========== 工具函数：切换到详情标签 ==========
  function showDetailTab() {
    tabDetailBtn.click();
  }

  // ========== 工具函数：将列表数据转换为CSV格式 ==========
  function convertToCSV(data) {
    // CSV表头
    const headers = ['作者', '点赞数', '标题', '链接'];
    // CSV内容（先写表头，再写数据）
    const csvRows = [
      headers.join(','), // 表头行
      ...data.map(item => {
        // 处理内容中的逗号（用双引号包裹，避免CSV格式错误）
        const author = `"${item.author.replace(/"/g, '""')}"`;
        const like = item.like;
        const title = `"${item.title.replace(/"/g, '""')}"`;
        const link = `"${item.link.replace(/"/g, '""')}"`;
        return [author, like, title, link].join(',');
      })
    ];
    return csvRows.join('\n');
  }

  // ========== 工具函数：将详情数据转换为CSV格式 ==========
  function convertDetailToCSV(data) {
    const headers = ['链接', '正文标题', '正文内容', '评论数', '评论详情'];
    const csvRows = [headers.join(',')];

    data.forEach(item => {
      // 处理评论列表
      let commentsText = '';
      item.comments.forEach(comment => {
        commentsText += `[${comment.username}] ${comment.content} (赞:${comment.likes}); `;
      });

      const url = `"${item.url.replace(/"/g, '""')}"`;
      const contentTitle = `"${item.contentTitle.replace(/"/g, '""')}"`;
      const content = `"${item.content.replace(/"/g, '""').replace(/\n/g, ' ')}"`;
      const commentsCount = item.commentsCount;
      const comments = `"${commentsText.replace(/"/g, '""')}"`;

      csvRows.push([url, contentTitle, content, commentsCount, comments].join(','));
    });

    return csvRows.join('\n');
  }
});