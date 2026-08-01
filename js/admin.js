// ===== 钛星 · 管理后台脚本（v3：仪表盘 / 文章审核 / 最新要闻 / 爬虫 / AI 提取 / 数据同步） =====
(function () {
  'use strict';

  // ---------- 常量 ----------
  var BOARD_LABELS = {
    rocket: '可回收火箭', moon: '中美登月', semiconductor: '中国半导体',
    'china-tech': '中国科技AI', 'mega-projects': '中国大工程',
    'controlled-fusion': '可控核聚变', finance: '科技资本'
  };
  var STATUS_MAP = { pending: '待审核', online: '已上线', block: '已屏蔽' };
  var ARTICLE_PAGE_SIZE = 20;

  // ---------- 状态 ----------
  var articlePage = 1;
  var selectedNewsIds = new Set();
  var detailNewsId = null;   // 文章详情模态框中当前文章
  var newsEditingId = null;  // 最新要闻编辑 id（null = 新增）
  var crawlPollingTimer = null;
  var crawlPolledLines = 0;  // 已消费的实时日志行数
  var tabsLoaded = { dashboard: true };

  // ---------- 工具 ----------
  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function fmtDate(s) {
    if (!s) return '-';
    var d = new Date(s);
    if (isNaN(d.getTime())) return String(s).substring(0, 16);
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function fmtDay(s) {
    if (!s) return '-';
    return String(s).substring(0, 10);
  }

  async function api(url, opts) {
    var res = await fetch(url, opts);
    var data = {};
    try { data = await res.json(); } catch (e) { /* 非 JSON 响应 */ }
    if (!res.ok) throw new Error(data.detail || data.message || ('HTTP ' + res.status));
    return data;
  }

  function emptyHtml(msg) {
    return '<div class="empty"><div class="empty-icon">📭</div><div>' + escapeHtml(msg) + '</div></div>';
  }

  function openModal(id) { document.getElementById(id).classList.add('active'); }
  function closeModal(id) {
    document.getElementById(id).classList.remove('active');
    if (id === 'article-modal') detailNewsId = null;
    if (id === 'news-modal') newsEditingId = null;
  }
  window.closeModal = closeModal;

  // ---------- 模块导航 ----------
  function switchTab(tab) {
    document.querySelectorAll('.admin-tab').forEach(function (b) {
      b.classList.toggle('on', b.dataset.tab === tab);
    });
    document.querySelectorAll('.admin-panel').forEach(function (p) {
      p.hidden = p.id !== 'panel-' + tab;
    });
    if (!tabsLoaded[tab]) {
      tabsLoaded[tab] = true;
      if (tab === 'articles') loadArticles();
      if (tab === 'news') loadNews();
      if (tab === 'crawl') loadCrawlHistory();
      if (tab === 'ai') loadAiHistory();
    }
  }

  // ---------- 仪表盘 ----------
  async function loadDashboard() {
    try {
      var data = await api('/api/admin/stats');
      var a = data.articles || {};
      document.getElementById('stat-total').textContent = a.total || 0;
      document.getElementById('stat-new').textContent = a.pending || 0;
      document.getElementById('stat-online').textContent = a.online || 0;
      document.getElementById('stat-news').textContent = data.latest_news_total || 0;
      renderBoardStatus(data.boards || []);
      renderRecentCrawl(data.recent_crawl_logs || []);
      renderRecentAi(data.recent_ai_logs || []);
    } catch (e) {
      document.getElementById('board-status-content').innerHTML = emptyHtml('加载失败：' + e.message);
    }
  }
  window.loadDashboard = loadDashboard;

  function renderBoardStatus(boards) {
    var el = document.getElementById('board-status-content');
    if (!boards.length) { el.innerHTML = emptyHtml('暂无版块状态数据'); return; }
    var html = '<table><thead><tr><th>版块</th><th>状态信息</th><th>新增数</th><th>数据源</th><th>错误源</th><th>最近抓取</th></tr></thead><tbody>';
    boards.forEach(function (b) {
      html += '<tr>' +
        '<td>' + escapeHtml(BOARD_LABELS[b.board_id] || b.board_id) + '</td>' +
        '<td class="title-cell" title="' + escapeHtml(b.last_message || '') + '">' + escapeHtml(b.last_message || '-') + '</td>' +
        '<td>' + escapeHtml(b.new_items_count || 0) + '</td>' +
        '<td>' + escapeHtml(b.total_sources || 0) + '</td>' +
        '<td>' + escapeHtml(b.error_sources || 0) + '</td>' +
        '<td class="date-cell">' + fmtDate(b.last_crawled_at) + '</td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  function renderRecentCrawl(list) {
    var el = document.getElementById('recent-crawl-content');
    if (!list.length) { el.innerHTML = emptyHtml('暂无爬取记录'); return; }
    var html = '<table><thead><tr><th>时间</th><th>版块</th><th>状态</th><th>信息</th></tr></thead><tbody>';
    list.forEach(function (r) {
      var cls = r.status === 'success' ? 'tag tag-success' : r.status === 'failed' ? 'tag tag-failed' : 'tag tag-idle';
      html += '<tr>' +
        '<td class="date-cell">' + fmtDate(r.created_at) + '</td>' +
        '<td>' + escapeHtml(BOARD_LABELS[r.board_id] || r.board_id) + '</td>' +
        '<td><span class="' + cls + '">' + escapeHtml(r.status || '-') + '</span></td>' +
        '<td class="title-cell" title="' + escapeHtml(r.error_message || r.message || '') + '">' + escapeHtml(r.error_message || r.message || '-') + '</td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  function renderRecentAi(list) {
    var el = document.getElementById('recent-ai-content');
    if (!list.length) { el.innerHTML = emptyHtml('暂无 AI 提取记录（表未创建或未执行过）'); return; }
    var html = '<table><thead><tr><th>时间</th><th>分类</th><th>入库/失败</th><th>状态</th></tr></thead><tbody>';
    list.forEach(function (r) {
      var cls = r.status === 'success' ? 'tag tag-success' : 'tag tag-failed';
      html += '<tr>' +
        '<td class="date-cell">' + fmtDate(r.created_at) + '</td>' +
        '<td>' + escapeHtml(r.category || '全部') + '</td>' +
        '<td>' + escapeHtml(r.inserted || 0) + ' / ' + escapeHtml(r.failed || 0) + '</td>' +
        '<td><span class="' + cls + '">' + escapeHtml(r.status || '-') + '</span></td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  // ---------- 文章审核 ----------
  function articleQueryParams() {
    var params = new URLSearchParams();
    var kw = document.getElementById('kw-search').value.trim();
    var cat = document.getElementById('filter-category').value;
    var st = document.getElementById('filter-status').value;
    if (kw) params.set('keyword', kw);
    if (cat) params.set('category', cat);
    if (st) params.set('status', st);
    params.set('sort_by', document.getElementById('sort-by').value);
    params.set('sort_order', document.getElementById('sort-order').value);
    params.set('page', articlePage);
    params.set('page_size', ARTICLE_PAGE_SIZE);
    return params.toString();
  }

  async function loadArticles() {
    var content = document.getElementById('articles-content');
    content.style.opacity = '0.3';
    try {
      var data = await api('/api/admin/articles?' + articleQueryParams());
      var stats = data.stats || {};
      document.getElementById('stat-total').textContent = stats.total || 0;
      document.getElementById('stat-new').textContent = stats.pending || 0;
      document.getElementById('stat-online').textContent = stats.online || 0;
      renderArticleTable(data.items || []);
      renderPagination(data.total || 0, data.page || 1, data.page_size || ARTICLE_PAGE_SIZE);
    } catch (e) {
      content.innerHTML = emptyHtml('加载失败：' + e.message);
    } finally {
      content.style.opacity = '1';
    }
  }
  window.loadArticles = loadArticles;

  function renderArticleTable(items) {
    var content = document.getElementById('articles-content');
    if (!items.length) { content.innerHTML = emptyHtml('暂无数据'); return; }
    var html = '<table><thead><tr>' +
      '<th class="check-col"><input type="checkbox" class="check-all" id="check-all"></th>' +
      '<th>标题</th><th>分类</th><th>来源</th><th>日期</th><th>状态</th><th>操作</th>' +
      '</tr></thead><tbody>';
    items.forEach(function (a) {
      var statusClass = 'status-' + (a.status || 'pending');
      var statusText = STATUS_MAP[a.status] || '待审核';
      var pubDate = fmtDay(a.publish_time || a.date);
      html += '<tr>' +
        '<td class="check-col"><input type="checkbox" class="row-check" data-id="' + escapeHtml(a.news_id) + '"></td>' +
        '<td class="title-cell" title="' + escapeHtml(a.title) + '">' + escapeHtml(a.title) + '</td>' +
        '<td>' + escapeHtml(a.category || '-') + '</td>' +
        '<td>' + escapeHtml(a.source_name || '-') + '</td>' +
        '<td class="date-cell">' + pubDate + '</td>' +
        '<td class="' + statusClass + '">' + statusText + '</td>' +
        '<td class="actions">' +
        '<button data-act="detail" data-id="' + escapeHtml(a.news_id) + '">详情</button>' +
        (a.status !== 'online' ? '<button data-act="set-status" data-status="online" data-id="' + escapeHtml(a.news_id) + '">发布</button>' : '') +
        (a.status === 'online' ? '<button data-act="set-status" data-status="block" data-id="' + escapeHtml(a.news_id) + '">屏蔽</button>' : '') +
        '<button class="danger" data-act="delete" data-id="' + escapeHtml(a.news_id) + '">删除</button>' +
        '</td></tr>';
    });
    html += '</tbody></table>';
    content.innerHTML = html;
  }

  function renderPagination(total, page, pageSize) {
    var el = document.getElementById('pagination');
    var pages = Math.max(1, Math.ceil(total / pageSize));
    var html = '<span class="page-info">共 ' + total + ' 条 · 第 ' + page + ' / ' + pages + ' 页</span>' +
      '<button class="page-btn" data-page="' + (page - 1) + '"' + (page <= 1 ? ' disabled' : '') + '>‹ 上一页</button>' +
      '<button class="page-btn" data-page="' + (page + 1) + '"' + (page >= pages ? ' disabled' : '') + '>下一页 ›</button>';
    el.innerHTML = html;
  }

  function updateBatchBar() {
    var n = selectedNewsIds.size;
    document.getElementById('batch-count').textContent = '已选 ' + n + ' 项';
    document.getElementById('batch-bar').hidden = n === 0;
  }

  function clearSelection() {
    selectedNewsIds.clear();
    document.querySelectorAll('.row-check').forEach(function (c) { c.checked = false; });
    var all = document.getElementById('check-all');
    if (all) all.checked = false;
    updateBatchBar();
  }
  window.clearSelection = clearSelection;

  async function batchStatus(status) {
    var ids = Array.from(selectedNewsIds);
    if (!ids.length) return;
    if (!confirm('确定将选中的 ' + ids.length + ' 篇文章设为「' + (STATUS_MAP[status] || status) + '」吗？')) return;
    try {
      var data = await api('/api/admin/articles/batch-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ news_ids: ids, status: status })
      });
      alert('已更新 ' + data.updated + ' / ' + data.total + ' 条');
      clearSelection();
      loadArticles();
    } catch (e) {
      alert('批量操作失败：' + e.message);
    }
  }
  window.batchStatus = batchStatus;

  async function updateArticleStatus(newsId, status) {
    try {
      await api('/api/admin/articles/' + encodeURIComponent(newsId) + '/status?status=' + status, { method: 'POST' });
      loadArticles();
    } catch (e) {
      alert('操作失败：' + e.message);
    }
  }

  async function deleteArticle(id) {
    if (!confirm('确定要删除这篇文章吗？')) return;
    try {
      await api('/api/admin/articles/' + encodeURIComponent(id), { method: 'DELETE' });
      clearSelection();
      loadArticles();
      loadDashboard();
    } catch (e) {
      alert('删除失败：' + e.message);
    }
  }

  // 文章详情
  async function openArticleDetail(newsId) {
    try {
      var data = await api('/api/admin/articles/' + encodeURIComponent(newsId));
      var a = data.item || {};
      detailNewsId = newsId;
      document.getElementById('det-title').textContent = a.title || '-';
      document.getElementById('det-news-id').textContent = a.news_id || '-';
      document.getElementById('det-source').textContent = a.source_name || a.source || '-';
      document.getElementById('det-category').textContent = a.category || '-';
      document.getElementById('det-status').textContent = STATUS_MAP[a.status] || a.status || '-';
      document.getElementById('det-publish').textContent = fmtDate(a.publish_time);
      document.getElementById('det-crawl').textContent = fmtDate(a.crawl_time);
      var url = a.source_url || a.url || '';
      var urlEl = document.getElementById('det-url');
      urlEl.href = url || '#';
      urlEl.textContent = url || '-';
      document.getElementById('det-summary').textContent = a.summary || '-';
      document.getElementById('det-content').textContent = a.raw_content || a.content || '（无正文）';
      openModal('article-modal');
    } catch (e) {
      alert('加载详情失败：' + e.message);
    }
  }

  async function detailStatus(status) {
    if (!detailNewsId) return;
    try {
      await api('/api/admin/articles/' + encodeURIComponent(detailNewsId) + '/status?status=' + status, { method: 'POST' });
      closeModal('article-modal');
      loadArticles();
    } catch (e) {
      alert('操作失败：' + e.message);
    }
  }
  window.detailStatus = detailStatus;

  // ---------- 最新要闻管理 ----------
  async function loadNews() {
    var el = document.getElementById('news-content');
    try {
      var data = await api('/api/admin/latest-news');
      renderNewsTable(data.items || []);
    } catch (e) {
      el.innerHTML = emptyHtml('加载失败：' + e.message);
    }
  }
  window.loadNews = loadNews;

  function renderNewsTable(items) {
    var el = document.getElementById('news-content');
    window.__newsItems = items;   // 供编辑/上下线操作回查本条数据
    if (!items.length) { el.innerHTML = emptyHtml('暂无最新要闻'); return; }
    var html = '<table><thead><tr><th>ID</th><th>标题</th><th>版块</th><th>日期</th><th>排序</th><th>状态</th><th>操作</th></tr></thead><tbody>';
    items.forEach(function (n) {
      var active = !!n.is_active;
      html += '<tr>' +
        '<td>' + escapeHtml(n.id) + '</td>' +
        '<td class="title-cell" title="' + escapeHtml(n.title) + '">' + escapeHtml(n.title) + '</td>' +
        '<td>' + escapeHtml(n.board_label || n.board || '-') + '</td>' +
        '<td class="date-cell">' + fmtDay(n.publish_date) + '</td>' +
        '<td>' + escapeHtml(n.sort_order || 0) + '</td>' +
        '<td class="' + (active ? 'status-online' : 'status-block') + '">' + (active ? '已上线' : '已下线') + '</td>' +
        '<td class="actions">' +
        '<button data-act="edit" data-id="' + escapeHtml(n.id) + '">编辑</button>' +
        '<button data-act="toggle" data-id="' + escapeHtml(n.id) + '">' + (active ? '下线' : '上线') + '</button>' +
        '<button class="danger" data-act="del" data-id="' + escapeHtml(n.id) + '">删除</button>' +
        '</td></tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  function openNewsModal(item) {
    newsEditingId = item ? item.id : null;
    document.getElementById('news-modal-title').textContent = item ? '编辑要闻 #' + item.id : '新增要闻';
    document.getElementById('news-title').value = item ? (item.title || '') : '';
    document.getElementById('news-summary').value = item ? (item.summary || '') : '';
    document.getElementById('news-link').value = item ? (item.link || '') : '';
    document.getElementById('news-source').value = item ? (item.source || '') : '';
    document.getElementById('news-board').value = item ? (item.board || '') : '';
    document.getElementById('news-board-label').value = item ? (item.board_label || '') : '';
    document.getElementById('news-publish-date').value = item ? fmtDay(item.publish_date) : '';
    document.getElementById('news-sort-order').value = item ? (item.sort_order || 0) : 0;
    document.getElementById('news-active').checked = item ? !!item.is_active : true;
    openModal('news-modal');
  }
  window.openNewsModal = openNewsModal;

  async function saveNews() {
    var payload = {
      title: document.getElementById('news-title').value.trim(),
      summary: document.getElementById('news-summary').value.trim(),
      link: document.getElementById('news-link').value.trim(),
      source: document.getElementById('news-source').value.trim(),
      board: document.getElementById('news-board').value,
      board_label: document.getElementById('news-board-label').value.trim(),
      publish_date: document.getElementById('news-publish-date').value || null,
      sort_order: parseInt(document.getElementById('news-sort-order').value, 10) || 0,
      is_active: document.getElementById('news-active').checked
    };
    if (!payload.title) { alert('标题不能为空'); return; }
    try {
      if (newsEditingId) {
        await api('/api/admin/latest-news/' + newsEditingId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await api('/api/admin/latest-news', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      closeModal('news-modal');
      loadNews();
      loadDashboard();
    } catch (e) {
      alert('保存失败：' + e.message);
    }
  }
  window.saveNews = saveNews;

  async function toggleNewsActive(id, active) {
    try {
      await api('/api/admin/latest-news/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !active })
      });
      loadNews();
    } catch (e) {
      alert('操作失败：' + e.message);
    }
  }

  async function deleteNews(id) {
    if (!confirm('确定删除这条要闻吗？')) return;
    try {
      await api('/api/admin/latest-news/' + id, { method: 'DELETE' });
      loadNews();
      loadDashboard();
    } catch (e) {
      alert('删除失败：' + e.message);
    }
  }

  // ---------- 爬虫控制台 ----------
  function addLog(containerId, message, type) {
    type = type || 'info';
    var container = document.getElementById(containerId);
    var time = new Date().toLocaleTimeString();
    var line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = '<span class="log-time">[' + time + ']</span> <span class="log-' + type + '">' + escapeHtml(message) + '</span>';
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  }

  function clearLogs() {
    document.getElementById('log-container').innerHTML = '';
    crawlPolledLines = 0;
    addLog('log-container', '日志已清空', 'info');
  }
  window.clearLogs = clearLogs;

  function updateCrawlStatus(status) {
    var el = document.getElementById('crawl-status');
    el.className = 'crawl-status status-' + status;
    var labels = { idle: '空闲', running: '运行中', success: '成功', failed: '失败' };
    el.textContent = labels[status] || status;
  }

  async function startCrawl() {
    var boardId = document.getElementById('crawl-board').value;
    if (!boardId) { alert('请选择版块'); return; }
    updateCrawlStatus('running');
    addLog('log-container', '开始抓取：' + boardId, 'info');
    try {
      await api('/api/crawl/' + boardId + '/start', { method: 'POST' });
      addLog('log-container', '爬虫已启动', 'success');
      if (crawlPollingTimer) clearInterval(crawlPollingTimer);
      crawlPolledLines = 0;
      crawlPollingTimer = setInterval(function () { pollCrawlLogs(boardId); }, 1000);
    } catch (e) {
      addLog('log-container', '启动失败：' + e.message, 'error');
      updateCrawlStatus('failed');
    }
  }
  window.startCrawl = startCrawl;

  async function startCrawlAll() {
    updateCrawlStatus('running');
    addLog('log-container', '开始抓取全部版块...', 'info');
    var boards = ['rocket', 'moon', 'semiconductor', 'china-tech', 'mega-projects', 'controlled-fusion', 'finance'];
    for (var i = 0; i < boards.length; i++) {
      var boardId = boards[i];
      try {
        await api('/api/crawl/' + boardId + '/start', { method: 'POST' });
        addLog('log-container', '[' + boardId + '] 爬虫已启动', 'info');
        await new Promise(function (r) { setTimeout(r, 500); });
      } catch (e) {
        addLog('log-container', '[' + boardId + '] 启动失败：' + e.message, 'error');
      }
    }
    addLog('log-container', '全部爬虫已启动，等待完成...', 'info');
    if (crawlPollingTimer) clearInterval(crawlPollingTimer);
    crawlPolledLines = 0;
    crawlPollingTimer = setInterval(function () { pollCrawlLogs(boards[boards.length - 1]); }, 2000);
  }
  window.startCrawlAll = startCrawlAll;

  async function pollCrawlLogs(boardId) {
    try {
      var data = await api('/api/crawl/' + boardId + '/logs');
      if (data.status === 'idle') {
        if (crawlPollingTimer) { clearInterval(crawlPollingTimer); crawlPollingTimer = null; }
        return;
      }
      var lines = data.lines || [];
      for (var i = crawlPolledLines; i < lines.length; i++) {
        var line = lines[i];
        var type = line.indexOf('错误') !== -1 ? 'error' : (line.indexOf('完成') !== -1 || line.indexOf('done') !== -1) ? 'success' : 'info';
        addLog('log-container', line, type);
      }
      crawlPolledLines = lines.length;
      updateCrawlStatus(data.status);
      if (data.status === 'success' || data.status === 'failed') {
        if (crawlPollingTimer) { clearInterval(crawlPollingTimer); crawlPollingTimer = null; }
        addLog('log-container', '抓取' + (data.status === 'success' ? '成功' : '失败'), data.status);
        loadArticles();
        loadDashboard();
      }
    } catch (e) {
      console.error('Polling error:', e);
      if (crawlPollingTimer) { clearInterval(crawlPollingTimer); crawlPollingTimer = null; }
    }
  }

  async function loadCrawlHistory() {
    var el = document.getElementById('crawl-history-content');
    try {
      var data = await api('/api/admin/crawl-logs?limit=50');
      var list = data.items || [];
      if (!list.length) { el.innerHTML = emptyHtml('暂无爬虫历史日志'); return; }
      var html = '<table><thead><tr><th>时间</th><th>版块</th><th>状态</th><th>新增数</th><th>信息</th></tr></thead><tbody>';
      list.forEach(function (r) {
        var cls = r.status === 'success' ? 'tag tag-success' : r.status === 'failed' ? 'tag tag-failed' : 'tag tag-idle';
        html += '<tr>' +
          '<td class="date-cell">' + fmtDate(r.created_at) + '</td>' +
          '<td>' + escapeHtml(BOARD_LABELS[r.board_id] || r.board_id) + '</td>' +
          '<td><span class="' + cls + '">' + escapeHtml(r.status || '-') + '</span></td>' +
          '<td>' + escapeHtml(r.items_count || 0) + '</td>' +
          '<td class="title-cell" title="' + escapeHtml(r.error_message || r.message || '') + '">' + escapeHtml(r.error_message || r.message || '-') + '</td>' +
          '</tr>';
      });
      html += '</tbody></table>';
      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = emptyHtml('加载失败：' + e.message);
    }
  }
  window.loadCrawlHistory = loadCrawlHistory;

  // ---------- AI 提取控制台 ----------
  function addAiLog(msg, type) {
    addLog('ai-log-container', msg, type);
  }

  async function startAiExtract() {
    var category = document.getElementById('ai-category').value;
    var statusText = document.getElementById('ai-status-text');
    var statusEl = document.getElementById('ai-status');
    statusEl.className = 'status-indicator status-running';
    statusText.textContent = '提取中...';
    addAiLog('开始 AI 提取 [' + (category || '全部') + ']...', 'info');
    try {
      var q = category ? ('?category=' + encodeURIComponent(category) + '&limit=10') : '?limit=10';
      var result = await api('/api/ai/extract' + q, { method: 'POST' });
      if (result.error || result.status === 'error') {
        addAiLog('错误: ' + (result.message || result.error), 'error');
        statusEl.className = 'status-indicator status-failed';
        statusText.textContent = '失败';
        return;
      }
      if (result.processed !== undefined && !result.total) {
        addAiLog(result.message || '没有待处理的文章', 'info');
        statusEl.className = 'status-indicator status-success';
        statusText.textContent = '完成';
        loadAiStats();
        loadAiHistory();
        return;
      }
      addAiLog('处理 ' + result.total + ' 条，提取 ' + result.extracted + ' 条', 'success');
      addAiLog('自动入库 ' + result.auto_inserted + ' 条，待审核 ' + result.pending_review + ' 条', 'info');
      (result.results || []).forEach(function (r) {
        var icon = r.auto_inserted ? '✓' : '○';
        var type = r.auto_inserted ? 'success' : 'warn';
        var conf = typeof r.confidence === 'number' ? r.confidence.toFixed(2) : '-';
        addAiLog(icon + ' [' + conf + '] ' + (r.title || '') , type);
      });
      statusEl.className = 'status-indicator status-success';
      statusText.textContent = '完成';
      loadArticles();
      loadAiStats();
      loadAiHistory();
    } catch (err) {
      addAiLog('请求失败: ' + err.message, 'error');
      statusEl.className = 'status-indicator status-failed';
      statusText.textContent = '失败';
    }
  }
  window.startAiExtract = startAiExtract;

  async function loadAiStats() {
    var category = document.getElementById('ai-category').value;
    try {
      var q = category ? ('?category=' + encodeURIComponent(category)) : '';
      var data = await api('/api/ai/stats' + q);
      document.getElementById('ai-stats').textContent =
        '待处理: ' + (data.pending_articles || 0) + ' 条 | 时间线: ' + (data.timeline_entries || 0) + ' 条 | 最新要闻: ' + (data.latest_news_total || 0) + ' 条';
    } catch (err) {
      document.getElementById('ai-stats').textContent = '获取统计失败';
    }
  }
  window.loadAiStats = loadAiStats;

  async function loadAiHistory() {
    var el = document.getElementById('ai-history-content');
    try {
      var data = await api('/api/admin/ai/logs?limit=50');
      var list = data.items || [];
      if (!list.length) { el.innerHTML = emptyHtml('暂无提取历史（ai_extract_logs 表未创建或尚未执行过提取）'); return; }
      var html = '<table><thead><tr><th>时间</th><th>分类</th><th>条数</th><th>处理</th><th>入库</th><th>失败</th><th>状态</th><th>信息</th></tr></thead><tbody>';
      list.forEach(function (r) {
        var cls = r.status === 'success' ? 'tag tag-success' : 'tag tag-failed';
        html += '<tr>' +
          '<td class="date-cell">' + fmtDate(r.created_at) + '</td>' +
          '<td>' + escapeHtml(r.category || '全部') + '</td>' +
          '<td>' + escapeHtml(r.limit || 0) + '</td>' +
          '<td>' + escapeHtml(r.total || 0) + '</td>' +
          '<td>' + escapeHtml(r.inserted || 0) + '</td>' +
          '<td>' + escapeHtml(r.failed || 0) + '</td>' +
          '<td><span class="' + cls + '">' + escapeHtml(r.status || '-') + '</span></td>' +
          '<td class="title-cell" title="' + escapeHtml(r.message || '') + '">' + escapeHtml(r.message || '-') + '</td>' +
          '</tr>';
      });
      html += '</tbody></table>';
      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = emptyHtml('加载失败：' + e.message);
    }
  }
  window.loadAiHistory = loadAiHistory;

  // ---------- 数据同步 ----------
  async function syncBoard(boardId) {
    addLog('sync-log-container', '开始同步：' + (BOARD_LABELS[boardId] || boardId), 'info');
    try {
      var data = await api('/api/admin/sync/' + boardId, { method: 'POST' });
      addLog('sync-log-container', '同步完成：' + (BOARD_LABELS[boardId] || boardId) + (data.result ? ('（' + JSON.stringify(data.result) + '）') : ''), 'success');
      loadDashboard();
    } catch (e) {
      addLog('sync-log-container', '同步失败：' + e.message, 'error');
    }
  }
  window.syncBoard = syncBoard;

  async function syncAll() {
    addLog('sync-log-container', '开始同步全部版块...', 'info');
    try {
      var data = await api('/api/admin/sync', { method: 'POST' });
      addLog('sync-log-container', '全部同步完成' + (data.result ? ('（' + JSON.stringify(data.result) + '）') : ''), 'success');
      loadDashboard();
    } catch (e) {
      addLog('sync-log-container', '同步失败：' + e.message, 'error');
    }
  }
  window.syncAll = syncAll;

  // ---------- 事件绑定 ----------
  function bindEvents() {
    document.getElementById('admin-tabs').addEventListener('click', function (e) {
      var btn = e.target.closest('.admin-tab');
      if (btn) switchTab(btn.dataset.tab);
    });

    // 文章表格操作（事件委托）
    document.getElementById('articles-content').addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-act]');
      if (!btn) return;
      var act = btn.dataset.act;
      var id = btn.dataset.id;
      if (act === 'detail') openArticleDetail(id);
      else if (act === 'set-status') updateArticleStatus(id, btn.dataset.status);
      else if (act === 'delete') deleteArticle(id);
    });

    // 行选择
    document.getElementById('articles-content').addEventListener('change', function (e) {
      var cb = e.target;
      if (cb.classList && cb.classList.contains('row-check')) {
        var id = cb.dataset.id;
        if (cb.checked) selectedNewsIds.add(id); else selectedNewsIds.delete(id);
        updateBatchBar();
      } else if (cb.id === 'check-all') {
        var checked = cb.checked;
        document.querySelectorAll('.row-check').forEach(function (c) { c.checked = checked; });
        selectedNewsIds.clear();
        if (checked) document.querySelectorAll('.row-check').forEach(function (c) { selectedNewsIds.add(c.dataset.id); });
        updateBatchBar();
      }
    });

    // 分页
    document.getElementById('pagination').addEventListener('click', function (e) {
      var btn = e.target.closest('.page-btn');
      if (!btn || btn.disabled) return;
      articlePage = parseInt(btn.dataset.page, 10) || 1;
      loadArticles();
    });

    // 最新要闻表格操作（事件委托）
    document.getElementById('news-content').addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-act]');
      if (!btn) return;
      var act = btn.dataset.act;
      var id = btn.dataset.id;
      if (act === 'edit') {
        // 从当前渲染列表取该条数据
        var items = window.__newsItems || [];
        var item = items.find(function (n) { return String(n.id) === String(id); });
        openNewsModal(item);
      } else if (act === 'toggle') {
        var it = (window.__newsItems || []).find(function (n) { return String(n.id) === String(id); });
        toggleNewsActive(id, !!it.is_active);
      } else if (act === 'del') {
        deleteNews(id);
      }
    });

    // 关键字搜索：回车触发
    document.getElementById('kw-search').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { articlePage = 1; loadArticles(); }
    });

    // 筛选变化：回到第一页重新加载
    ['filter-category', 'filter-status', 'sort-by', 'sort-order'].forEach(function (selId) {
      document.getElementById(selId).addEventListener('change', function () { articlePage = 1; loadArticles(); });
    });

    // AI 分类切换时刷新统计
    document.getElementById('ai-category').addEventListener('change', loadAiStats);
  }

  // ---------- 初始化 ----------
  document.addEventListener('DOMContentLoaded', function () {
    bindEvents();
    loadDashboard();
    loadArticles();
    loadAiStats();
  });
})();