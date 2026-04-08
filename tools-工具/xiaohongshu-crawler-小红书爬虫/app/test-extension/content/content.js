// ========== 1. 自动滚动加载所有笔记 ==========
async function autoScrollToLoadAll() {
  return new Promise((resolve) => {
    let lastHeight = 0;
    let sameHeightCount = 0;
    const maxSameCount = 3; // 连续3次高度不变则停止

    const scrollInterval = setInterval(() => {
      // 滚动到页面底部
      window.scrollTo(0, document.body.scrollHeight);

      const currentHeight = document.body.scrollHeight;

      // 检查高度是否有变化
      if (currentHeight === lastHeight) {
        sameHeightCount++;
        if (sameHeightCount >= maxSameCount) {
          clearInterval(scrollInterval);
          // 滚动回顶部
          window.scrollTo(0, 0);
          resolve();
        }
      } else {
        sameHeightCount = 0;
        lastHeight = currentHeight;
      }
    }, 1000); // 每秒滚动一次
  });
}

// ========== 2. 抓取列表页笔记数据（兼容所有加载的笔记）==========
function getNoteDataFromDOM() {
  const noteData = [];

  // 步骤1：找到页面中所有独立的笔记卡片容器（核心，确保拿到所有笔记）
  const noteCards = document.querySelectorAll(
    // 复合选择器：匹配所有笔记卡片的特征
    'div:has(a.title):has(span.name):has(span.like-wrapper), ' +
    'div:has(a[href*="/explore/"]), ' +
    'div[class*="note"], div[class*="card"], div[class*="item"]'
  );

  // 去重卡片：保留最内层的单条笔记卡片（排除父级大容器）
  const uniqueCards = new Set();
  noteCards.forEach(card => {
    // 判断是否是最内层卡片（没有子卡片）
    const hasChildCard = card.querySelector('div:has(a.title):has(span.name)') ||
                          card.querySelector('div:has(a[href*="/explore/"])');
    if (!hasChildCard) {
      uniqueCards.add(card);
    } else {
      // 如果有子卡片，添加子卡片而非父卡片
      const childCards = card.querySelectorAll('div:has(a.title):has(span.name), div:has(a[href*="/explore/"])');
      childCards.forEach(child => uniqueCards.add(child));
    }
  });

  // 步骤2：遍历每个笔记卡片，抓取数据
  uniqueCards.forEach(card => {
    try {
      // 1. 提取作者名称（兼容多种DOM结构）
      let author = '未知作者';
      const authorElements = card.querySelectorAll('span.name, div.name, [class*="nickname"], [class*="user-name"]');
      for (const el of authorElements) {
        const text = el.textContent.trim();
        if (text && text.length > 0) {
          author = text;
          break;
        }
      }

      // 2. 提取标题（兼容多种DOM结构，兜底短文本）
      let title = '无标题';
      // 优先匹配标题标签
      const titleLink = card.querySelector('a.title');
      if (titleLink) {
        const titleSpan = titleLink.querySelector('span') || titleLink;
        title = titleSpan.textContent.trim();
      }
      // 兜底：抓取卡片内的短文本（排除按钮文本）
      if (title === '无标题') {
        const textElements = card.querySelectorAll('span, div, p');
        for (const el of textElements) {
          const text = el.textContent.trim();
          if (text.length > 0 && text.length < 100 && !text.includes('关注') && !text.includes('点赞')) {
            title = text;
            break;
          }
        }
      }

      // 3. 提取点赞数量（只保留数字，兼容k/m单位）
      let like = '0';
      const likeElements = card.querySelectorAll('span.like-wrapper, div[class*="like"], span.count, [class*="like-count"]');
      for (const el of likeElements) {
        const text = el.textContent.trim();
        if (text && /\d/.test(text)) {
          // 转换k/m为数字（如1.2k→1200，2m→2000000）
          like = text.replace(/(\d+)(\.\d+)?k/gi, (_, n, d) => (n * 1000) + (d ? d * 100 : 0))
                     .replace(/(\d+)(\.\d+)?m/gi, (_, n, d) => (n * 1000000) + (d ? d * 100000 : 0))
                     .replace(/[^\d]/g, '');
          break;
        }
      }

      // 4. 提取笔记链接（核心特征：/explore/ 或 /notes/）
      let link = '';
      // 优先匹配/explore/链接
      const exploreLink = card.querySelector('a[href*="/explore/"]');
      if (exploreLink) {
        const href = exploreLink.getAttribute('href');
        link = href.startsWith('/') ? `https://www.xiaohongshu.com${href}` : href;
      }
      // 备用：匹配/notes/链接
      if (!link) {
        const noteLink = card.querySelector('a[href*="/notes/"]');
        if (noteLink) {
          const href = noteLink.getAttribute('href');
          link = href.startsWith('/') ? `https://www.xiaohongshu.com${href}` : href;
        }
      }

      // 过滤无效数据：只保留有链接、标题和作者的笔记
      if (link && title !== '无标题' && author !== '未知作者') {
        noteData.push({ author, like, title, link });
      }
    } catch (e) {
      // 单个卡片失败不影响其他笔记
      console.error('处理单条笔记失败：', e);
      return;
    }
  });

  // 最终去重：根据链接去重（避免同一笔记多次抓取）
  const uniqueNoteData = Array.from(new Map(noteData.map(item => [item.link, item])).values());
  return uniqueNoteData;
}

