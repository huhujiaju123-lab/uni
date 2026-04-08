// 小红书笔记采集器 - Popup Script

document.addEventListener('DOMContentLoaded', function() {
  // 获取页面元素
  const captureBtn = document.getElementById('captureBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  const exportBtn = document.getElementById('exportBtn');
  const clearBtn = document.getElementById('clearBtn');
  const notesList = document.getElementById('notesList');
  const totalNotesEl = document.getElementById('totalNotes');
  const todayNotesEl = document.getElementById('todayNotes');
  const statusMessage = document.getElementById('statusMessage');

  // 加载并显示笔记列表
  loadNotes();

  // 采集当前笔记
  captureBtn.addEventListener('click', async () => {
    try {
      captureBtn.disabled = true;
      captureBtn.textContent = '📌 采集中...';

      // 获取当前活动标签页
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab.url.includes('xiaohongshu.com')) {
        showStatus('请在小红书笔记页面使用此功能', 'error');
        return;
      }

      // 发送消息到 content script
      chrome.tabs.sendMessage(tab.id, { action: 'captureNote' }, (response) => {
        if (chrome.runtime.lastError) {
          showStatus('页面加载中，请稍后重试', 'error');
          console.error(chrome.runtime.lastError);
        } else if (response && response.success) {
          const message = response.message || `✅ 采集成功！共 ${response.count || 0} 条笔记`;
          showStatus(message, 'success');
          loadNotes();
        } else {
          showStatus('❌ 采集失败：' + (response?.error || '未知错误'), 'error');
        }
      });

    } catch (error) {
      showStatus('❌ 采集失败：' + error.message, 'error');
      console.error(error);
    } finally {
      setTimeout(() => {
        captureBtn.disabled = false;
        captureBtn.textContent = '📌 采集当前笔记';
      }, 2000);
    }
  });

  // 刷新列表
  refreshBtn.addEventListener('click', () => {
    loadNotes();
    showStatus('🔄 列表已刷新', 'success');
  });

  // 导出为 CSV
  exportBtn.addEventListener('click', async () => {
    try {
      const result = await chrome.storage.local.get(['notes']);
      const notes = result.notes || [];

      if (notes.length === 0) {
        showStatus('没有数据可以导出', 'error');
        return;
      }

      // 生成 CSV 内容
      const csvContent = generateCSV(notes);

      // 创建下载链接
      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      link.download = `小红书笔记采集_${timestamp}.csv`;
      link.href = url;
      link.click();

      URL.revokeObjectURL(url);
      showStatus('✅ 导出成功！', 'success');

    } catch (error) {
      showStatus('❌ 导出失败：' + error.message, 'error');
      console.error(error);
    }
  });

  // 清空数据
  clearBtn.addEventListener('click', () => {
    if (confirm('确定要清空所有采集的数据吗？此操作不可恢复！')) {
      chrome.storage.local.set({ notes: [] }, () => {
        loadNotes();
        showStatus('🗑️ 数据已清空', 'success');
      });
    }
  });

  // 加载笔记列表
  async function loadNotes() {
    try {
      const result = await chrome.storage.local.get(['notes']);
      const notes = result.notes || [];

      // 更新统计数据
      totalNotesEl.textContent = notes.length;

      // 计算今日新增
      const today = new Date().toDateString();
      const todayCount = notes.filter(note => {
        const noteDate = new Date(note.timestamp).toDateString();
        return noteDate === today;
      }).length;
      todayNotesEl.textContent = todayCount;

      // 渲染笔记列表
      renderNotes(notes);

    } catch (error) {
      console.error('加载笔记失败:', error);
      showStatus('加载数据失败', 'error');
    }
  }

  // 渲染笔记列表
  function renderNotes(notes) {
    if (notes.length === 0) {
      notesList.innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
          </svg>
          <p>还没有采集任何笔记<br>访问小红书笔记页面后点击"采集当前笔记"</p>
        </div>
      `;
      return;
    }

    let html = '';
    notes.forEach((note, index) => {
      const date = new Date(note.timestamp).toLocaleString('zh-CN');
      html += `
        <div class="note-item">
          <div class="note-title">${escapeHtml(note.title || '无标题')}</div>
          <div class="note-meta">
            <span class="note-author">👤 ${escapeHtml(note.author || '未知作者')}</span>
            <span class="note-likes">❤️ ${escapeHtml(note.likes || '0')}</span>
          </div>
          <a href="${note.url}" target="_blank" class="note-link" title="${note.url}">
            🔗 ${note.url}
          </a>
          <div style="font-size: 11px; color: #aaa; margin-top: 5px;">
            ⏰ ${date}
          </div>
        </div>
      `;
    });

    notesList.innerHTML = html;
  }

  // 生成 CSV 内容
  function generateCSV(notes) {
    // CSV 表头
    const headers = ['序号', '标题', '作者', '点赞数', '链接', '采集时间'];
    let csv = headers.join(',') + '\n';

    // CSV 数据行
    notes.forEach((note, index) => {
      const row = [
        index + 1,
        `"${escapeCSV(note.title || '无标题')}"`,
        `"${escapeCSV(note.author || '未知作者')}"`,
        `"${escapeCSV(note.likes || '0')}"`,
        `"${escapeCSV(note.url)}"`,
        `"${new Date(note.timestamp).toLocaleString('zh-CN')}"`
      ];
      csv += row.join(',') + '\n';
    });

    return csv;
  }

  // 转义 HTML
  function escapeHtml(text) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
  }

  // 转义 CSV
  function escapeCSV(text) {
    if (typeof text !== 'string') {
      text = String(text);
    }
    return text.replace(/"/g, '""');
  }

  // 显示状态消息
  function showStatus(message, type = 'success') {
    statusMessage.textContent = message;
    statusMessage.className = 'status-message status-' + type;
    statusMessage.style.display = 'block';

    setTimeout(() => {
      statusMessage.style.display = 'none';
    }, 3000);
  }
});
