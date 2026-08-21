/**
 * 钛星 · A档视觉动效（effects.js）
 * 自定义光标 / Hero 视差光斑 / 3D tilt / 滚动入场(stagger) / 数字计数 / 最新要闻跑马灯
 *
 * - 指针类效果仅在 (hover:hover) and (pointer:fine) 的桌面启用，移动端自动跳过。
 * - prefers-reduced-motion 时跳过所有主动画（CSS 侧也已被 style-base 禁用）。
 * - 通过 MutationObserver 兜底：动态渲染的卡片/计数同样获得动效。
 * - 所有操作只做 class/transform 增强，不修改任何数据。
 */
(function () {
  'use strict';

  var finePointer = window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ============================================================
   * 1. 自定义光标（发光圆点 + 缓动光环）
   * ============================================================ */
  function initCursor() {
    if (!finePointer || reduced) return;
    var dot = document.createElement('div');
    dot.className = 'cursor-dot';
    var ring = document.createElement('div');
    ring.className = 'cursor-ring';
    document.body.appendChild(dot);
    document.body.appendChild(ring);
    document.documentElement.classList.add('custom-cursor');
    // 首次移动前隐藏，避免角落闪现
    document.body.classList.add('cursor-idle');

    var x = innerWidth / 2, y = innerHeight / 2;
    var rx = x, ry = y;
    var visible = false, raf = null;

    function place() {
      dot.style.transform = 'translate3d(' + x + 'px,' + y + 'px,0) translate(-50%,-50%)';
      ring.style.transform = 'translate3d(' + rx + 'px,' + ry + 'px,0) translate(-50%,-50%)';
      raf = null;
    }
    function loop() {
      rx += (x - rx) * 0.16;
      ry += (y - ry) * 0.16;
      place();
      if (Math.abs(rx - x) > 0.05 || Math.abs(ry - y) > 0.05) {
        raf = requestAnimationFrame(loop);
      }
    }

    window.addEventListener('mousemove', function (e) {
      x = e.clientX; y = e.clientY;
      if (!visible) {
        visible = true;
        document.body.classList.remove('cursor-idle');
        rx = x; ry = y;
        place();
      }
      if (!raf) raf = requestAnimationFrame(loop);
    }, { passive: true });

    document.addEventListener('mouseleave', function () {
      visible = false;
      document.body.classList.add('cursor-idle');
    });

    var HOVER = 'a,button,input,select,textarea,[role="button"],.card,.section-card,.company-card,.route,.hl-card,.breakdown-card,.pt-group,.fusion-tl-col,.company,.debt-card,.rate-card,.bond-card,.fx-card,.member-card,.com-card,.kpi-card,.tlv-card,.tab-nav button,.back-to-top,.quick-nav a,.tk-item a,.kv';
    document.addEventListener('mouseover', function (e) {
      var t = e.target;
      if (t && t.closest && t.closest(HOVER)) ring.classList.add('hover');
    }, { passive: true });
    document.addEventListener('mouseout', function (e) {
      var t = e.target;
      if (t && t.closest && t.closest(HOVER)) ring.classList.remove('hover');
    }, { passive: true });
    window.addEventListener('mousedown', function () { ring.classList.add('press'); }, { passive: true });
    window.addEventListener('mouseup', function () { ring.classList.remove('press'); }, { passive: true });
  }

  /* ============================================================
   * 2. Hero 鼠标视差（光斑 + data-parallax 子元素）
   * ============================================================ */
  function initParallax() {
    if (!finePointer || reduced) return;
    var hero = document.querySelector('.hero');
    if (!hero) return;
    var px = 0, py = 0, tx = 0, ty = 0, raf = null;

    function step() {
      px += (tx - px) * 0.10;
      py += (ty - py) * 0.10;
      hero.style.setProperty('--px', px.toFixed(3));
      hero.style.setProperty('--py', py.toFixed(3));
      var kids = hero.querySelectorAll('[data-parallax]');
      for (var i = 0; i < kids.length; i++) {
        var d = parseFloat(kids[i].getAttribute('data-parallax')) || 8;
        kids[i].style.transform = 'translate3d(' + (px * d).toFixed(2) + 'px,' + (py * d).toFixed(2) + 'px,0)';
      }
      raf = null;
    }
    hero.addEventListener('mousemove', function (e) {
      var r = hero.getBoundingClientRect();
      tx = ((e.clientX - r.left) / r.width) * 2 - 1;
      ty = ((e.clientY - r.top) / r.height) * 2 - 1;
      if (!raf) raf = requestAnimationFrame(step);
    }, { passive: true });
    hero.addEventListener('mouseleave', function () { tx = 0; ty = 0; });
  }

  /* ============================================================
   * 3. 卡片 3D tilt（轻量自写，无依赖）
   * ============================================================ */
  var TILT_SEL = '.section-card,.news-grid .card,.company-card,.route,.hl-card,.breakdown-card,.pt-group,.fusion-tl-col,.company,.debt-card,.rate-card,.bond-card,.fx-card,.member-card,.com-card,.tlv-card';
  function initTilt() {
    if (!finePointer || reduced) return function () {};
    function bindTilt(c) {
      if (c.__tilt) return;
      c.__tilt = true;
      var s = { rx: 0, ry: 0, tx: 0, ty: 0, raf: null };
      c.addEventListener('pointerenter', function () {
        c.style.transition = 'transform .12s ease-out';
      });
      c.addEventListener('pointermove', function (e) {
        var r = c.getBoundingClientRect();
        var px = ((e.clientX - r.left) / r.width) * 2 - 1;
        var py = ((e.clientY - r.top) / r.height) * 2 - 1;
        s.ty = -py * 8;   // 顶部悬停时上缘后仰
        s.tx = px * 10;   // 左右倾斜
        if (!s.raf) {
          s.raf = requestAnimationFrame(function () {
            s.raf = null;
            s.rx += (s.ty - s.rx) * 0.25;
            s.ry += (s.tx - s.ry) * 0.25;
            c.style.transform = 'perspective(900px) rotateX(' + s.rx.toFixed(2) + 'deg) rotateY(' + s.ry.toFixed(2) + 'deg) scale3d(1.02,1.02,1.02)';
          });
        }
      }, { passive: true });
      c.addEventListener('pointerleave', function () {
        s.tx = 0; s.ty = 0;
        c.style.transition = 'transform .5s cubic-bezier(.2,.8,.2,1)';
        c.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg)';
      });
    }
    document.querySelectorAll(TILT_SEL).forEach(bindTilt);
    return bindTilt;
  }

  /* ============================================================
   * 4. 滚动入场（stagger 延迟，复用 .anim-in / fadeInUp）
   * ============================================================ */
  var REVEAL_SEL = '.hero .wrap,.bd-hero,.bd-sec-head,.sec-head,.section-card,.card,.company-card,.company,.route,.tl-item,.hl-card,.tlv-row,.tlv-card,.fusion-tl-col,.pt-group,.cmp-wrap,.news-list,.data-table-wrap,.quick-nav,.highlight-row,.breakdown-card';
  function initReveal() {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add('anim-in');
        observer.unobserve(en.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

    function bind(el) {
      if (el.__reveal) return;
      el.__reveal = true;
      var parent = el.parentElement;
      var siblings = [];
      if (parent && parent.children) {
        for (var i = 0; i < parent.children.length; i++) {
          var ch = parent.children[i];
          if (ch.matches && ch.matches(REVEAL_SEL)) siblings.push(ch);
        }
      } else {
        siblings.push(el);
      }
      var idx = siblings.indexOf(el);
      var delay = Math.min(idx * 90, 540);
      el.style.setProperty('--d', delay + 'ms');
      observer.observe(el);
    }
    document.querySelectorAll(REVEAL_SEL).forEach(bind);
    return bind;
  }

  /* ============================================================
   * 5. 数字滚动计数（[data-count] 显式标记，如 40+ / 7）
   * ============================================================ */
  function initCount() {
    function bindCount(el) {
      if (el.__count) return;
      el.__count = true;
      var target = parseFloat(el.getAttribute('data-count'));
      if (isNaN(target)) return;
      var prefix = el.getAttribute('data-prefix') || '';
      var suffix = el.getAttribute('data-suffix') || '';
      var dec = parseInt(el.getAttribute('data-decimals') || '0', 10);
      var duration = 1400;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          io.disconnect();
          var start = null;
          function frame(ts) {
            if (start === null) start = ts;
            var p = Math.min(1, (ts - start) / duration);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = prefix + (target * eased).toFixed(dec) + suffix;
            if (p < 1) requestAnimationFrame(frame);
            else el.textContent = prefix + target.toFixed(dec) + suffix;
          }
          requestAnimationFrame(frame);
        });
      }, { threshold: 0.4 });
      io.observe(el);
    }
    document.querySelectorAll('[data-count]').forEach(bindCount);
    return bindCount;
  }

  /* ============================================================
   * 6. 最新要闻跑马灯（header 注入的 .ticker，数据来自 /api/latest-news）
   * ============================================================ */
  var FALLBACK_BOARDS = ['可回收火箭', '中美登月', '中国科技', '超级工程', '可控核聚变', '科技资本', '宏观指标'];
  function initTicker() {
    function buildItem(board, title, link) {
      var span = document.createElement('span');
      span.className = 'tk-item';
      var b = document.createElement('span');
      b.className = 'tk-board';
      b.textContent = board;
      var a = document.createElement('a');
      a.href = link || '#';
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = title;
      span.appendChild(b);
      span.appendChild(a);
      return span;
    }
    function populate(ticker) {
      if (ticker.__done) return;
      ticker.__done = true;
      var trackA = ticker.querySelector('.tk-track-a');
      var trackB = ticker.querySelector('.tk-track-b');
      if (!trackA || !trackB) return;
      function fill(items) {
        if (!items.length) {
          FALLBACK_BOARDS.forEach(function (name) {
            trackA.appendChild(buildItem(name, '前沿动态 · AI 实时聚合', ''));
            trackB.appendChild(buildItem(name, '前沿动态 · AI 实时聚合', ''));
          });
        } else {
          items.forEach(function (it, idx) {
            var item = buildItem(it.board_label || it.board || '要闻', it.title || '', it.link || '');
            if (idx % 2 === 0) trackA.appendChild(item);
            else trackB.appendChild(item);
          });
        }
        trackA.innerHTML += trackA.innerHTML; // 复制一份，无缝循环
        trackB.innerHTML += trackB.innerHTML;
        ticker.classList.add('ready');
      }
      fetch('/api/latest-news?limit=14&t=' + Date.now())
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function (data) {
          fill((data && Array.isArray(data.items)) ? data.items : []);
        })
        .catch(function () { fill([]); });
    }
    var tk = document.querySelector('.ticker');
    if (tk) populate(tk);
    return populate;
  }

  /* ============================================================
   * 7. MutationObserver：兜底动态渲染的卡片 / 计数 / tilt / ticker
   * ============================================================ */
  function initWatcher() {
    var bindReveal = initReveal();
    var bindCount = initCount();
    var bindTilt = initTilt();
    var populateTicker = initTicker();
    var observer = new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        m.addedNodes.forEach(function (n) {
          if (!n || n.nodeType !== 1) return;
          if (n.matches && n.matches(REVEAL_SEL)) bindReveal(n);
          if (n.querySelectorAll) n.querySelectorAll(REVEAL_SEL).forEach(bindReveal);
          if (n.matches && n.matches(TILT_SEL)) bindTilt(n);
          if (n.querySelectorAll) n.querySelectorAll(TILT_SEL).forEach(bindTilt);
          if (n.matches && n.matches('[data-count]')) bindCount(n);
          if (n.querySelectorAll) n.querySelectorAll('[data-count]').forEach(bindCount);
          if (n.matches && n.matches('.ticker')) populateTicker(n);
          if (n.querySelectorAll) n.querySelectorAll('.ticker').forEach(populateTicker);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* ============================================================
   * 启动
   * ============================================================ */
  function boot() {
    // initCursor(); // 自定义光标特效已按用户要求移除
    initParallax();
    initWatcher();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
