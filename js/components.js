/**
 * 钛星 · 公共组件加载器
 * 自动将 components/ 目录下的 HTML 片段注入页面容器
 * 全局 API：window.loadComponent(selector, url)
 */
(function() {
  'use strict';

  /**
   * 加载 HTML 组件并注入到指定的 DOM 容器
   * @param {string} selector - 容器 CSS 选择器
   * @param {string} url - 组件 HTML 文件路径
   * @returns {Promise<void>}
   */
  function loadComponent(selector, url) {
    var container = document.querySelector(selector);
    if (!container) return Promise.resolve();
    return fetch(url + '?t=' + Date.now())
      .then(function(res) { return res.text(); })
      .then(function(html) {
        container.innerHTML = html;
      })
      .catch(function(err) {
        console.warn('[钛星] 组件加载失败:', url, err.message);
      });
  }

  /**
   * 页面加载后高亮当前导航项
   */
  function highlightCurrentNav() {
    var path = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav a, .mobile-nav a').forEach(function(a) {
      if (a.getAttribute('href') === path) {
        a.classList.add('on');
      }
    });
  }

  /**
   * 汉堡菜单切换（含滚动锁定 / Esc 关闭 / 窗口变宽自动收起）
   */
  function initHamburger() {
    var hamburger = document.querySelector('.hamburger');
    var mobileNav = document.querySelector('.mobile-nav');
    var overlay = document.querySelector('.mobile-nav-overlay');
    if (!hamburger || !mobileNav || !overlay) return;

    // 与 CSS 中汉堡菜单断点保持一致（style-nav.css @media max-width:860px）
    var DESKTOP_BREAKPOINT = 860;

    function setMenu(open) {
      hamburger.classList.toggle('active', open);
      mobileNav.classList.toggle('active', open);
      overlay.classList.toggle('active', open);
      document.body.style.overflow = open ? 'hidden' : '';
      if (hamburger.getAttribute) {
        hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
      }
    }

    hamburger.addEventListener('click', function() {
      setMenu(!mobileNav.classList.contains('active'));
    });
    overlay.addEventListener('click', function() { setMenu(false); });
    mobileNav.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', function() { setMenu(false); });
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') setMenu(false);
    });
    window.addEventListener('resize', function() {
      if (window.innerWidth > DESKTOP_BREAKPOINT) setMenu(false);
    });
  }

  /**
   * 回到顶部按钮
   */
  function initBackToTop() {
    var btn = document.querySelector('.back-to-top');
    if (!btn) return;
    window.addEventListener('scroll', function() {
      btn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /**
   * 阅读进度条（兼容 #progressBar 与 .progress-bar 两种写法）
   */
  function initProgressBar() {
    var bar = document.querySelector('#progressBar, .progress-bar');
    if (!bar) return;
    var ticking = false;
    function update() {
      var scrollTop = window.scrollY;
      var docHeight = document.documentElement.scrollHeight - window.innerHeight;
      var progress = docHeight > 0 ? Math.min(100, (scrollTop / docHeight) * 100) : 0;
      bar.style.width = progress + '%';
      ticking = false;
    }
    window.addEventListener('scroll', function() {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }, { passive: true });
  }

  /**
   * 导航栏滚动阴影
   */
  function initScrollEffect() {
    var topbar = document.querySelector('.topbar');
    if (!topbar) return;
    window.addEventListener('scroll', function() {
      topbar.classList.toggle('scrolled', window.scrollY > 10);
    }, { passive: true });
  }

  // ===== 初始化 =====
  // 注：公共 header/footer 由本文件自动注入（页面只需放置占位容器），
  // 注入完成后才绑定导航高亮 / 汉堡菜单 / 滚动阴影，避免依赖未就绪的 DOM。
  function init() {
    initBackToTop();
    initProgressBar();

    loadComponent('#header-placeholder', 'components/header.html').then(function() {
      highlightCurrentNav();
      initHamburger();
      initScrollEffect();
    });
    loadComponent('#footer-placeholder', 'components/footer.html');
  }

  // 暴露 loadComponent 供全局使用
  window.loadComponent = loadComponent;

  // DOM 就绪后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
