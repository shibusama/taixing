/**
 * 钛星 · Three.js 交互粒子星空（starfield.js）
 * 桌面端：WebGL 粒子漂移 + 邻近连线 + 鼠标视差，叠在极光背景之上、内容之下。
 * 移动端 / 减弱动效 / WebGL 不可用 / 未加载 three 时自动跳过（保留 CSS 极光背景）。
 */
(function () {
  'use strict';
  if (!window.THREE) return;

  var fine = window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!fine || reduced) return;
  if (window.innerWidth < 768) return; // 移动端降级为 CSS 极光背景

  var canvas = document.createElement('canvas');
  canvas.id = 'starfield';
  document.body.appendChild(canvas);

  var renderer, scene, camera, points, lines;
  var W = innerWidth, H = innerHeight;
  var targetX = 0, targetY = 0, mx = 0, my = 0;
  var COUNT = 260;
  var LINK_DIST = 95;

  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: false });
  } catch (e) {
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
    return;
  }
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(70, W / H, 0.1, 1400);
  camera.position.z = 0;

  // 粒子：球壳分布 + 主题色板
  var positions = new Float32Array(COUNT * 3);
  var colors = new Float32Array(COUNT * 3);
  var palette = [[34, 211, 238], [168, 85, 247], [236, 72, 153], [255, 255, 255]];
  for (var i = 0; i < COUNT; i++) {
    var r = 120 + Math.random() * 380;
    var th = Math.random() * Math.PI * 2;
    var ph = Math.acos(2 * Math.random() - 1);
    positions[i * 3] = r * Math.sin(ph) * Math.cos(th);
    positions[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th);
    positions[i * 3 + 2] = r * Math.cos(ph);
    var c = palette[(Math.random() * palette.length) | 0];
    colors[i * 3] = c[0] / 255;
    colors[i * 3 + 1] = c[1] / 255;
    colors[i * 3 + 2] = c[2] / 255;
  }
  var geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  var pm = new THREE.PointsMaterial({
    size: 2.2, vertexColors: true, transparent: true, opacity: 0.9,
    depthWrite: false, blending: THREE.AdditiveBlending
  });
  points = new THREE.Points(geo, pm);
  scene.add(points);

  // 邻近连线（一次构建，与粒子同旋转，保持对齐）
  var lineArr = [];
  for (var a = 0; a < COUNT; a++) {
    var ax = positions[a * 3], ay = positions[a * 3 + 1], az = positions[a * 3 + 2];
    for (var b = a + 1; b < COUNT; b++) {
      var bx = positions[b * 3], by = positions[b * 3 + 1], bz = positions[b * 3 + 2];
      var dx = ax - bx, dy = ay - by, dz = az - bz;
      if (dx * dx + dy * dy + dz * dz < LINK_DIST * LINK_DIST) {
        lineArr.push(ax, ay, az, bx, by, bz);
      }
    }
  }
  var lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(lineArr), 3));
  var lm = new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.1 });
  lines = new THREE.LineSegments(lineGeo, lm);
  scene.add(lines);

  document.addEventListener('mousemove', function (e) {
    targetX = e.clientX / W - 0.5;
    targetY = e.clientY / H - 0.5;
  }, { passive: true });

  function tick() {
    mx += (targetX - mx) * 0.05;
    my += (targetY - my) * 0.05;
    points.rotation.y += 0.0006 - mx * 0.05;
    points.rotation.x += 0.0002 - my * 0.05;
    lines.rotation.y = points.rotation.y;
    lines.rotation.x = points.rotation.x;
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
