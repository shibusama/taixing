/**
 * 钛星 · 星系 + 巨型转动球体背景（galaxy.js v2 - Shader 版）
 * - 螺旋星系：自定义 GLSL shader 渲染，柔光圆点 + 每颗星明暗闪烁
 * - 中心黑洞：暗核 + 吸积环 + 外发光，缓慢脉动
 * - 巨型球体：自转 + 光环 + 大气层边缘光（背向 Fresnel 发光）
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

  var renderer, scene, camera;
  var galaxy, galaxyMat, bhRing, sphere, sphereGroup, ring, atm;
  var W = innerWidth, H = innerHeight;
  var time = 0;

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

  /* ==================== 工具：生成 Canvas 纹理 ==================== */
  function makeSphereTexture() {
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
    grad.addColorStop(0, 'rgba(34,211,238,.9)');
    grad.addColorStop(0.35, 'rgba(168,85,247,.45)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  }

  /* ==================== 螺旋星系（Shader 柔光点 + 闪烁） ==================== */
  (function buildGalaxy() {
    var count = 16000;
    var arms = 5;            // 5 条旋臂，更密更戏剧
    var radius = 130;
    var spin = 2.2;          // 转数更多，旋臂更紧
    var randomness = 0.3;
    var minR = 0.34;         // 中心留黑洞空洞

    var pos = new Float32Array(count * 3);
    var col = new Float32Array(count * 3);
    var scl = new Float32Array(count);
    var pha = new Float32Array(count);
    var cIn = new THREE.Color(0xffffff);   // 内圈 白
    var cMid = new THREE.Color(0x6f9bff);  // 中圈 蓝
    var cOut = new THREE.Color(0xa855f7);  // 外圈 紫
    var tmp = new THREE.Color();

    for (var i = 0; i < count; i++) {
      // 星星大小：幂律分布 = 绝大多数细小微粒 + 少数大亮星（更细致）
      scl[i] = Math.pow(Math.random(), 2.4) * 1.6 + 0.18;
      pha[i] = Math.random() * Math.PI * 2;
      // 全部在旋臂上（从空洞外缘开始），中心留黑
      var ra = (minR + Math.random() * (1 - minR)) * radius;
      var arm = i % arms;
      var rot = (ra / radius) * spin;
      var angle = rot + arm * ((Math.PI * 2) / arms);
      var radial = 1 + Math.random() * randomness;
      pos[i * 3] = Math.cos(angle) * ra * radial;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 2.2;
      pos[i * 3 + 2] = Math.sin(angle) * ra * radial;
      var t = ra / radius;
      if (t < 0.5) tmp.copy(cIn).lerp(cMid, t / 0.5);
      else tmp.copy(cMid).lerp(cOut, (t - 0.5) / 0.5);
      col[i * 3] = tmp.r; col[i * 3 + 1] = tmp.g; col[i * 3 + 2] = tmp.b;
    }

    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
    geo.setAttribute('aScale', new THREE.BufferAttribute(scl, 1));
    geo.setAttribute('aPhase', new THREE.BufferAttribute(pha, 1));

    galaxyMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio || 1, 1.5) },
        uSize: { value: 26 }
      },
      vertexShader: [
        'uniform float uTime;',
        'uniform float uPixelRatio;',
        'uniform float uSize;',
        'attribute float aScale;',
        'attribute float aPhase;',
        'attribute vec3 aColor;',
        'varying vec3 vColor;',
        'varying float vTwinkle;',
        'void main(){',
        '  vec4 modelPos = modelMatrix * vec4(position, 1.0);',
        '  vec4 viewPos = viewMatrix * modelPos;',
        '  gl_Position = projectionMatrix * viewPos;',
        '  gl_PointSize = uSize * aScale * uPixelRatio * (240.0 / -viewPos.z);',
        '  vColor = aColor;',
        '  vTwinkle = 0.55 + 0.45 * sin(uTime * 1.4 + aPhase);',
        '}'
      ].join('\n'),
      fragmentShader: [
        'varying vec3 vColor;',
        'varying float vTwinkle;',
        'void main(){',
        '  float d = distance(gl_PointCoord, vec2(0.5));',
        '  float strength = smoothstep(0.5, 0.0, d);',
        '  strength = pow(strength, 1.6);',
        '  if (strength < 0.02) discard;',
        '  gl_FragColor = vec4(vColor * vTwinkle, strength * 0.95);',
        '}'
      ].join('\n')
    });

    galaxy = new THREE.Points(geo, galaxyMat);
    galaxy.rotation.x = Math.PI * 0.38;
    galaxy.rotation.z = Math.PI * 0.06;
    galaxy.position.set(12, 4, -120);
    scene.add(galaxy);
  })();

  /* ==================== 中心黑洞（暗核 + 吸积环 + 外发光） ==================== */
  (function buildBlackHole() {
    var bh = new THREE.Group();
    var dark = new THREE.Mesh(
      new THREE.SphereGeometry(13, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x000000 })
    );
    bh.add(dark);
    // 吸积亮环（黑洞边缘，两圈旋转）
    bhRing = new THREE.Mesh(
      new THREE.TorusGeometry(40, 0.9, 16, 128),
      new THREE.MeshBasicMaterial({
        color: 0x9db8ff, transparent: true, opacity: 0.6,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
      })
    );
    bhRing.rotation.x = Math.PI / 2;
    bh.add(bhRing);
    var bhRing2 = new THREE.Mesh(
      new THREE.TorusGeometry(42, 0.32, 16, 128),
      new THREE.MeshBasicMaterial({
        color: 0xa855f7, transparent: true, opacity: 0.42,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
      })
    );
    bhRing2.rotation.x = Math.PI / 2;
    bhRing2.rotation.z = Math.PI * 0.5;
    bh.add(bhRing2);
    var glowS = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: makeGlow(), transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false })
    );
    glowS.scale.set(88, 88, 1);
    bh.add(glowS);
    bh.position.set(12, 4, -120);
    scene.add(bh);
  })();

  /* ==================== 巨型球体（自转 + 光环 + 大气层边缘光） ==================== */
  (function buildSphere() {
    sphereGroup = new THREE.Group();
    sphere = new THREE.Mesh(
      new THREE.SphereGeometry(9, 64, 64),
      new THREE.MeshStandardMaterial({ map: makeSphereTexture(), roughness: 0.82, metalness: 0.06 })
    );
    sphereGroup.add(sphere);

    // 大气层：背向 Fresnel 发光（反向法线 + 加色混合，模拟边缘大气）
    atm = new THREE.Mesh(
      new THREE.SphereGeometry(9.55, 64, 64),
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
          '  gl_FragColor = vec4(mix(uColor, uColor2, intensity), intensity * 0.85);',
          '}'
        ].join('\n')
      })
    );
    sphereGroup.add(atm);

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

    sphereGroup.position.set(38, 1, -8);
    scene.add(sphereGroup);
  })();

  /* ==================== 灯光 ==================== */
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  var dl = new THREE.DirectionalLight(0x9fd8ff, 1.2);
  dl.position.set(6, 4, 8);
  scene.add(dl);
  var pl = new THREE.PointLight(0xa855f7, 1.2, 44);
  pl.position.set(-6, -2, 4);
  scene.add(pl);

  /* ==================== 鼠标视差 ==================== */
  var tx = 0, ty = 0, mx = 0, my = 0;
  document.addEventListener('mousemove', function (e) {
    tx = e.clientX / innerWidth - 0.5;
    ty = e.clientY / innerHeight - 0.5;
  }, { passive: true });

  function tick() {
    time += 0.016;
    mx += (tx - mx) * 0.05;
    my += (ty - my) * 0.05;

    galaxyMat.uniforms.uTime.value = time;
    galaxy.rotation.y += 0.0012 + mx * 0.02;
    galaxy.rotation.x = Math.PI * 0.38 + my * 0.02;

    bhRing.rotation.z += 0.01;
    bhRing.rotation.y += 0.004;

    sphere.rotation.y += 0.004;
    sphere.rotation.x += 0.0006;
    atm.rotation.y = sphere.rotation.y;
    atm.rotation.x = sphere.rotation.x;
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
