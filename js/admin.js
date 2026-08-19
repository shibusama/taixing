// ===== 钛星 · 管理后台脚本（爬虫控制台版：仅保留爬虫控制台） =====
(function () {
  'use strict';

  // ---------- 状态 ----------
  var crawlPollingTimer = null;
  var crawlPolledLines = 0;  // 已消费的实时日志行数

  // ---------- 工具 ----------
  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  async function api(url, opts) {
    var res = await fetch(url, opts);
    var data = {};
    try { data = await res.json(); } catch (e) { /* 非 JSON 响应 */ }
    if (!res.ok) throw new Error(data.detail || data.message || ('HTTP ' + res.status));
    return data;
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

  // 抓取期间禁用操作按钮，防止误触重复启动
  function setControlsDisabled(disabled) {
    document.querySelectorAll('#panel-crawl button').forEach(function (b) {
      b.disabled = disabled;
    });
  }

  async function startCrawl() {
    if (crawlPollingTimer) {
      alert('已有板块正在抓取中，请等待完成');
      return;
    }
    var boardId = document.getElementById('crawl-board').value;
    if (!boardId) { alert('请选择版块'); return; }
    updateCrawlStatus('running');
    setControlsDisabled(true);
    addLog('log-container', '开始抓取：' + boardId, 'info');
    try {
      var resp = await api('/api/crawl/' + boardId + '/start', { method: 'POST' });
      if (resp.status === 'already_running') {
        addLog('log-container', (resp.message || '该板块正在抓取中，请勿重复启动'), 'warn');
        updateCrawlStatus('idle');
        setControlsDisabled(false);
        return;
      }
      addLog('log-container', '爬虫已启动', 'success');
      if (crawlPollingTimer) clearInterval(crawlPollingTimer);
      crawlPolledLines = 0;
      crawlPollingTimer = setInterval(function () { pollCrawlLogs(boardId); }, 1000);
    } catch (e) {
      addLog('log-container', '启动失败：' + e.message, 'error');
      updateCrawlStatus('failed');
      setControlsDisabled(false);
    }
  }
  window.startCrawl = startCrawl;

  async function startCrawlAll() {
    if (crawlPollingTimer) {
      alert('已有板块正在抓取中，请等待完成');
      return;
    }
    updateCrawlStatus('running');
    setControlsDisabled(true);
    addLog('log-container', '开始抓取全部版块...', 'info');
    var boards = ['rocket', 'moon', 'semiconductor', 'china-tech', 'mega-projects', 'controlled-fusion', 'finance'];
    for (var i = 0; i < boards.length; i++) {
      var boardId = boards[i];
      try {
        var resp = await api('/api/crawl/' + boardId + '/start', { method: 'POST' });
        if (resp.status === 'already_running') {
          addLog('log-container', '[' + boardId + '] ' + (resp.message || '正在抓取中，跳过'), 'warn');
          continue;
        }
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

  // 宏观指标一键抓取（独立按钮，固定触发 macro 板块）
  async function startMacroCrawl() {
    if (crawlPollingTimer) {
      alert('已有板块正在抓取中，请等待完成');
      return;
    }
    var boardId = 'macro';
    updateCrawlStatus('running');
    setControlsDisabled(true);
    addLog('log-container', '🪙 开始抓取宏观指标（利率/国债/汇率/期货/商品）...', 'info');
    try {
      var resp = await api('/api/crawl/' + boardId + '/start', { method: 'POST' });
      if (resp.status === 'already_running') {
        addLog('log-container', (resp.message || '宏观指标正在抓取中，请勿重复启动'), 'warn');
        updateCrawlStatus('idle');
        setControlsDisabled(false);
        return;
      }
      addLog('log-container', '宏观爬虫已启动，等待完成...', 'success');
      if (crawlPollingTimer) clearInterval(crawlPollingTimer);
      crawlPolledLines = 0;
      crawlPollingTimer = setInterval(function () { pollCrawlLogs(boardId); }, 1000);
    } catch (e) {
      addLog('log-container', '启动失败：' + e.message, 'error');
      updateCrawlStatus('failed');
      setControlsDisabled(false);
    }
  }
  window.startMacroCrawl = startMacroCrawl;

  async function pollCrawlLogs(boardId) {
    try {
      var data = await api('/api/crawl/' + boardId + '/logs');
      if (data.status === 'idle') {
        if (crawlPollingTimer) { clearInterval(crawlPollingTimer); crawlPollingTimer = null; }
        setControlsDisabled(false);
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
        setControlsDisabled(false);
      }
    } catch (e) {
      console.error('Polling error:', e);
      if (crawlPollingTimer) { clearInterval(crawlPollingTimer); crawlPollingTimer = null; }
      setControlsDisabled(false);
    }
  }
})();
