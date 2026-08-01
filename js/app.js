// ===== 钛星 共享脚本（汉堡菜单 / 回到顶部 / 进度条已统一由 components.js 负责） =====
(function(){
  // --- 滚动动画 ---
  const observer = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('anim-in');observer.unobserve(e.target)}});
  },{threshold:.15});
  document.querySelectorAll('.company,.card,.section-card,.route,.tl-item,.hl-card').forEach(el=>{
    observer.observe(el);
  });
})();

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
