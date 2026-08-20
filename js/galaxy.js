/**
 * 钛星 · 深空星点背景（galaxy.js - 星点版）
 * 全屏细密星点 + 缓慢旋转 + 鼠标视差，作为页面背景氛围。
 * 桌面端启用；移动端 / 减弱动效 / WebGL 不可用自动跳过。
 */
(function () {
  'use strict';
  if (!window.THREE) return;

  var fine = window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!fine || reduced) return;
  if (window.innerWidth < 1024) return;

  var canvas = document.createElement('canvas');
  canvas.id = 'galaxy';
  document.body.appendChild(canvas);

  var renderer, scene, camera;
  var stars;
  var W = innerWidth, H = innerHeight;

  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  } catch (e) {
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
    return;
  }
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 500);
  camera.position.z = 40;

  /* ==================== 深空星点 ==================== */
  (function buildStars() {
    var count = 1200;
    var pos = new Float32Array(count * 3);
    for (var i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 200;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 130;
      pos[i * 3 + 2] = -10 - Math.random() * 90;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var mat = new THREE.PointsMaterial({
      color: 0xffffff, size: 0.3, sizeAttenuation: true,
      transparent: true, opacity: 0.55,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    stars = new THREE.Points(geo, mat);
    scene.add(stars);
  })();

  /* ==================== 鼠标视差 ==================== */
  var tx = 0, ty = 0, mx = 0, my = 0;
  document.addEventListener('mousemove', function (e) {
    tx = e.clientX / innerWidth - 0.5;
    ty = e.clientY / innerHeight - 0.5;
  }, { passive: true });

  function tick() {
    mx += (tx - mx) * 0.05;
    my += (ty - my) * 0.05;

    stars.rotation.y += 0.0003 + mx * 0.01;
    stars.rotation.x = my * 0.01;

    renderer.render(scene, camera);
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  window.addEventListener('resize', function () {
    W = innerWidth; H = innerHeight;
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  });
})();
