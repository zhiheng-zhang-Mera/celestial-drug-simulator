import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {initAnatomyBridge} from './bridge.mjs';
import {isVisible, visualStyle} from './interaction.mjs';

// Real BodyParts3D surfaces only. The upstream reference bundle is generated
// into ./data/bodyparts3d.mjs by tools/build_web_anatomy.py; the page never
// fetches anything (CSP connect-src 'none').
const els = {
  wrap: document.getElementById('canvas-wrap'),
  canvas: document.getElementById('three-canvas'),
  loading: document.getElementById('loading'),
  loadingText: document.getElementById('loading-text'),
  loadingBar: document.getElementById('loading-bar'),
  loadingDetail: document.getElementById('loading-detail'),
  status: document.getElementById('viewport-status'),
};
const started = performance.now();
let booted = false;

const REGION_NAMES = {
  brain: '大脑', heart: '心脏', lungs: '肺', liver: '肝脏', stomach: '胃',
  kidneys: '双肾', bladder: '膀胱', testes: '睾丸', uterus: '子宫',
  biceps: '肱二头肌群', triceps: '肱三头肌群', quadriceps: '股四头肌群',
  nervous: '神经系统', metabolic: '代谢相关器官', urinary: '泌尿系统',
  digestive: '消化系统', cardiovascular: '心血管系统', respiratory: '呼吸系统',
  reproductive: '生殖器官分层', muscular: '肌肉系统',
};

// Muted tissue colours. These are interface conventions, not measurements.
const TISSUE = {
  brain: 0xD2B8B1, heart: 0xC5837A, lungs: 0xD0A69C, liver: 0xB07A66,
  stomach: 0xCFA98A, kidneys: 0xAD7A6F, bladder: 0xCEBAA0, testes: 0xC49A8B,
  biceps: 0xBB7A6E, triceps: 0xB47166, quadriceps: 0xB8786C, uterus: 0xC99AA8,
};
const SYSTEM_OF = {
  brain: 'ner', heart: 'cir', lungs: 'res', liver: 'dig', stomach: 'dig',
  kidneys: 'uri', bladder: 'uri', biceps: 'mus', triceps: 'mus',
  quadriceps: 'mus', testes: 'rep', uterus: 'rep',
};
const MUSCLE_REGIONS = new Set(['biceps', 'triceps', 'quadriceps']);

function setProgress(text, percent, detail) {
  els.loadingText.textContent = text;
  els.loadingBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  if (detail) els.loadingDetail.textContent = detail;
}

function fail(message, detail) {
  els.loading.hidden = false;
  els.loading.classList.add('is-error');
  els.loadingText.textContent = message;
  els.loadingDetail.textContent = detail || '可使用舞台下方的「简化视图」回退。';
  els.status.textContent = '渲染不可用';
}

window.addEventListener('error', event => {
  if (!booted) fail('人体视图初始化失败：' + (event.message || '未知错误'),
                    '可使用舞台下方的「简化视图」回退。');
});
window.addEventListener('unhandledrejection', event => {
  if (!booted) fail('人体视图初始化失败：' + ((event.reason && event.reason.message) || '未知错误'),
                    '可使用舞台下方的「简化视图」回退。');
});

const nextFrame = () => new Promise(resolve => requestAnimationFrame(resolve));

