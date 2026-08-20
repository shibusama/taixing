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

  group = new THREE.Group();

  // 星球本体
  planet = new THREE.Mesh(
    new THREE.SphereGeometry(1.9, 64, 64),
    new THREE.MeshStandardMaterial({ map: makeTexture(), roughness: 0.82, metalness: 0.06 })
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

  // 光环
  ring = new THREE.Mesh(
    new THREE.TorusGeometry(2.95, 0.05, 16, 120),
    new THREE.MeshBasicMaterial({
      color: 0x22d3ee, transparent: true, opacity: 0.25,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
    })
  );
  ring.rotation.x = Math.PI / 2.4;
  ring.rotation.y = 0.4;
  group.add(ring);

  // 外发光
  glow = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: makeGlow(), transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  glow.scale.set(10.5, 10.5, 1);
  group.add(glow);

  group.position.y = -0.1;
  scene.add(group);

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
    W = canvas.clientWidth || 560;
    H = canvas.clientHeight || 560;
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  });
})();