// ========== 3. 抓取详情页数据（笔记正文标题、内容、评论）==========
function getNoteDetailData() {
  console.log('[详情页抓取] 开始抓取，当前URL:', window.location.href);

  try {
    // 判断是否在详情页
    const url = window.location.href;
    const isDetailPage = url.includes('/explore/') ||
                        url.includes('/discovery/item/') ||
                        url.includes('/note/') ||
                        url.includes('/notes/');

    if (!isDetailPage) {
      console.log('[详情页抓取] 不是详情页，URL不符合');
      return { error: 'not_detail_page', url };
    }

    console.log('[详情页抓取] 确认是详情页，开始提取数据...');

    // 1. 提取笔记正文标题 - 使用更智能的方式
    let contentTitle = '';

    // 尝试多种方式提取标题
    const titleStrategies = [
      // 策略1: 查找包含"标题"特征的元素
      () => {
        const candidates = document.querySelectorAll('h1, [class*="title"], [class*="Title"]');
        for (const el of candidates) {
          const text = el.textContent.trim();
          if (text && text.length > 3 && text.length < 200 && !text.includes('小红书')) {
            return text;
          }
        }
        return null;
      },
      // 策略2: 查找主内容区的第一个大文本
      () => {
        const mainContent = document.querySelector('[class*="note"], [class*="detail"], main, article');
        if (mainContent) {
          const headings = mainContent.querySelectorAll('h1, h2, div[class*="title"]');
          if (headings.length > 0) {
            return headings[0].textContent.trim();
          }
        }
        return null;
      },
      // 策略3: 从页面标题提取
      () => {
        const pageTitle = document.title;
        if (pageTitle && !pageTitle.includes('小红书')) {
          return pageTitle.split('-')[0].split('|')[0].trim();
        }
        return null;
      }
    ];

    for (const strategy of titleStrategies) {
      const result = strategy();
      if (result) {
        contentTitle = result;
        console.log('[详情页抓取] 标题提取成功:', contentTitle);
        break;
      }
    }

    // 2. 提取笔记正文内容
    let content = '';

    const contentStrategies = [
      // 策略1: 查找描述或内容区域
      () => {
        const selectors = [
          '[class*="desc"]',
          '[class*="content"]',
          '[class*="note-text"]',
          '[id*="detail-desc"]',
          '[class*="NoteContent"]'
        ];
        for (const sel of selectors) {
          const el = document.querySelector(sel);
          if (el) {
            const text = el.textContent.trim();
            if (text.length > 10) {
              return text;
            }
          }
        }
        return null;
      },
      // 策略2: 查找包含大量文本的div
      () => {
        const allDivs = document.querySelectorAll('div, p, section');
        let longestText = '';
        for (const div of allDivs) {
          const text = div.textContent.trim();
          // 排除导航、按钮等元素
          if (text.length > 50 &&
              text.length < 5000 &&
              !text.includes('关注') &&
              !text.includes('点赞') &&
              !text.includes('收藏') &&
              text.length > longestText.length) {
            longestText = text;
          }
        }
        return longestText || null;
      }
    ];

    for (const strategy of contentStrategies) {
      const result = strategy();
      if (result) {
        content = result;
        console.log('[详情页抓取] 内容提取成功，长度:', content.length);
        break;
      }
    }

    // 3. 提取评论列表
    const comments = [];
    console.log('[详情页抓取] 开始提取评论...');

    // 查找评论区域
    const commentContainerSelectors = [
      '[class*="comment"]',
      '[id*="comment"]',
      '[class*="Comment"]'
    ];

    let commentContainer = null;
    for (const sel of commentContainerSelectors) {
      const el = document.querySelector(sel);
      if (el && el.querySelectorAll('div').length > 3) {
        commentContainer = el;
        console.log('[详情页抓取] 找到评论容器:', sel);
        break;
      }
    }

    if (commentContainer) {
      // 查找评论项
      const commentItemSelectors = [
        '[class*="comment-item"]',
        '[class*="CommentItem"]',
        '[class*="item"]'
      ];

      let commentItems = [];
      for (const sel of commentItemSelectors) {
        const items = commentContainer.querySelectorAll(sel);
        if (items.length > 0) {
          commentItems = Array.from(items);
          console.log('[详情页抓取] 找到评论项:', items.length, '条');
          break;
        }
      }

      // 如果没找到特定的item类，就尝试找所有包含文本的div
      if (commentItems.length === 0) {
        const allDivs = commentContainer.querySelectorAll('div');
        commentItems = Array.from(allDivs).filter(div => {
          const text = div.textContent.trim();
          return text.length > 5 && text.length < 500;
        });
        console.log('[详情页抓取] 使用备用方案，找到', commentItems.length, '个可能的评论元素');
      }

      // 提取每条评论
      commentItems.forEach((commentEl, index) => {
        try {
          const allText = commentEl.textContent.trim();

          // 跳过太短或太长的内容
          if (allText.length < 2 || allText.length > 1000) {
            return;
          }

          // 提取评论用户名
          let username = '匿名用户';
          const userSelectors = [
            '[class*="username"]',
            '[class*="nickname"]',
            '[class*="name"]',
            '[class*="user"]',
            'span',
            'a'
          ];

          for (const sel of userSelectors) {
            const userEl = commentEl.querySelector(sel);
            if (userEl) {
              const name = userEl.textContent.trim();
              if (name && name.length > 0 && name.length < 50 && !name.includes('回复')) {
                username = name;
                break;
              }
            }
          }

          // 提取评论内容
          let commentText = allText;

          // 提取点赞数
          let commentLikes = '0';
          const likeMatch = allText.match(/(\d+)\s*赞|点赞\s*(\d+)|(\d+)\s*👍/);
          if (likeMatch) {
            commentLikes = likeMatch[1] || likeMatch[2] || likeMatch[3];
          }

          // 只添加有实际内容的评论
          if (commentText && commentText.length > 2) {
            // 避免重复添加
            const isDuplicate = comments.some(c => c.content === commentText);
            if (!isDuplicate) {
              comments.push({
                index: comments.length + 1,
                username,
                content: commentText,
                likes: commentLikes
              });
            }
          }
        } catch (e) {
          console.error('[详情页抓取] 提取单条评论失败:', e);
        }
      });
    }

    console.log('[详情页抓取] 评论提取完成，共', comments.length, '条');

    const result = {
      url: window.location.href,
      contentTitle: contentTitle || '未找到标题',
      content: content || '未找到内容',
      comments,
      commentsCount: comments.length
    };

    console.log('[详情页抓取] 抓取完成:', result);
    return result;

  } catch (e) {
    console.error('[详情页抓取] 发生错误:', e);
    return { error: 'exception', message: e.message, url: window.location.href };
  }
}

