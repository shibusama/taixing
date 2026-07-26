/**
 * 钛星数据加载器 — 通用模块
 * 每个页面在底部调用：loadData('finance').then(render)
 */

const DATA_BASE = './data/';

async function loadData(module) {
  try {
    const res = await fetch(`${DATA_BASE}${module}.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`[钛星] 加载 ${module}.json 失败:`, e.message);
    return null;
  }
}

/**
 * 通用卡片渲染 — 将 data.companies 渲染到指定容器
 * container: CSS 选择器，如 '#finance-cards'
 * items: 数组，每项含 {tag, name, desc, highlight?, grid: [{k,v}]}
 */
function renderCards(container, items) {
  const el = document.querySelector(container);
  if (!el || !items) return;
  el.innerHTML = items.map(item => {
    const grid = (item.grid || []).map(kv =>
      `<div class="kv"><span class="k">${kv.k}</span><span class="v">${kv.v}</span></div>`
    ).join('');
    const hl = item.highlight
      ? `<div class="card-hl"><span class="hl-num">${item.highlight.num}</span><span class="hl-unit">${item.highlight.unit}</span><span class="hl-label">${item.highlight.label}</span></div>`
      : '';
    return `
      <div class="company">
        <span class="tl-badge">${item.tag}</span>
        <h3>${item.name}</h3>
        <p>${item.desc}</p>
        <div class="company-grid">${grid}</div>
        ${hl}
      </div>`;
  }).join('');
}

/**
 * 通用时间线渲染
 * container: CSS 选择器
 * items: 数组，每项含 {date, title, desc, status: 'done'|'prog'|'plan'}
 */
function renderTimeline(container, items) {
  const el = document.querySelector(container);
  if (!el || !items) return;
  el.innerHTML = items.map(item => {
    const cls = item.status === 'done' ? 'green' : item.status === 'prog' ? '' : 'amber';
    return `
      <div class="tl-item ${cls}">
        <div class="tl-date">${item.date}</div>
        <h4>${item.title}</h4>
        <p>${item.desc}</p>
      </div>`;
  }).join('');
}

/**
 * 通用表格渲染
 * container: CSS 选择器
 * headers: 表头数组
 * rows: 行数组（每项是单元格字符串数组）
 */
function renderTable(container, headers, rows) {
  const el = document.querySelector(container);
  if (!el || !rows) return;
  const th = headers.map(h => `<th>${h}</th>`).join('');
  const tr = rows.map(row => `<tr>${row.map(c => `<td>${c}</td>`).join('')}</tr>`).join('');
  el.innerHTML = `<table class="data-table"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
}

/**
 * 通用列表渲染（用于新闻列表、事件列表）
 * container: CSS 选择器
 * items: 数组，每项含 {date, title, tag?, url?}
 */
function renderList(container, items) {
  const el = document.querySelector(container);
  if (!el || !items) return;
  el.innerHTML = items.map(item => {
    const tag = item.tag ? `<span class="news-tag">${item.tag}</span>` : '';
    const link = item.url ? `<a href="${item.url}" target="_blank">${item.title}</a>` : item.title;
    return `<div class="news-item">${tag}<span class="news-date">${item.date}</span><span class="news-title">${link}</span></div>`;
  }).join('');
}

window.taixingData = { loadData, renderCards, renderTimeline, renderTable, renderList };
