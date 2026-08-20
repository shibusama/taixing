/**
 * 钛星 · 星系 + 巨型转动球体背景（galaxy.js）
 * 替换原粒子星空：螺旋星系（青→紫旋臂星云，缓慢自转）+
 * 巨型星球（光环 + 外发光，持续自转，右侧大半出画营造巨型感）。
 * 叠在 CSS Aurora 光晕之上、内容之下；鼠标移动整体微视差。
 * 桌面端启用；移动端 / 减弱动效 / WebGL 不可用自动跳过（回落 CSS 极光背景）。
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

  var renderer, scene, camera, galaxy, sphere, sphereGroup, ring;
  var W = innerWidth, H = innerHeight;

  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: false });
  } catch (e) {
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
    return;
  }
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 3000);
  camera.position.z = 60;

  /* ============ 螺旋星系 ============ */
  (function buildGalaxy() {
    var count = 6000;
    var positions = new Float32Array(count * 3);
    var colors = new Float32Array(count * 3);
    var arms = 3;
    var radius = 130;
    var spin = 1.6;
    var randomness = 0.55;
    var colorInner = new THREE.Color(0x22d3ee);
    var colorOuter = new THREE.Color(0xa855f7);
    var insideCount = Math.floor(count * 0.42);

    for (var i = 0; i < count; i++) {
      if (i < insideCount) {
        // 中心星团
        var r = Math.random() * radius * 0.45;
        var a = Math.random() * Math.PI * 2;
        positions[i * 3] = Math.cos(a) * r;
        positions[i * 3 + 1] = Math.sin(a) * r;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
        var c1 = colorInner.clone().lerp(colorOuter, Math.random());
        colors[i * 3] = c1.r; colors[i * 3 + 1] = c1.g; colors[i * 3 + 2] = c1.b;
      } else {
        // 旋臂
        var ra = Math.random() * radius;
        var arm = (i - insideCount) % arms;
        var rot = (ra / radius) * spin;
        var angle = rot + arm * ((Math.PI * 2) / arms);
        var radial = 1 + Math.random() * randomness;
        positions[i * 3] = Math.cos(angle) * ra * radial;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 3.2;
        positions[i * 3 + 2] = Math.sin(angle) * ra * radial;
        var t = ra / radius;
        var c2 = colorInner.clone().lerp(colorOuter, t);
        colors[i * 3] = c2.r; colors[i * 3 + 1] = c2.g; colors[i * 3 + 2] = c2.b;
      }
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    var mat = new THREE.PointsMaterial({
      size: 0.55, vertexColors: true, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    galaxy = new THREE.Points(geo, mat);
    galaxy.rotation.x = Math.PI * 0.38;
    galaxy.rotation.z = Math.PI * 0.06;
    galaxy.position.set(12, 4, -120);
    scene.add(galaxy);
  })();

  /* ============ 巨型转动球体 ============ */
  (function buildSphere() {
    function makeTexture() {
      var c = document.createElement('canvas');
      c.width = c.height = 512;
      var g = c.getContext('2d');
      g.fillStyle = '#0d0d18';
      g.fillRect(0, 0, 512, 512);
      var cols = ['rgba(34,211,238,', 'rgba(168,85,247,', 'rgba(236,72,153,'];
      for (var i = 0; i < 80; i++) {
        g.beginPath();
        g.arc(60 + Math.random() * 392, 60 + Math.random() * 392, 18 + Math.random() * 56, 0, 7);
        g.fillStyle = cols[i % 3] + (0.10 + Math.random() * 0.22).toFixed(2) + ')';
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
    function makeGlow() {
      var c = document.createElement('canvas');
      c.width = c.height = 256;
      var g = c.getContext('2d');
      var grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
      grad.addColorStop(0, 'rgba(34,211,238,.85)');
      grad.addColorStop(0.4, 'rgba(168,85,247,.4)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = grad;
      g.fillRect(0, 0, 256, 256);
      return new THREE.CanvasTexture(c);
    }

    sphereGroup = new THREE.Group();
    sphere = new THREE.Mesh(
      new THREE.SphereGeometry(9, 64, 64),
      new THREE.MeshStandardMaterial({ map: makeTexture(), roughness: 0.82, metalness: 0.06 })
    );
    sphereGroup.add(sphere);

    ring = new THREE.Mesh(
      new THREE.TorusGeometry(13.2, 0.18, 16, 120),
      new THREE.MeshBasicMaterial({
        color: 0x22d3ee, transparent: true, opacity: 0.26,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
      })
    );
    ring.rotation.x = Math.PI / 2.4;
    ring.rotation.z = 0.35;
    sphereGroup.add(ring);

    var glowSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: makeGlow(), transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false })
    );
    glowSprite.scale.set(34, 34, 1);
    sphereGroup.add(glowSprite);

    // 右侧偏大半个出画，营造“巨型”感
    sphereGroup.position.set(38, 1, -8);
    scene.add(sphereGroup);
  })();

  /* ============ 灯光 ============ */
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  var dl = new THREE.DirectionalLight(0x9fd8ff, 1.2);
  dl.position.set(6, 4, 8);
  scene.add(dl);
  var pl = new THREE.PointLight(0xa855f7, 1.2, 44);
  pl.position.set(-6, -2, 4);
  scene.add(pl);

  /* ============ 鼠标视差 ============ */
  var tx = 0, ty = 0, mx = 0, my = 0;
  document.addEventListener('mousemove', function (e) {
    tx = e.clientX / innerWidth - 0.5;
    ty = e.clientY / innerHeight - 0.5;
  }, { passive: true });

  function tick() {
    mx += (tx - mx) * 0.05;
    my += (ty - my) * 0.05;

    // 星系缓慢自转 + 鼠标微视差
    galaxy.rotation.y += 0.0012 + mx * 0.02;
    galaxy.rotation.x = Math.PI * 0.38 + my * 0.02;

    // 巨型球体自转 + 光环旋转
    sphere.rotation.y += 0.004;
    sphere.rotation.x += 0.0006;
    ring.rotation.z += 0.001;
    sphereGroup.rotation.y = mx * 0.5;
    sphereGroup.rotation.x = -my * 0.35;

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