async function boot() {
  setProgress('初始化图形…', 4);
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas: els.canvas, antialias: true, alpha: false, stencil: true,
      powerPreference: 'high-performance',
    });
  } catch (error) {
    fail('WebGL 图形初始化失败', '该设备或驱动不支持所需的 WebGL 功能；可使用「简化视图」回退。');
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.setClearColor(0x0C0D0F, 1);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0C0D0F);

  const camera = new THREE.PerspectiveCamera(34, 1, 0.05, 40);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.075;
  controls.enablePan = true;
  controls.screenSpacePanning = true;
  controls.minPolarAngle = 0.05;
  controls.maxPolarAngle = Math.PI - 0.05;
  controls.minDistance = 0.9;
  controls.maxDistance = 6.5;
  controls.rotateSpeed = 0.65;
  controls.zoomSpeed = 0.8;
  controls.panSpeed = 0.6;
  controls.autoRotateSpeed = 0.7;

  // Studio-neutral lighting: warm key, cool fill, cool rim. No coloured neon.
  scene.add(new THREE.HemisphereLight(0xFFF6EA, 0x191B1E, 1.05));
  const key = new THREE.DirectionalLight(0xFFF2E1, 1.55);
  key.position.set(2.6, 3.4, 3.0);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xC5D9E6, 0.55);
  fill.position.set(-3.2, 1.4, 1.8);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xDDEBF2, 0.7);
  rim.position.set(-1.4, 2.4, -3.2);
  scene.add(rim);

  const model = {
    root: new THREE.Group(),
    shellGroup: new THREE.Group(),
    sysGroups: {},
    regions: new Map(),
    picker: [],
    parts: [],
  };
  scene.add(model.root);
  model.root.add(model.shellGroup);
  for (const key of ['cir', 'res', 'dig', 'ner', 'uri', 'mus', 'rep']) {
    const group = new THREE.Group();
    group.name = key;
    model.sysGroups[key] = group;
    model.root.add(group);
  }

  // ------------------------------------------------------------------ shell
  // A translucent skin shell needs its own shading: standard transparent
  // materials over the ink stage either look like dark leather or, with enough
  // Fresnel, wash out the organs. This shader keeps a readable body outline by
  // putting most of the alpha in the view-dependent rim, while the interior
  // stays a light warm haze. Derivative normals avoid the upstream mesh's
  // non-manifold smooth-normal seams.
  const skinMaterial = new THREE.ShaderMaterial({
    uniforms: {
      uSkin: {value: new THREE.Color(0xFFE1BA)},
      uRim: {value: new THREE.Color(0xFFE9CB)},
      uOpacity: {value: 0.30},
    },
    vertexShader: `
      varying vec3 vViewPosition;
      void main() {
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        vViewPosition = mvPosition.xyz;
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      uniform vec3 uSkin;
      uniform vec3 uRim;
      uniform float uOpacity;
      varying vec3 vViewPosition;
      void main() {
        // Per-fragment geometric normal: stable even where the source mesh's
        // welded vertex normals are inconsistent. Alpha stays constant so
        // overlapping patches can never accumulate into streaks; the warm rim
        // is added to colour only, which keeps the silhouette readable.
        vec3 normal = normalize(cross(dFdx(vViewPosition), dFdy(vViewPosition)));
        vec3 viewDir = normalize(-vViewPosition);
        vec3 keyDir = normalize(vec3(0.35, 0.55, 0.75));
        vec3 fillDir = normalize(vec3(-0.60, 0.10, 0.62));
        float facing = abs(dot(normal, viewDir));
        float shade = 0.62 + 0.28 * abs(dot(normal, keyDir)) + 0.12 * abs(dot(normal, fillDir));
        float rim = pow(1.0 - facing, 3.0);
        vec3 color = uSkin * shade + uRim * rim * 0.45;
        gl_FragColor = vec4(pow(max(color, vec3(0.0)), vec3(1.0 / 2.2)), uOpacity);
      }
    `,
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false,
    depthTest: true,
    // The clustered skin contains coincident patches. Draw the shell at most
    // once per pixel (stencil ref 1) so transparency never accumulates into
    // streaks; the geometric first hit wins.
    stencilWrite: true,
    stencilRef: 1,
    stencilFunc: THREE.NotEqualStencilFunc,
    stencilFail: THREE.KeepStencilOp,
    stencilZFail: THREE.KeepStencilOp,
    stencilZPass: THREE.ReplaceStencilOp,
  });
  skinMaterial.renderOrder = 10;

  const stageState = {
    effects: {},
    selected: 'brain',
    members: [],
    regions: [],
  };
  let systemColors = true;
  let organOpacity = 0.82;
  let glow = 1.0;
  let reproChoice = 'none';
  let homeTarget = new THREE.Vector3(0, 0.85, 0);
  let fitDistance = 2.95;
  let height = 1.64;
  const layerState = {shell: true, cir: true, res: true, dig: true, ner: true, uri: true, mus: true, rep: true};
  let outlineGroup = null;
  let lastStatusAt = 0;

  function regionMaterial(region, baseColor, opacity) {
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(baseColor),
      roughness: MUSCLE_REGIONS.has(region) ? 0.72 : 0.58,
      metalness: 0.0,
      emissive: new THREE.Color(0x000000),
      emissiveIntensity: 0,
      transparent: true,
      opacity,
      side: THREE.DoubleSide,
      depthWrite: true,
    });
    return material;
  }

  // --------------------------------------------------------------- geometry
  let anatomy;
  try {
    setProgress('读取本地网格数据…', 10);
    anatomy = (await import('./data/bodyparts3d.mjs')).ANATOMY;
  } catch (error) {
    fail('人体网格数据未能加载',
         'assets/web/data/bodyparts3d.mjs 不可读；请使用「简化视图」回退。');
    return;
  }
  height = anatomy.height;
  homeTarget = new THREE.Vector3(0, height * 0.515, 0);
  fitDistance = (height * 1.025) / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));

  setProgress('构建真实体表与器官网格…', 22, 'BodyParts3D · 真实三角网格');
  await nextFrame();
  for (const part of anatomy.parts) {
    const region = part.region;
    if (!model.regions.has(region)) {
      const group = new THREE.Group();
      group.name = region;
      model.regions.set(region, {
        region, group, parts: [], baseColor: TISSUE[region] || 0xB9AFA4,
        system: SYSTEM_OF[region] || 'rep', schematic: false, material: null,
      });
    }
    const info = model.regions.get(region);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(part.positions, 3));
    geometry.setIndex(part.indices);
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();

    if (region === 'shell') {
      const mesh = new THREE.Mesh(geometry, skinMaterial);
      mesh.name = 'body-surface';
      mesh.renderOrder = 10;
      model.shellGroup.add(mesh);
      info.parts.push(mesh);
      continue;
    }

    if (!info.material) {
      const opacity = MUSCLE_REGIONS.has(region) ? organOpacity * 0.72 : organOpacity;
      info.material = regionMaterial(region, info.baseColor, opacity);
    }
    const mesh = new THREE.Mesh(geometry, info.material);
    mesh.name = `${region}-part`;
    mesh.userData.region = region;
    mesh.renderOrder = 2;
    info.group.add(mesh);
    info.parts.push(mesh);
    model.picker.push(mesh);
    model.parts.push(mesh);
  }

  // Place organ groups under their system layers.
  for (const info of model.regions.values()) {
    if (info.region === 'shell') continue;
    model.sysGroups[info.system].add(info.group);
  }

  // ------------------------------------------------------------- schematic
  // The source bundle has no uterus. Keep the existing supplement entry but
  // render it as an explicitly labelled schematic: translucent body plus a
  // wireframe overlay, never described as source geometry.
  function buildUterusSchematic() {
    const bladder = model.regions.get('bladder');
    if (!bladder) return null;
    const center = new THREE.Box3().setFromObject(bladder.group).getCenter(new THREE.Vector3());
    const anchor = center.clone().add(new THREE.Vector3(0, 0.055, -0.012));
    const group = new THREE.Group();
    group.name = 'uterus';
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(TISSUE.uterus), roughness: 0.68, metalness: 0,
      transparent: true, opacity: 0.42, side: THREE.DoubleSide, depthWrite: false,
    });
    const wireMaterial = new THREE.MeshBasicMaterial({
      color: 0xE3AEBC, wireframe: true, transparent: true, opacity: 0.22,
      depthWrite: false,
    });
    const meshes = [];
    function addPart(geometry, position, scale) {
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(position);
      mesh.scale.copy(scale);
      mesh.userData.region = 'uterus';
      mesh.userData.schematic = true;
      group.add(mesh);
      meshes.push(mesh);
      return mesh;
    }
    addPart(new THREE.SphereGeometry(1, 20, 14), anchor, new THREE.Vector3(0.040, 0.056, 0.032));
    addPart(new THREE.SphereGeometry(1, 14, 10),
      anchor.clone().add(new THREE.Vector3(0, -0.052, 0.002)),
      new THREE.Vector3(0.017, 0.021, 0.016));
    for (const side of [-1, 1]) {
      const start = anchor.clone().add(new THREE.Vector3(side * 0.016, 0.028, 0));
      const mid = anchor.clone().add(new THREE.Vector3(side * 0.060, 0.040, -0.006));
      const end = anchor.clone().add(new THREE.Vector3(side * 0.082, 0.036, -0.004));
      const curve = new THREE.CatmullRomCurve3([start, mid, end]);
      addPart(new THREE.TubeGeometry(curve, 18, 0.0032, 6, false),
        new THREE.Vector3(), new THREE.Vector3(1, 1, 1));
      addPart(new THREE.SphereGeometry(1, 12, 9), end, new THREE.Vector3(0.011, 0.009, 0.010));
    }
    for (const mesh of meshes) {
      const wire = new THREE.Mesh(mesh.geometry, wireMaterial);
      wire.userData.region = 'uterus';
      wire.userData.schematic = true;
      mesh.add(wire);
    }
    model.sysGroups.rep.add(group);
    const info = {
      region: 'uterus', group, parts: meshes, baseColor: TISSUE.uterus,
      system: 'rep', schematic: true, material,
    };
    model.regions.set('uterus', info);
    for (const mesh of meshes) model.picker.push(mesh);
    return group;
  }
  buildUterusSchematic();

  // ------------------------------------------------------------ interaction
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function pick(clientX, clientY) {
    const rect = renderer.domElement.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    pointer.set(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    const visible = model.picker.filter(isVisible);
    const hit = raycaster.intersectObjects(visible, false)[0];
    if (!hit) return null;
    const info = model.regions.get(hit.object.userData.region);
    if (!info) return null;
    return {
      region: info.region,
      name: REGION_NAMES[info.region] || info.region,
      schematic: info.schematic,
    };
  }

  // ------------------------------------------------------------------ views
  function viewPosition(name) {
    const distance = fitDistance;
    if (name === 'back') return new THREE.Vector3(0, homeTarget.y, -distance);
    return new THREE.Vector3(0, homeTarget.y, distance);
  }

  let tweenToken = 0;
  function moveTo(viewName) {
    controls.autoRotate = false;
    const token = ++tweenToken;
    const toPosition = viewPosition(viewName);
    const toTarget = homeTarget.clone();
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      camera.position.copy(toPosition);
      controls.target.copy(toTarget);
      controls.update();
      return;
    }
    const fromPosition = camera.position.clone();
    const fromTarget = controls.target.clone();
    const duration = 260;
    const t0 = performance.now();
    function step(now) {
      if (token !== tweenToken) return;
      const k = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - k, 3);
      camera.position.lerpVectors(fromPosition, toPosition, eased);
      controls.target.lerpVectors(fromTarget, toTarget, eased);
      controls.update();
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function resize() {
    const width = Math.max(1, els.wrap.clientWidth);
    const heightPx = Math.max(1, els.wrap.clientHeight);
    renderer.setSize(width, heightPx);
    camera.aspect = width / heightPx;
    camera.updateProjectionMatrix();
  }
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(els.wrap);
  resize();

  camera.position.copy(viewPosition('front'));
  controls.target.copy(homeTarget);
  controls.update();

  // ---------------------------------------------------------- state painting
  const scratchColor = new THREE.Color();
  const accentColor = new THREE.Color(0x74E3C8);
  const focusColor = new THREE.Color(0xBFE8DF);

  function applyHighlight() {
    for (const info of model.regions.values()) {
      if (info.region === 'shell' || !info.material) continue;
      const style = requireStyle(info.region);
      const isSelected = info.region === stageState.selected;
      const isMember = Array.isArray(stageState.members) && stageState.members.includes(info.region);
      const material = info.material;
      material.color.setHex(info.baseColor);
      if (!systemColors && !style.effect) {
        material.color.setHex(MUSCLE_REGIONS.has(info.region) ? 0x8B9AA1 : 0x9FB8CC);
      }
      if (style.effect) {
        scratchColor.setHex(style.color);
        material.color.lerp(scratchColor, 0.32);
      }
      if (isSelected || isMember) material.color.lerp(focusColor, 0.14);
      material.emissive.setHex(0x000000);
      material.emissiveIntensity = 0;
      // A faint self-tint keeps organs readable behind translucent skin even
      // when the room lighting is dim; evidence/selection replaces it.
      material.emissive.copy(material.color).multiplyScalar(0.06);
      material.emissiveIntensity = 1;
      if (style.effect) {
        material.emissive.setHex(style.color);
        material.emissiveIntensity = 0.18 * glow;
      }
      if (isMember && !style.effect) {
        material.emissive.setHex(0x9FD8CE);
        material.emissiveIntensity = 0.07 * glow;
      }
      if (isSelected) {
        material.emissive.setHex(0x74E3C8);
        material.emissiveIntensity = Math.max(material.emissiveIntensity, 0.10 * glow);
      }
      material.opacity = MUSCLE_REGIONS.has(info.region)
        ? Math.min(0.9, organOpacity * 0.52)
        : organOpacity;
      material.needsUpdate = true;
    }
    updateOutlineMaterial();
  }

  // visualStyle is the single, tested source of evidence colour semantics.
  function requireStyle(region) {
    return visualStyle(region, stageState, systemColors, model.regions.get(region).baseColor);
  }

  function clearOutline() {
    if (!outlineGroup) return;
    scene.remove(outlineGroup);
    outlineGroup.traverse(object => {
      if (object.isMesh) {
        object.geometry.dispose();
        object.material.dispose();
      }
    });
    outlineGroup = null;
  }

  function buildOutline() {
    clearOutline();
    const focus = new Set();
    if (model.regions.has(stageState.selected)) focus.add(stageState.selected);
    for (const member of stageState.members || []) {
      if (model.regions.has(member)) focus.add(member);
    }
    if (!focus.size) return;
    outlineGroup = new THREE.Group();
    outlineGroup.name = 'selection-outline';
    for (const region of focus) {
      const info = model.regions.get(region);
      if (!info || info.schematic) continue;
      for (const mesh of info.parts) {
        if (!mesh.geometry.boundingSphere) mesh.geometry.computeBoundingSphere();
        const center = mesh.geometry.boundingSphere.center.clone();
        const geometry = mesh.geometry.clone();
        geometry.translate(-center.x, -center.y, -center.z);
        const material = new THREE.MeshBasicMaterial({
          color: 0x74E3C8,
          transparent: true,
          opacity: 0.16,
          side: THREE.BackSide,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        });
        const hull = new THREE.Mesh(geometry, material);
        hull.position.copy(center);
        hull.scale.setScalar(1.035);
        hull.renderOrder = 3;
        outlineGroup.add(hull);
      }
    }
    scene.add(outlineGroup);
    updateOutlineMaterial();
  }

  function updateOutlineMaterial() {
    if (!outlineGroup) return;
    const opacity = Math.min(0.6, 0.30 * Math.max(0.35, glow));
    outlineGroup.traverse(object => {
      if (object.isMesh && object.material) object.material.opacity = opacity;
    });
  }

  function syncLayerVisibility() {
    model.shellGroup.visible = layerState.shell;
    for (const key of ['cir', 'res', 'dig', 'ner', 'uri', 'mus', 'rep']) {
      model.sysGroups[key].visible = layerState[key];
    }
    if (model.sysGroups.rep.visible) {
      for (const region of ['testes', 'uterus']) {
        const info = model.regions.get(region);
        if (!info) continue;
        info.group.visible = reproChoice === 'both' || reproChoice === region;
      }
    }
  }

  function syncStatus(force) {
    const now = performance.now();
    if (!force && now - lastStatusAt < 140) return;
    lastStatusAt = now;
    const dx = camera.position.x - controls.target.x;
    const dz = camera.position.z - controls.target.z;
    let facing = '正面';
    if (dz < -Math.abs(dx) * 1.2) facing = '背面';
    else if (Math.abs(dx) > Math.abs(dz)) facing = '侧面';
    const distance = camera.position.distanceTo(controls.target);
    const zoom = Math.round((fitDistance / distance) * 100);
    els.status.textContent = `${facing} · ${zoom}%`;
  }
  controls.addEventListener('change', () => syncStatus(false));

  const stage = {
    THREE, scene, camera, renderer, controls, model,
    get height() { return height; },
    get fitDistance() { return fitDistance; },
    get systemColors() { return systemColors; },
    get layerState() { return {...layerState}; },
    get reproChoice() { return reproChoice; },
    regionName(region) { return REGION_NAMES[region] || region; },
    isSchematic(region) { return !!(model.regions.get(region) || {}).schematic; },
    pick,
    setLayer(key, visible) {
      if (!(key in layerState)) return;
      layerState[key] = !!visible;
      syncLayerVisibility();
    },
    setRepro(choice) {
      reproChoice = ['none', 'testes', 'uterus', 'both'].includes(choice) ? choice : 'none';
      syncLayerVisibility();
    },
    setSkinOpacity(value) {
      skinMaterial.uniforms.uOpacity.value = value;
    },
    setOrganOpacity(value) {
      organOpacity = value;
      applyHighlight();
    },
    setGlow(value) {
      glow = value;
      applyHighlight();
    },
    setSystemColors(value) {
      systemColors = !!value;
      applyHighlight();
    },
    setView(name) { moveTo(name === 'back' ? 'back' : 'front'); },
    toggleAutoRotate() {
      controls.autoRotate = !controls.autoRotate;
      return controls.autoRotate;
    },
    get autoRotating() { return controls.autoRotate; },
    applyState(state) {
      const previous = stageState.selected;
      stageState.effects = state.effects || {};
      stageState.selected = state.selected || previous;
      stageState.members = state.members || [];
      stageState.regions = state.regions || stageState.regions;
      // Reveal the layer for the selected region / related structures.
      const reveal = new Set([stageState.selected, ...stageState.members,
        ...Object.keys(stageState.effects)]);
      for (const region of reveal) {
        const info = model.regions.get(region);
        if (info && info.system) layerState[info.system] = true;
        if (region === 'testes' || region === 'uterus') {
          reproChoice = region === 'testes' ? 'testes' : 'uterus';
        }
      }
      if (stageState.selected === 'reproductive' ||
          (stageState.members || []).includes('testes') && (stageState.members || []).includes('uterus')) {
        reproChoice = 'both';
      }
      syncLayerVisibility();
      applyHighlight();
      buildOutline();
      if (previous !== stageState.selected) {
        if (stageState.selected === 'triceps') moveTo('back');
        else if (stageState.selected === 'biceps' || stageState.selected === 'quadriceps') moveTo('front');
      }
      syncStatus(true);
    },
    resize, syncStatus,
  };

  // ---------------------------------------------------------------- bridge
  initAnatomyBridge({THREE, scene, camera, renderer, controls, stage});

  // First frame evidence: render once before reporting ready.
  renderer.render(scene, camera);
  const firstFrame = Math.round(performance.now() - started);
  const shellPart = anatomy.parts.find(part => part.region === 'shell') || {positions: []};
  console.log(`[anatomy] first frame ${firstFrame}ms · parts=${anatomy.parts.length} · ` +
    `shellVerts=${shellPart.positions.length / 3} · height=${height}m · ` +
    `source=${anatomy.sourceCommit}`);
  els.loadingBar.style.width = '100%';
  els.loading.hidden = true;
  booted = true;
  els.status.textContent = '全身 · 100%';
  els.canvas.focus({preventScroll: true});

  window.addEventListener('resize', resize);
  els.canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    fail('图形上下文已丢失', '请重载本模块，或使用「简化视图」回退。');
  });

  function animate() {
    requestAnimationFrame(animate);
    if (document.hidden) return;
    controls.update();
    renderer.render(scene, camera);
  }
  animate();
}

boot().catch(error => {
  console.error('[anatomy] boot failed', error);
  fail('人体视图初始化失败', (error && error.message) || '未知错误；可使用「简化视图」回退。');
});