// ========== 4. 自动监控抓取系统 ==========
let autoMonitorEnabled = false; // 自动监控开关
let currentPageType = 'unknown'; // 当前页面类型
let lastProcessedNotes = new Set(); // 已处理的笔记（避免重复）
let lastUrl = '';

// 判断当前页面类型
function detectPageType() {
  const url = window.location.href;

  if (url.includes('/explore/') || url.includes('/discovery/item/') ||
      url.includes('/note/') || url.includes('/notes/')) {
    return 'detail'; // 详情页
  } else if (url.includes('xiaohongshu.com')) {
    return 'list'; // 列表页
  }
  return 'unknown';
}

// 自动抓取详情页
async function autoCapturDetailPage() {
  console.log('[自动抓取] 检测到详情页，开始抓取...');

  // 等待页面加载
  await new Promise(resolve => setTimeout(resolve, 2000));

  const detailData = getNoteDetailData();

  if (detailData && !detailData.error) {
    // 发送到后台保存
    chrome.runtime.sendMessage({
      action: 'saveDetailData',
      data: detailData
    }, (response) => {
      if (response && response.status === 'success') {
        console.log('[自动抓取] 详情页数据已保存:', detailData.contentTitle);
      }
    });
  }
}

// 自动抓取列表页
async function autoCaptureListPage() {
  console.log('[自动抓取] 检测到列表页，开始抓取...');

  const data = getNoteDataFromDOM();

  // 过滤出新笔记
  const newNotes = data.filter(note => !lastProcessedNotes.has(note.link));

  if (newNotes.length > 0) {
    // 记录已处理的笔记
    newNotes.forEach(note => lastProcessedNotes.add(note.link));

    // 发送到后台保存
    chrome.runtime.sendMessage({
      action: 'saveListData',
      data: newNotes
    }, (response) => {
      if (response && response.status === 'success') {
        console.log(`[自动抓取] 新增 ${newNotes.length} 条列表数据`);
      }
    });
  }
}

