/**
 * 钛星 · C档：Hero 3D 星球（planet3d.js）
 * 程序化生成的 3D 天体悬浮在 Hero 右侧空白区：
 *   自转 + 光环自旋 + 外发光 + 鼠标视差 + 上下浮动 + 滚动淡出（滚动过 Hero 后暂停渲染省 GPU）。
 * 桌面端（fine pointer 且视口 ≥1360px）启用；移动端 / 减弱动效 / WebGL 不可用自动跳过。
 */
(function () {
  'use strict';
  if (!window.THREE) return;

  var fine = window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!fine || reduced) return;
  if (window.innerWidth < 1360) return;

  var canvas = document.createElement('canvas');
  canvas.id = 'planet3d';
  document.body.appendChild(canvas);

  var renderer, scene, camera, group, planet, ring, glow;
  var W = canvas.clientWidth || 420;
  var H = canvas.clientHeight || 420;

  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  } catch (e) {
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
    return;
  }
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 200);
  camera.position.z = 7;

  // 灯光
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  var dir = new THREE.DirectionalLight(0x9fd8ff, 1.3);
  dir.position.set(4, 3, 5);
  scene.add(dir);
  var purp = new THREE.PointLight(0xa855f7, 1.4, 24);
  purp.position.set(-4, -2, 3);
  scene.add(purp);

  group = new THREE.Group();

  // ---- 星球本体（canvas 生成表面纹理：深底 + 青/紫/粉块 + 细网格线） ----
  function makeTexture() {
    var c = document.createElement('canvas');
    c.width = c.height = 512;
    var g = c.getContext('2d');
    g.fillStyle = '#0d0d18';
    g.fillRect(0, 0, 512, 512);
    var colors = ['rgba(34,211,238,', 'rgba(168,85,247,', 'rgba(236,72,153,'];
    for (var i = 0; i < 70; i++) {
      g.beginPath();
      g.arc(60 + Math.random() * 392, 60 + Math.random() * 392, 18 + Math.random() * 56, 0, 7);
      g.fillStyle = colors[i % 3] + (0.10 + Math.random() * 0.22).toFixed(2) + ')';
      g.fill();
    }
    g.strokeStyle = 'rgba(34,211,238,.10)';
    g.lineWidth = 1;
    for (var lat = 1; lat < 5; lat++) {
      g.beginPath();
      g.arc(256, 256, 40 + lat * 46, 0, 7);
      g.stroke();
    }
    g.beginPath();
    g.arc(256, 256, 230, 0, 7);
    g.strokeStyle = 'rgba(168,85,247,.12)';
    g.stroke();
    var t = new THREE.CanvasTexture(c);
    t.anisotropy = 2;
    return t;
  }
  planet = new THREE.Mesh(
    new THREE.SphereGeometry(1.35, 64, 64),
    new THREE.MeshStandardMaterial({ map: makeTexture(), roughness: 0.82, metalness: 0.06 })
  );
  group.add(planet);

  // ---- 光环 ----
  ring = new THREE.Mesh(
    new THREE.TorusGeometry(2.05, 0.045, 16, 120),
    new THREE.MeshBasicMaterial({
      color: 0x22d3ee, transparent: true, opacity: 0.3,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
    })
  );
  ring.rotation.x = Math.PI / 2.4;
  ring.rotation.y = 0.4;
  group.add(ring);

  // ---- 外发光 ----
  function makeGlow() {
    var c = document.createElement('canvas');
    c.width = c.height = 256;
    var g = c.getContext('2d');
    var grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    grad.addColorStop(0, 'rgba(34,211,238,.85)');
    grad.addColorStop(0.4, 'rgba(168,85,247,.38)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  }
  glow = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: makeGlow(), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  glow.scale.set(7.6, 7.6, 1);
  group.add(glow);

  group.position.y = -0.1;
  scene.add(group);

  // ---- 鼠标视差 ----
  var targetX = 0, targetY = 0, mx = 0, my = 0;
  document.addEventListener('mousemove', function (e) {
    targetX = e.clientX / innerWidth - 0.5;
    targetY = e.clientY / innerHeight - 0.5;
  }, { passive: true });

  // ---- 滚动范围 ----
  var hero = document.querySelector('.hero');
  var heroBottom = hero ? hero.offsetTop + hero.offsetHeight : innerHeight;

  var t = 0;
  function tick() {
    t += 0.016;
    mx += (targetX - mx) * 0.06;
    my += (targetY - my) * 0.06;

    planet.rotation.y += 0.004;
    planet.rotation.x += 0.0006;
    ring.rotation.z += 0.0012;
    group.rotation.y = mx * 0.8;
    group.rotation.x = -my * 0.5;
    group.position.y = Math.sin(t * 0.5) * 0.14 - 0.1;

    // 滚动淡出；滚过 Hero 后暂停渲染
    var sc = window.scrollY;
    var p = Math.min(1, Math.max(0, sc / (heroBottom || 1)));
    canvas.style.opacity = (1 - p * p).toFixed(3);
    if (sc < heroBottom * 1.15) {
      renderer.render(scene, camera);
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  window.addEventListener('resize', function () {
    W = canvas.clientWidth || 420;
    H = canvas.clientHeight || 420;
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  });
})();
