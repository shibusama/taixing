/**
 * 钛星 · 星系 + 巨型转动球体背景（galaxy.js v3）
 * 技术参考：AmitDigga/threejs-galaxy-shader（自定义 GLSL shader）
 * - 螺旋星系：15,000 颗星在 shader 内实时计算旋臂 + 随时间沿旋臂流动（自转）
 * - 黑洞引力扭曲：黑洞半径内粒子被向中心拉伸（透镜效果）+ 暗核 + 吸积环
 * - 颜色：青→紫→粉 按半径渐变，柔和圆点 + 距离淡出
 * - 巨型球体：自转 + 光环 + 大气层边缘光（Fresnel）
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
  var TOTAL_POINTS = 15000;

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

  /* ==================== 工具 ==================== */
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

  /* ==================== 螺旋星系（Shader：螺旋计算 + 流动 + 黑洞扭曲 + 渐变） ==================== */
  var VERTEX = [
    'uniform vec2 u_resolution;',
    'uniform float u_pointSize;',
    'uniform float u_totalPoints;',
    'uniform float u_time;',
    'uniform float u_blackHoleRadius;',
    'uniform vec3 u_blackHolePosition;',
    'uniform float u_spiralCount;',
    'uniform float u_turnsPerSpiral;',
    'attribute float a_index;',
    'varying float v_index;',
    'varying float vDistanceFromCamera;',
    'varying float radius;',
    'float randM1To1(vec2 co){ return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453) * 2.0 - 1.0; }',
    'vec3 getNoiseM1To1(float index){ return vec3(randM1To1(vec2(index)), randM1To1(vec2(index + 1.0)), randM1To1(vec2(index + 2.0))); }',
    'float getRand01(float index){ return randM1To1(vec2(index, index + 5.0)) / 2.0 + 0.5; }',
    'vec3 getSpiralCoordinate(float originalIndex){',
    '  v_index = originalIndex;',
    '  float totalSpirals = u_spiralCount;',
    '  float totalTurns = u_turnsPerSpiral;',
    '  float pointsPerSpiral = floor(u_totalPoints / totalSpirals);',
    '  float spiralIndex = floor(originalIndex / pointsPerSpiral);',
    '  float angleOffset = spiralIndex / totalSpirals * 3.14159 * 2.0;',
    '  float index = mod(originalIndex, pointsPerSpiral);',
    '  float timeOffset = mod(u_time, 1.0);',
    '  index = mod(index - timeOffset * pointsPerSpiral, pointsPerSpiral);',
    '  float radiusInSpiral = index / pointsPerSpiral;',
    '  radius = radiusInSpiral;',
    '  float angleInSpiral = index / pointsPerSpiral * 3.14159 * 2.0 * totalTurns + angleOffset;',
    '  vec3 noise = getNoiseM1To1(originalIndex) * 0.4;',
    '  radius *= (1.0 + noise.x / 2.0);',
    '  angleInSpiral += noise.y * 10.0 * 3.14159 / 180.0;',
    '  float planeAngle = noise.z * 5.0 * 3.14159 / 180.0;',
    '  float x = cos(angleInSpiral) * radius;',
    '  float y = sin(angleInSpiral) * radius;',
    '  float z = sin(planeAngle) * radius;',
    '  vec3 fullRandom = getNoiseM1To1(originalIndex + 22.2) * 0.02;',
    '  return vec3(x + fullRandom.x, y + fullRandom.y, z + fullRandom.z);',
    '}',
    'vec3 getCoordinateFromBlackHole(vec3 position){',
    '  vec3 vecFromCenter = position - u_blackHolePosition;',
    '  float distance = length(vecFromCenter);',
    '  if (distance > u_blackHoleRadius || distance < 0.001) return position;',
    '  float scale = u_blackHoleRadius / distance;',
    '  return u_blackHolePosition + vecFromCenter * scale;',
    '}',
    'void main(){',
    '  vec3 pos = getSpiralCoordinate(a_index);',
    '  pos = getCoordinateFromBlackHole(pos);',
    '  vec4 viewPosition = modelViewMatrix * vec4(pos, 1.0);',
    '  gl_Position = projectionMatrix * viewPosition;',
    '  vDistanceFromCamera = -viewPosition.z;',
    '  float pointScale = 4.0 * pow(getRand01(a_index + 7.0) + 0.1, 3.0) * pow(getRand01(a_index + 9.0) + 0.1, 3.0);',
    '  gl_PointSize = u_pointSize * pointScale * (u_resolution.y / 1200.0) * 2.0;',
    '}'
  ].join('\n');

  var FRAGMENT = [
    'uniform float u_fadeNear;',
    'uniform float u_fadeFar;',
    'uniform int u_colorMode;',
    'uniform vec3 u_colorPalette[8];',
    'uniform int u_paletteSize;',
    'uniform float u_colorIntensity;',
    'varying float v_index;',
    'varying float vDistanceFromCamera;',
    'varying float radius;',
    'vec3 getColorByMode(float index, float rad){',
    '  if (u_colorMode == 1) {',
    '    float t = clamp(rad, 0.0, 1.0);',
    '    int baseIndex = int(floor(t * float(u_paletteSize - 1)));',
    '    int nextIndex = min(baseIndex + 1, u_paletteSize - 1);',
    '    float blend = fract(t * float(u_paletteSize - 1));',
    '    return mix(u_colorPalette[baseIndex], u_colorPalette[nextIndex], blend);',
    '  }',
    '  return vec3(1.0);',
    '}',
    'void main(){',
    '  vec2 p = gl_PointCoord * 2.0 - 1.0;',
    '  float d = dot(p, p);',
    '  if (d > 1.0) discard;',
    '  float soft = 1.0 - smoothstep(0.0, 0.5, sqrt(d));',
    '  float cameraFade = 1.0 - smoothstep(u_fadeNear, u_fadeFar, vDistanceFromCamera);',
    '  vec3 col = getColorByMode(v_index, radius) * u_colorIntensity;',
    '  gl_FragColor = vec4(col, cameraFade * soft);',
    '}'
  ].join('\n');

  (function buildGalaxy() {
    var geo = new THREE.BufferGeometry();
    var positions = new Float32Array(TOTAL_POINTS * 3);
    var indices = new Float32Array(TOTAL_POINTS);
    for (var i = 0; i < TOTAL_POINTS; i++) {
      positions[i * 3] = positions[i * 3 + 1] = positions[i * 3 + 2] = 0;
      indices[i] = i;
    }
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('a_index', new THREE.BufferAttribute(indices, 1));
    geo.computeBoundingSphere();

    var c1 = new THREE.Color(0x22d3ee); // 青
    var c2 = new THREE.Color(0xa855f7); // 紫
    var c3 = new THREE.Color(0xec4899); // 粉
    galaxyMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        u_resolution: { value: new THREE.Vector2(W, H) },
        u_pointSize: { value: 16 },
        u_totalPoints: { value: TOTAL_POINTS },
        u_time: { value: 0 },
        u_blackHoleRadius: { value: 0.14 },
        u_blackHolePosition: { value: new THREE.Vector3(0, 0, 0) },
        u_spiralCount: { value: 3 },
        u_turnsPerSpiral: { value: 1.3 },
        u_fadeNear: { value: 40 },
        u_fadeFar: { value: 420 },
        u_colorMode: { value: 1 },
        u_colorPalette: { value: [c1, c2, c3] },
        u_paletteSize: { value: 3 },
        u_colorIntensity: { value: 1.15 }
      },
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT
    });

    galaxy = new THREE.Points(geo, galaxyMat);
    galaxy.scale.set(170, 170, 170);
    galaxy.rotation.x = Math.PI * 0.38;
    galaxy.rotation.z = Math.PI * 0.06;
    galaxy.position.set(12, 4, -120);
    scene.add(galaxy);
  })();

  /* ==================== 中心黑洞视觉（暗核 + 吸积环 + 外发光） ==================== */
  (function buildBlackHole() {
    var bh = new THREE.Group();
    var dark = new THREE.Mesh(
      new THREE.SphereGeometry(10, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x000000 })
    );
    bh.add(dark);
    bhRing = new THREE.Mesh(
      new THREE.TorusGeometry(16, 0.8, 16, 64),
      new THREE.MeshBasicMaterial({
        color: 0x22d3ee, transparent: true, opacity: 0.4,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
      })
    );
    bhRing.rotation.x = Math.PI / 2;
    bh.add(bhRing);
    var bhRing2 = new THREE.Mesh(
      new THREE.TorusGeometry(16.5, 0.4, 16, 64),
      new THREE.MeshBasicMaterial({
        color: 0xa855f7, transparent: true, opacity: 0.32,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false
      })
    );
    bhRing2.rotation.x = Math.PI / 2;
    bhRing2.rotation.z = Math.PI * 0.5;
    bh.add(bhRing2);
    var glowS = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: makeGlow(), transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false })
    );
    glowS.scale.set(48, 48, 1);
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

    // 星系：沿旋臂流动（自转）+ 鼠标微视差
    galaxyMat.uniforms.u_time.value = time * 0.045;
    galaxy.rotation.y = mx * 0.05;
    galaxy.rotation.x = Math.PI * 0.38 + my * 0.03;

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
    galaxyMat.uniforms.u_resolution.value.set(W, H);
  });
})();
