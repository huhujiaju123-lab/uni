// 小红书笔记采集器 - Content Script (列表页版本)

// 已采集的笔记 URL 集合（避免重复采集）
const collectedUrls = new Set();

// 初始化时加载已采集的 URL
async function loadCollectedUrls() {
  try {
    const result = await chrome.storage.local.get(['notes']);
    const notes = result.notes || [];
    notes.forEach(note => collectedUrls.add(note.url));
    console.log('✅ 已加载', collectedUrls.size, '条历史记录');
  } catch (error) {
    console.error('❌ 加载历史记录失败:', error);
  }
}

// 从笔记卡片提取信息
function extractNoteFromCard(card) {
  try {
    const noteInfo = {
      url: '',
      title: '',
      author: '',
      likes: '',
      timestamp: new Date().toISOString()
    };

    // 提取链接
    const linkElement = card.querySelector('a[href*="/explore/"]');
    if (linkElement) {
      const href = linkElement.getAttribute('href');
      noteInfo.url = href.startsWith('http')
        ? href
        : 'https://www.xiaohongshu.com' + href;
    }

    // 如果没有链接，跳过
    if (!noteInfo.url) {
      return null;
    }

    // 检查是否已经采集过
    if (collectedUrls.has(noteInfo.url)) {
      return null;
    }

    // 提取标题 - 尝试多种选择器
    const titleSelectors = [
      '.title',
      '[class*="title"]',
      '[class*="Title"]',
      'a[href*="/explore/"]',
      '.note-title',
      '[class*="note-text"]',
    ];

    for (const selector of titleSelectors) {
      const titleElement = card.querySelector(selector);
      if (titleElement) {
        const text = titleElement.textContent.trim();
        if (text && text.length > 0 && text.length < 200) {
          noteInfo.title = text;
          break;
        }
      }
    }

    // 如果没找到标题，尝试使用图片的 alt 属性
    if (!noteInfo.title) {
      const imgElement = card.querySelector('img[alt]');
      if (imgElement) {
        const alt = imgElement.getAttribute('alt').trim();
        if (alt && alt !== '图片') {
          noteInfo.title = alt;
        }
      }
    }

    // 提取作者 - 尝试多种选择器
    const authorSelectors = [
      '.author',
      '[class*="author"]',
      '[class*="nickname"]',
      '[class*="username"]',
      '[class*="name"]',
      '.user-name',
    ];

    for (const selector of authorSelectors) {
      const authorElement = card.querySelector(selector);
      if (authorElement) {
        const text = authorElement.textContent.trim();
        if (text && text.length > 0 && text.length < 50) {
          noteInfo.author = text;
          break;
        }
      }
    }

    // 提取点赞数 - 尝试多种选择器
    const likeSelectors = [
      '[class*="like"] span',
      '[class*="Like"] span',
      'span[class*="count"]',
      '.count',
      '[class*="interact"] span',
    ];

    for (const selector of likeSelectors) {
      const likeElements = card.querySelectorAll(selector);
      for (const likeElement of likeElements) {
        const text = likeElement.textContent.trim();
        // 匹配数字格式：123, 1.2w, 1.2k 等
        if (text && /^[\d\.]+[wWkK万千]?$/.test(text)) {
          noteInfo.likes = text;
          break;
        }
      }
      if (noteInfo.likes) break;
    }

    // 如果标题为空，使用后备方案
    if (!noteInfo.title) {
      noteInfo.title = '未提取到标题 - ' + noteInfo.url.split('/').pop();
    }

    console.log('📝 提取笔记:', {
      title: noteInfo.title.substring(0, 30),
      author: noteInfo.author || '未知',
      likes: noteInfo.likes || '0',
      url: noteInfo.url
    });

    return noteInfo;

  } catch (error) {
    console.error('❌ 提取笔记信息失败:', error);
    return null;
  }
}

// 保存笔记信息
async function saveNoteInfo(noteInfo) {
  if (!noteInfo || !noteInfo.url) {
    return;
  }

  try {
    // 从 Chrome storage 获取已保存的笔记列表
    const result = await chrome.storage.local.get(['notes']);
    let notes = result.notes || [];

    // 检查是否已经保存过这个 URL
    const existingIndex = notes.findIndex(note => note.url === noteInfo.url);

    if (existingIndex === -1) {
      // 新笔记，添加到列表
      notes.unshift(noteInfo);
      collectedUrls.add(noteInfo.url);
      console.log('✅ 保存新笔记:', noteInfo.title.substring(0, 30));
    } else {
      // 更新现有笔记
      notes[existingIndex] = noteInfo;
      console.log('🔄 更新笔记:', noteInfo.title.substring(0, 30));
    }

    // 保存到 storage
    await chrome.storage.local.set({ notes: notes });

  } catch (error) {
    console.error('❌ 保存笔记失败:', error);
  }
}

