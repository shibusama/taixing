/**
 * 钛星 · B档视觉增强（b-tier.js）
 * 1) 预加载屏（HTML 中已放 .preloader，这里负责收起）
 * 2) GSAP 滚动叙事（仅首页：Hero 滚动退场视差；GSAP 本地库，未加载时静默跳过）
 * 3) 按钮流光 / 标题扫光由 style-v2.css 实现，无需 JS
 *
 * 守卫：prefers-reduced-motion 时跳过 GSAP 动效；库未加载不报错。
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

  /* ---------- 2. GSAP 滚动叙事（仅首页 Hero 退场，不与 A 档入场冲突） ---------- */
  (function initScrollNarrative() {
    if (reduced) return;
    var hero = document.querySelector('.hero');
    if (!hero) return;          // 仅首页
    if (!window.gsap) return;   // 库未加载则静默跳过

    if (window.ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
    }

    gsap.to('.hero .wrap', {
      yPercent: 22,
      opacity: 0.12,
      scale: 0.965,
      ease: 'none',
      scrollTrigger: {
        trigger: '.hero',
        start: 'top top',
        end: 'bottom top',
        scrub: true
      }
    });
  })();
})();
