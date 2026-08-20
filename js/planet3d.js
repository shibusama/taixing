/**
 * 钛星 · 巨型旋转球体（planet3d.js）
 * 独立的 3D 星球悬浮在 Hero 右侧空白区：自转 + 光环 + 大气层边缘光 + 外发光 + 鼠标视差 + 滚动淡出。
 * 保持低调：只有这一个主体，不铺星系；滚过 Hero 后淡出并暂停渲染省 GPU。
 * 桌面大屏（fine pointer 且 ≥1360px）启用；移动端 / 减弱动效 / WebGL 不可用自动跳过。
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

  var renderer, scene, camera, group, planet, atm, ring, glow;
  var W = canvas.clientWidth || 560;
  var H = canvas.clientHeight || 560;

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

  /* ---- 工具 ---- */
  function makeTexture() {
    var c = document.createElement('canvas');
    c.width = c.height = 512;
    var g = c.getContext('2d');

    // 深色基底：两极略暗的纵向渐变
    var base = g.createLinearGradient(0, 0, 0, 512);
    base.addColorStop(0, '#080b14');
    base.addColorStop(0.5, '#141b2e');
    base.addColorStop(1, '#080b14');
    g.fillStyle = base;
    g.fillRect(0, 0, 512, 512);

    // 横向云带（类土星气态，冷色调），柔和渐变带
    var bands = [
      { y: 0.10, h: 0.09, c: '34,211,238', a: 0.17 },
      { y: 0.24, h: 0.05, c: '129,140,248', a: 0.21 },
      { y: 0.36, h: 0.12, c: '168,85,247', a: 0.14 },
      { y: 0.50, h: 0.07, c: '34,211,238', a: 0.18 },
      { y: 0.63, h: 0.11, c: '129,140,248', a: 0.16 },
      { y: 0.78, h: 0.06, c: '34,211,238', a: 0.13 },
      { y: 0.90, h: 0.08, c: '168,85,247', a: 0.11 }
    ];
    bands.forEach(function (b) {
      var yy = b.y * 512;
      var hh = b.h * 512;
      var bg = g.createLinearGradient(0, yy - hh, 0, yy + hh);
      bg.addColorStop(0, 'rgba(' + b.c + ',0)');
      bg.addColorStop(0.5, 'rgba(' + b.c + ',' + b.a + ')');
      bg.addColorStop(1, 'rgba(' + b.c + ',0)');
      g.fillStyle = bg;
      g.fillRect(0, yy - hh, 512, hh * 2);
    });

    // 横向细波纹（增强云层流动感）
    for (var i = 0; i < 70; i++) {
      var wy = Math.random() * 512;
      var wa = Math.random() * 0.05 + 0.01;
      g.fillStyle = 'rgba(255,255,255,' + wa.toFixed(3) + ')';
      g.fillRect(0, wy, 512, Math.random() * 2 + 0.5);
    }

    // 细腻颗粒噪声（云层质感）
    for (var j = 0; j < 500; j++) {
      var px = Math.random() * 512;
      var py = Math.random() * 512;
      var pr = Math.random() * 1.4 + 0.3;
      g.fillStyle = 'rgba(255,255,255,' + (Math.random() * 0.05).toFixed(3) + ')';
      g.beginPath();
      g.arc(px, py, pr, 0, 7);
      g.fill();
    }

    var t = new THREE.CanvasTexture(c);
    t.anisotropy = 4;
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
  function makeRingTexture() {
    // 径向多层环带 + 冰粒颗粒，模拟真实土星环（含 Cassini 缝 + 外缘渐隐）
    var c = document.createElement('canvas');
    c.width = c.height = 1024;
    var g = c.getContext('2d');
    g.clearRect(0, 0, 1024, 1024);
    var cx = 512, cy = 512;

    // 环带定义：[内半径px, 外半径px, 透明度]（内环→亮环→缝→A环→外淡环）
    var bands = [
      [134, 158, 0.30],
      [160, 196, 0.62],
      [199, 206, 0.04],
      [209, 238, 0.44],
      [241, 247, 0.08],
      [250, 256, 0.14]
    ];

    // 用海量小颗粒绘制环带（真实土星环由无数冰粒组成）
    for (var i = 0; i < 60000; i++) {
      var ang = Math.random() * Math.PI * 2;
      var rad = 130 + Math.random() * 130; // 130~260 px
      var a = 0;
      for (var b = 0; b < bands.length; b++) {
        if (rad >= bands[b][0] && rad <= bands[b][1]) { a = bands[b][2]; break; }
      }
      if (a <= 0.01) continue;
      a *= 0.35 + Math.random() * 0.65;
      var x = cx + Math.cos(ang) * rad;
      var y = cy + Math.sin(ang) * rad;
      var sz = 0.6 + Math.random() * 1.6;
      g.fillStyle = 'rgba(200,228,255,' + a.toFixed(3) + ')';
      g.fillRect(x, y, sz, sz);
    }
    var t = new THREE.CanvasTexture(c);
    t.anisotropy = 2;
    return t;
  }

  group = new THREE.Group();

  // 星球本体
  planet = new THREE.Mesh(
    new THREE.SphereGeometry(1.9, 64, 64),
    new THREE.MeshStandardMaterial({ map: makeTexture(), roughness: 0.7, metalness: 0.05 })
  );
  group.add(planet);

  // 大气层边缘光（Fresnel 背向发光）
  atm = new THREE.Mesh(
    new THREE.SphereGeometry(2.0, 64, 64),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      uniforms: {
        uColor: { value: new THREE.Color(0x22d3ee) },
        uColor2: { value: new THREE.Color(0xa855f7) }
      },
      vertexShader: [
        'varying vec3 vNormal;',
        'varying vec3 vView;',
        'void main(){',
        '  vec4 mv = modelViewMatrix * vec4(position, 1.0);',
        '  vNormal = normalize(normalMatrix * normal);',
        '  vView = normalize(-mv.xyz);',
        '  gl_Position = projectionMatrix * mv;',
        '}'
      ].join('\n'),
      fragmentShader: [
        'uniform vec3 uColor;',
        'uniform vec3 uColor2;',
        'varying vec3 vNormal;',
        'varying vec3 vView;',
        'void main(){',
        '  float f = dot(vNormal, vView);',
        '  float intensity = pow(1.0 - abs(f), 2.6);',
        '  gl_FragColor = vec4(mix(uColor, uColor2, intensity), intensity * 0.8);',
        '}'
      ].join('\n')
    })
  );
  group.add(atm);

  // 光环（多层渐隐环带 + 冰粒颗粒，类土星）
  ring = new THREE.Mesh(
    new THREE.RingGeometry(2.2, 4.2, 128),
    new THREE.MeshBasicMaterial({
      map: makeRingTexture(), transparent: true, opacity: 0.85,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
    })
  );
  ring.rotation.x = Math.PI / 2.35;
  ring.rotation.y = 0.15;
  group.add(ring);

  // 外发光
  glow = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: makeGlow(), transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  glow.scale.set(10.5, 10.5, 1);
  group.add(glow);

  group.position.y = -0.1;
  scene.add(group);

  // 光照：主光 + 冷色补光 + 环境光（让云纹有立体明暗）
  var keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
  keyLight.position.set(5, 3, 4);
  scene.add(keyLight);
  var rimLight = new THREE.DirectionalLight(0x22d3ee, 0.7);
  rimLight.position.set(-4, -1, -3);
  scene.add(rimLight);
  scene.add(new THREE.AmbientLight(0x1a2540, 1.4));

  /* ---- 鼠标视差 ---- */
  var targetX = 0, targetY = 0, mx = 0, my = 0;
  document.addEventListener('mousemove', function (e) {
    targetX = e.clientX / innerWidth - 0.5;
    targetY = e.clientY / innerHeight - 0.5;
  }, { passive: true });

  var hero = document.querySelector('.hero');
  var heroBottom = hero ? hero.offsetTop + hero.offsetHeight : innerHeight;
  var t = 0;

  function tick() {
    t += 0.016;
    mx += (targetX - mx) * 0.06;
    my += (targetY - my) * 0.06;

    planet.rotation.y += 0.004;
    planet.rotation.x += 0.0006;
    atm.rotation.y = planet.rotation.y;
    atm.rotation.x = planet.rotation.x;
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
    W = canvas.clientWidth || 560;
    H = canvas.clientHeight || 560;
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  });
})();