// URL变化监听器
let urlCheckInterval = null;

function startAutoMonitor() {
  console.log('[自动监控] 已启动');
  autoMonitorEnabled = true;
  lastUrl = window.location.href;
  currentPageType = detectPageType();

  // 立即执行一次抓取
  if (currentPageType === 'detail') {
    autoCapturDetailPage();
  } else if (currentPageType === 'list') {
    autoCaptureListPage();
  }

  // 定时检查URL变化
  urlCheckInterval = setInterval(() => {
    const newUrl = window.location.href;

    if (newUrl !== lastUrl) {
      console.log('[自动监控] URL变化:', newUrl);
      lastUrl = newUrl;
      const newPageType = detectPageType();

      if (newPageType !== currentPageType) {
        currentPageType = newPageType;

        // 页面类型变化，执行相应抓取
        if (currentPageType === 'detail') {
          autoCapturDetailPage();
        } else if (currentPageType === 'list') {
          autoCaptureListPage();
        }
      }
    }
  }, 1000); // 每秒检查一次

  // 监听列表页的DOM变化（新笔记加载）
  if (currentPageType === 'list') {
    const observer = new MutationObserver(() => {
      if (autoMonitorEnabled && currentPageType === 'list') {
        autoCaptureListPage();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }
}

function stopAutoMonitor() {
  console.log('[自动监控] 已停止');
  autoMonitorEnabled = false;

  if (urlCheckInterval) {
    clearInterval(urlCheckInterval);
    urlCheckInterval = null;
  }
}

// ========== 5. 消息监听器 ==========
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // 手动列表页抓取（带自动滚动）
  if (request.action === 'crawlData') {
    (async () => {
      try {
        // 先自动滚动加载所有笔记
        await autoScrollToLoadAll();
        // 再抓取数据
        const data = getNoteDataFromDOM();
        sendResponse({ status: 'success', data: data, count: data.length });
      } catch (e) {
        console.error('抓取数据失败：', e);
        sendResponse({ status: 'fail', data: [], count: 0 });
      }
    })();
    return true; // 保持消息通道开启（异步响应）
  }

  // 手动详情页抓取
  if (request.action === 'crawlDetail') {
    try {
      const detailData = getNoteDetailData();

      // 检查是否有错误
      if (detailData && detailData.error) {
        if (detailData.error === 'not_detail_page') {
          sendResponse({
            status: 'fail',
            message: '⚠️ 当前不在笔记详情页！\n\n请先打开一篇笔记的详情页（点击笔记进入完整内容页面），然后再点击"抓取当前详情页"按钮。\n\n详情页URL特征：\n- 包含 /explore/\n- 包含 /note/\n- 包含 /notes/'
          });
        } else {
          sendResponse({
            status: 'fail',
            message: `抓取失败: ${detailData.message || '未知错误'}`
          });
        }
      } else if (detailData) {
        sendResponse({ status: 'success', data: detailData });
      } else {
        sendResponse({ status: 'fail', message: '抓取失败，未返回数据' });
      }
    } catch (e) {
      console.error('[消息监听] 抓取详情页异常：', e);
      sendResponse({ status: 'fail', message: `发生错误: ${e.message}` });
    }
    return true;
  }

  // 启动自动监控
  if (request.action === 'startAutoMonitor') {
    startAutoMonitor();
    sendResponse({ status: 'success', message: '自动监控已启动' });
    return true;
  }

  // 停止自动监控
  if (request.action === 'stopAutoMonitor') {
    stopAutoMonitor();
    sendResponse({ status: 'success', message: '自动监控已停止' });
    return true;
  }

  // 获取监控状态
  if (request.action === 'getMonitorStatus') {
    sendResponse({
      status: 'success',
      enabled: autoMonitorEnabled,
      pageType: currentPageType
    });
    return true;
  }
});