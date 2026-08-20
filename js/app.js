// ===== 钛星 共享脚本（汉堡菜单 / 回到顶部 / 进度条已统一由 components.js 负责） =====
// --- 滚动入场动画已移交 js/effects.js（含 stagger 与动态渲染兜底），此处不再重复监听 ---

// --- 动态数据日期 ---
(function(){
  const el = document.getElementById('data-date');
  if (!el) return;
  fetch('/api/last-updated')
    .then(r => r.json())
    .then(data => {
      if (data.last_updated && data.last_updated !== '暂无数据') {
        el.textContent = data.last_updated;
      }
    })
    .catch(function(){ /* 接口不可用时保持占位文字 */ });
})();

// --- 动态火箭引言 ---
(function(){
  const el = document.getElementById('rocket-intro');
  if (!el) return;
  fetch('/api/rocket-intro')
    .then(r => r.json())
    .then(data => {
      const raw = data.intro;
      const intro = typeof raw === 'string' ? raw : (raw && typeof raw === 'object' ? (raw.intro || '') : '');
      if (intro) {
        el.innerHTML = intro;
      }
    })
    .catch(function(){ /* 接口不可用时保持静态占位文字 */ });
})();
