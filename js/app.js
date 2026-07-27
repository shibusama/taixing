// ===== 前瞻科技 共享脚本 =====
(function(){
  // --- 汉堡菜单 ---
  const hamburger = document.querySelector('.hamburger');
  const overlay = document.querySelector('.mobile-nav-overlay');
  const mobileNav = document.querySelector('.mobile-nav');
  if(hamburger && overlay && mobileNav){
    hamburger.addEventListener('click',()=>{
      hamburger.classList.toggle('active');
      overlay.classList.toggle('active');
      mobileNav.classList.toggle('active');
      document.body.style.overflow = hamburger.classList.contains('active')?'hidden':'';
    });
    overlay.addEventListener('click',()=>{
      hamburger.classList.remove('active');
      overlay.classList.remove('active');
      mobileNav.classList.remove('active');
      document.body.style.overflow = '';
    });
    mobileNav.querySelectorAll('a').forEach(a=>{a.addEventListener('click',()=>{
      hamburger.classList.remove('active');
      overlay.classList.remove('active');
      mobileNav.classList.remove('active');
      document.body.style.overflow = '';
    })});
  }

  // --- 回到顶部 ---
  const btt = document.querySelector('.back-to-top');
  if(btt){
    window.addEventListener('scroll',()=>{
      btt.classList.toggle('visible', window.scrollY > 400);
    });
    btt.addEventListener('click',()=>{window.scrollTo({top:0,behavior:'smooth'})});
  }

  // --- 阅读进度条 (仅文章页) ---
  const bar = document.querySelector('.progress-bar');
  if(bar){
    window.addEventListener('scroll',()=>{
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const pct = Math.min(100, Math.round((scrollTop / docHeight) * 100));
      bar.style.width = pct + '%';
    });
  }

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
