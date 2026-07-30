/**
 * 钛星 · 公共组件加载器
 * 自动将 components/ 目录下的 HTML 片段注入页面容器
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
      var href = a.getAttribute('href');
      if (href === path) {
        a.classList.add('on');
      }
    });
  }

  /**
   * 汉堡菜单切换
   */
  function initHamburger() {
    var hamburger = document.querySelector('.hamburger');
    var mobileNav = document.querySelector('.mobile-nav');
    var overlay = document.querySelector('.mobile-nav-overlay');
    if (!hamburger || !mobileNav || !overlay) return;

    function closeMenu() {
      hamburger.classList.remove('active');
      mobileNav.classList.remove('active');
      overlay.classList.remove('active');
    }

    hamburger.addEventListener('click', function() {
      hamburger.classList.toggle('active');
      mobileNav.classList.toggle('active');
      overlay.classList.toggle('active');
    });

    overlay.addEventListener('click', closeMenu);
    mobileNav.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', closeMenu);
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
    });
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /**
   * 阅读进度条
   */
  function initProgressBar() {
    var bar = document.getElementById('progressBar');
    if (!bar) return;
    window.addEventListener('scroll', function() {
      var scrollTop = window.scrollY;
      var docHeight = document.documentElement.scrollHeight - window.innerHeight;
      var progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = progress + '%';
    });
  }

  /**
   * 导航栏滚动阴影
   */
  function initScrollEffect() {
    var topbar = document.querySelector('.topbar');
    if (!topbar) return;
    window.addEventListener('scroll', function() {
      topbar.classList.toggle('scrolled', window.scrollY > 10);
    });
  }

  // ===== 初始化 =====
  function init() {
    highlightCurrentNav();
    initHamburger();
    initBackToTop();
    initProgressBar();
    initScrollEffect();
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