// 查找并采集页面上的所有笔记卡片
function collectNotesOnPage() {
  // 尝试多种可能的笔记卡片选择器
  const cardSelectors = [
    'section[class*="note"]',
    '[class*="note-item"]',
    '[class*="feed-item"]',
    'a[href*="/explore/"]',
    '.note-card',
    '[class*="NoteCard"]',
  ];

  let cards = [];

  // 尝试每种选择器
  for (const selector of cardSelectors) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      cards = Array.from(elements);
      console.log(`🔍 使用选择器 "${selector}" 找到 ${cards.length} 个元素`);
      break;
    }
  }

  // 如果没找到，尝试查找所有包含笔记链接的父元素
  if (cards.length === 0) {
    const links = document.querySelectorAll('a[href*="/explore/"]');
    cards = Array.from(links).map(link => {
      // 找到包含完整信息的父容器
      let parent = link.parentElement;
      let depth = 0;
      while (parent && depth < 5) {
        // 如果父元素足够大，可能包含完整信息
        if (parent.offsetHeight > 100) {
          return parent;
        }
        parent = parent.parentElement;
        depth++;
      }
      return link;
    });
    console.log(`🔍 通过链接查找到 ${cards.length} 个笔记容器`);
  }

  if (cards.length === 0) {
    console.log('⚠️ 未找到笔记卡片，可能需要等待页面加载');
    return;
  }

  let newCount = 0;
  cards.forEach((card, index) => {
    const noteInfo = extractNoteFromCard(card);
    if (noteInfo) {
      saveNoteInfo(noteInfo);
      newCount++;
    }
  });

  if (newCount > 0) {
    console.log(`✅ 本次采集到 ${newCount} 条新笔记`);
  }
}

// 调试：打印页面结构
function debugPageStructure() {
  console.log('=== 页面结构调试 ===');
  console.log('URL:', window.location.href);

  // 查找所有探索链接
  const exploreLinks = document.querySelectorAll('a[href*="/explore/"]');
  console.log('探索链接数量:', exploreLinks.length);

  if (exploreLinks.length > 0) {
    console.log('示例链接:', exploreLinks[0].href);
    console.log('链接的父元素类名:', exploreLinks[0].parentElement?.className);
  }

  // 查找可能的容器元素
  const possibleContainers = document.querySelectorAll('[class*="note"], [class*="feed"], [class*="card"]');
  console.log('可能的笔记容器数量:', possibleContainers.length);

  console.log('==================');
}

// 监听页面变化，自动采集新加载的笔记
let observerTimeout;
function setupPageObserver() {
  const observer = new MutationObserver((mutations) => {
    // 防抖：避免频繁触发
    clearTimeout(observerTimeout);
    observerTimeout = setTimeout(() => {
      console.log('🔄 检测到页面变化，重新采集...');
      collectNotesOnPage();
    }, 1000);
  });

  // 观察整个文档的变化
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  console.log('👀 页面监听器已启动，将自动采集新加载的笔记');
}

// 监听滚动事件，当滚动到底部时采集
let scrollTimeout;
function setupScrollListener() {
  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      const scrollHeight = document.documentElement.scrollHeight;
      const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
      const clientHeight = document.documentElement.clientHeight;

      // 滚动到底部 80% 时采集
      if (scrollTop + clientHeight >= scrollHeight * 0.8) {
        console.log('📜 滚动到底部，尝试采集新内容...');
        collectNotesOnPage();
      }
    }, 500);
  });

  console.log('📜 滚动监听器已启动');
}

// 监听来自 popup 的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'captureNote') {
    console.log('📌 收到手动采集请求');

    collectNotesOnPage();

    setTimeout(() => {
      chrome.storage.local.get(['notes'], (result) => {
        const notes = result.notes || [];
        sendResponse({
          success: true,
          count: notes.length,
          message: `已采集 ${notes.length} 条笔记`
        });
      });
    }, 1500);

    return true; // 保持消息通道开启
  }

  if (request.action === 'debugPage') {
    debugPageStructure();
    sendResponse({ success: true });
    return true;
  }
});

// 页面加载完成后初始化
async function init() {
  console.log('🚀 小红书笔记采集器已加载 (列表页模式)');
  console.log('📍 当前页面:', window.location.href);

  // 加载历史记录
  await loadCollectedUrls();

  // 等待页面加载
  setTimeout(() => {
    console.log('🔍 开始首次采集...');
    collectNotesOnPage();

    // 如果没找到笔记，打印调试信息
    setTimeout(() => {
      const links = document.querySelectorAll('a[href*="/explore/"]');
      if (links.length === 0) {
        console.log('⚠️ 未找到笔记，打印调试信息...');
        debugPageStructure();
      }
    }, 2000);
  }, 2000);

  // 启动监听器
  setTimeout(() => {
    setupPageObserver();
    setupScrollListener();
  }, 3000);
}

// 启动
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
