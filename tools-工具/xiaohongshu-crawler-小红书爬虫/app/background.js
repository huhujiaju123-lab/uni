// ========== 后台脚本：处理数据保存 ==========

// 监听来自content script的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // 保存列表数据
  if (request.action === 'saveListData') {
    chrome.storage.local.get('noteData', (result) => {
      const savedData = result.noteData || [];
      const newData = request.data;

      // 合并并去重
      const combinedData = [...savedData, ...newData];
      const uniqueData = Array.from(
        new Map(combinedData.map(item => [item.link, item])).values()
      );

      // 保存
      chrome.storage.local.set({ noteData: uniqueData }, () => {
        console.log(`[后台] 保存了 ${newData.length} 条列表数据`);
        sendResponse({ status: 'success', count: newData.length });
      });
    });
    return true; // 异步响应
  }

  // 保存详情数据
  if (request.action === 'saveDetailData') {
    chrome.storage.local.get('detailData', (result) => {
      const savedData = result.detailData || [];
      const newData = request.data;

      // 合并并去重
      const combinedData = [...savedData, newData];
      const uniqueData = Array.from(
        new Map(combinedData.map(item => [item.url, item])).values()
      );

      // 保存
      chrome.storage.local.set({ detailData: uniqueData }, () => {
        console.log(`[后台] 保存了详情数据:`, newData.contentTitle);
        sendResponse({ status: 'success' });
      });
    });
    return true; // 异步响应
  }
});
