/**
 * 钛星 · B/C档视觉增强（b-tier.js）
 * 1) 预加载屏收起
 * 2) GSAP 滚动叙事（首页）：Hero 滚动退场 + 形变（标题缩放/模糊、元素分层淡出）
 * 3) 交互式时间线（全站 .tl / .tl-versus）：滚动进度填充 + 点击聚焦高亮
 *
 * 守卫：prefers-reduced-motion 时跳过动效；GSAP 未加载时首页叙事静默跳过。
 * 时间线进度用纯 JS（rAF 节流）实现，不依赖 GSAP，全站生效。
 */
(function () {
  'use strict';

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 1. 预加载屏收起 ---------- */
  (function initPreloader() {
    var pl = document.querySelector('.preloader');
    if (!pl) return;
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      pl.classList.add('done');
      setTimeout(function () {
        if (pl.parentNode) pl.parentNode.removeChild(pl);
      }, 600);
    }
    window.addEventListener('load', finish);
    setTimeout(finish, 2500); // 兜底：绝不因加载屏卡住页面
  })();

  /* ---------- 2. GSAP 滚动叙事（仅首页：Hero 退场 + 形变） ---------- */
  (function initScrollNarrative() {
    if (reduced) return;
    if (!document.querySelector('.hero')) return;
    if (!window.gsap) return;
    if (window.ScrollTrigger) gsap.registerPlugin(ScrollTrigger);

    var st = {
      trigger: '.hero',
      start: 'top top',
      end: 'bottom top',
      scrub: true
    };

    // 整卡上移 + 微缩 + 淡出
    gsap.to('.hero .wrap', {
      yPercent: 22, scale: 0.96, opacity: 0.15, ease: 'none', scrollTrigger: st
    });

    // 标题形变：缩小上移 + 轻微模糊（.glow 非鼠标视差目标，无 transform 冲突）
    gsap.to('.hero h1 .glow', {
      scale: 0.8, yPercent: 20, opacity: 0.2, filter: 'blur(7px)', ease: 'none', scrollTrigger: st
    });

    // 元素分层淡出（只动 opacity，不与鼠标视差的 transform 冲突）
    gsap.to('.hero .kicker, .hero .sub, .hero .hero-stats', {
      opacity: 0, ease: 'none', scrollTrigger: st
    });
  })();

  /* ---------- 3. 交互式时间线（全站） ---------- */
  (function initInteractiveTimelines() {
    if (reduced) return;
    var containers = Array.prototype.slice.call(document.querySelectorAll('.tl, .tl-versus'));
    if (!containers.length) return;

    // 3a. 滚动进度填充：--tlp 0→1 控制 CSS ::after 的 scaleY
    var ticking = false;
    function update() {
      var vh = window.innerHeight;
      containers.forEach(function (el) {
        var r = el.getBoundingClientRect();
        var total = r.height + vh;
        var p = (vh - r.top) / total;
        p = Math.max(0, Math.min(1, p));
        el.style.setProperty('--tlp', p.toFixed(3));
      });
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();

    // 3b. 点击聚焦：高亮当前条目（同容器内互斥）
    document.addEventListener('click', function (e) {
      var item = e.target && e.target.closest ? e.target.closest('.tl-item') : null;
      if (!item) return;
      var container = item.closest('.tl, .tl-versus');
      if (container) {
        container.querySelectorAll('.tl-item.active').forEach(function (x) {
          if (x !== item) x.classList.remove('active');
        });
      }
      item.classList.toggle('active');
    });
  })();
})();
