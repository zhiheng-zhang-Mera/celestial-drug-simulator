import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {initAnatomyBridge} from './bridge.mjs';
  // ========== 基础场景 ==========
  const scene = new THREE.Scene();
  scene.background = null;

  const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 1.6, 4.2);

  const renderer = new THREE.WebGLRenderer({
    canvas: document.getElementById("three-canvas"),
    antialias: true,
    alpha: true
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(document.getElementById("canvas-wrap").clientWidth, document.getElementById("canvas-wrap").clientHeight);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;

  // 蓝色 X-Ray 背景层
  const bgCanvas = document.createElement("canvas");
  const bgCtx = bgCanvas.getContext("2d");
  function drawBg() {
    const w = renderer.domElement.width;
    const h = renderer.domElement.height;
    bgCanvas.width = w;
    bgCanvas.height = h;
    const grad = bgCtx.createRadialGradient(w/2, h/2, 0, w/2, h/2, Math.max(w, h) * 0.7);
    grad.addColorStop(0, "#154b8c");
    grad.addColorStop(0.55, "#0b2a5a");
    grad.addColorStop(1, "#031024");
    bgCtx.fillStyle = grad;
    bgCtx.fillRect(0, 0, w, h);

    // 扫描线
    bgCtx.strokeStyle = "rgba(120, 200, 255, 0.05)";
    bgCtx.lineWidth = 1;
    for (let y = 0; y < h; y += 18) {
      bgCtx.beginPath();
      bgCtx.moveTo(0, y);
      bgCtx.lineTo(w, y);
      bgCtx.stroke();
    }
    // 中心光晕
    const glow = bgCtx.createRadialGradient(w/2, h/2, 0, w/2, h/2, Math.min(w, h) * 0.4);
    glow.addColorStop(0, "rgba(120, 200, 255, 0.25)");
    glow.addColorStop(1, "rgba(120, 200, 255, 0)");
    bgCtx.fillStyle = glow;
    bgCtx.fillRect(0, 0, w, h);

    renderer.domElement.style.backgroundImage = `url(${bgCanvas.toDataURL()})`;
    renderer.domElement.style.backgroundSize = "cover";
  }
  drawBg();

  // ========== 控制器：仅横向旋转 ==========
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minPolarAngle = 0.08;
  controls.maxPolarAngle = Math.PI - 0.08;
  controls.minDistance = 2.2;
  controls.maxDistance = 7;
  controls.autoRotate = false;
  controls.autoRotateSpeed = 1.2;
  controls.target.set(0, 0.95, 0);
  controls.enablePan = true;

  // ========== 灯光 ==========
  scene.add(new THREE.AmbientLight(0x88bbff, 0.55));
  const keyLight = new THREE.DirectionalLight(0xaad8ff, 0.9);
  keyLight.position.set(3, 4, 3);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0x5599ff, 0.5);
  rimLight.position.set(-3, 2, -3);
  scene.add(rimLight);

  // ========== 系统分组与深度分层 ==========
  // 层级原则：外壳最外；骨骼最内；器官按前后层级错开
  const LAYER = {
    SKIN: 0,
    ORGAN_FRONT: 0.02,
    ORGAN_MIDDLE: 0,
    ORGAN_BACK: -0.02,
    SKELETON: -0.04
  };

  const bodyShell = new THREE.Group();
  const sysSke = new THREE.Group();
  const sysCir = new THREE.Group();
  const sysRes = new THREE.Group();
  const sysDig = new THREE.Group();
  const sysNer = new THREE.Group();
  const sysUri = new THREE.Group();

  scene.add(bodyShell);
  scene.add(sysSke);
  scene.add(sysCir);
  scene.add(sysRes);
  scene.add(sysDig);
  scene.add(sysNer);
  scene.add(sysUri);

  // 材质
  const skinMat = new THREE.MeshPhongMaterial({
    color: 0x88b8dd,
    transparent: true,
    opacity: 0.20,
    side: THREE.DoubleSide,
    depthWrite: false
  });

  const organCommon = {
    transparent: true,
    opacity: 0.85,
    side: THREE.DoubleSide,
    depthWrite: false
  };

  const matSke = new THREE.MeshPhongMaterial({ color: 0xe9f6ff, emissive: 0x7faad6, emissiveIntensity: 0.4, ...organCommon });
  const matCir = new THREE.MeshPhongMaterial({ color: 0xff5566, emissive: 0xff2233, emissiveIntensity: 1.2, ...organCommon });
  const matRes = new THREE.MeshPhongMaterial({ color: 0x55ddff, emissive: 0x2299dd, emissiveIntensity: 1.2, ...organCommon });
  const matDig = new THREE.MeshPhongMaterial({ color: 0xffbb55, emissive: 0xdd9922, emissiveIntensity: 1.1, ...organCommon });
  const matNer = new THREE.MeshPhongMaterial({ color: 0xbb77ff, emissive: 0x8833dd, emissiveIntensity: 1.3, ...organCommon });
  const matUri = new THREE.MeshPhongMaterial({ color: 0x66ddaa, emissive: 0x22bb88, emissiveIntensity: 1.1, ...organCommon });

  // ========== 透明人体外壳 ==========
  const bodyGeo = new THREE.CylinderGeometry(0.55, 0.4, 1.8, 24, 4, true);
  const bodyMesh = new THREE.Mesh(bodyGeo, skinMat);
  bodyMesh.position.y = 1.0;
  bodyShell.add(bodyMesh);

  // 头部轮廓
  const headGeo = new THREE.SphereGeometry(0.24, 20, 20);
  const head = new THREE.Mesh(headGeo, skinMat);
  head.position.set(0, 2.1, 0);
  bodyShell.add(head);

  // 手臂轮廓
  const armGeo = new THREE.CylinderGeometry(0.06, 0.04, 1.4, 12);
  const armL = new THREE.Mesh(armGeo, skinMat);
  armL.position.set(-0.72, 1.15, 0);
  armL.rotation.z = 0.35;
  bodyShell.add(armL);
  const armR = new THREE.Mesh(armGeo, skinMat);
  armR.position.set(0.72, 1.15, 0);
  armR.rotation.z = -0.35;
  bodyShell.add(armR);

  // ========== 骨骼系统（最内层） ==========
  function addBone(group, geometry, x, y, z, mat) {
    const m = new THREE.Mesh(geometry, mat);
    m.position.set(x, y, z + LAYER.SKELETON);
    group.add(m);
    return m;
  }

  addBone(sysSke, new THREE.CylinderGeometry(0.04, 0.04, 1.6, 12), 0, 1.0, 0, matSke);       // 躯干中轴
  addBone(sysSke, new THREE.CylinderGeometry(0.03, 0.03, 0.6, 12), 0, 1.85, 0, matSke);     // 颈
  addBone(sysSke, new THREE.SphereGeometry(0.18, 16, 16), 0, 2.15, 0, matSke);                // 颅骨
  addBone(sysSke, new THREE.CylinderGeometry(0.025, 0.02, 1.3, 10), -0.55, 1.2, 0, matSke); // 左臂
  addBone(sysSke, new THREE.CylinderGeometry(0.025, 0.02, 1.3, 10), 0.55, 1.2, 0, matSke);  // 右臂
  addBone(sysSke, new THREE.CylinderGeometry(0.035, 0.03, 0.8, 12), -0.18, 0.3, 0, matSke);  // 左股骨
  addBone(sysSke, new THREE.CylinderGeometry(0.035, 0.03, 0.8, 12), 0.18, 0.3, 0, matSke);   // 右股骨

  // ========== 循环系统（中层靠前） ==========
  const heart = new THREE.Mesh(new THREE.SphereGeometry(0.18, 20, 20), matCir);
  heart.position.set(0, 0.45, 0.4 + LAYER.ORGAN_FRONT);
  sysCir.add(heart);

  // 主动脉弓
  const archCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.15, 0.6, 0.4 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0, 0.82, 0.42 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0.18, 0.6, 0.4 + LAYER.ORGAN_FRONT)
  ]);
  const arch = new THREE.Mesh(new THREE.TubeGeometry(archCurve, 32, 0.022, 12, false), matCir);
  sysCir.add(arch);

  // 躯干血管网格
  function makeVeinLines(points, mat) {
    const g = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(g, new THREE.LineBasicMaterial({ color: mat.color, transparent: true, opacity: 0.75 }));
    return line;
  }

  const veinL = makeVeinLines([
    new THREE.Vector3(-0.22, 1.3, 0.35 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(-0.18, 0.9, 0.38 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(-0.14, 0.5, 0.4 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(-0.1, 0.1, 0.42 + LAYER.ORGAN_FRONT)
  ], matCir);
  const veinR = makeVeinLines([
    new THREE.Vector3(0.22, 1.3, 0.35 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0.18, 0.9, 0.38 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0.14, 0.5, 0.4 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0.1, 0.1, 0.42 + LAYER.ORGAN_FRONT)
  ], matCir);
  sysCir.add(veinL, veinR);

  // 手臂血管
  const armVeinL = makeVeinLines([
    new THREE.Vector3(-0.45, 1.5, 0.32 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(-0.62, 1.15, 0.3 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(-0.74, 0.8, 0.28 + LAYER.ORGAN_FRONT)
  ], matCir);
  const armVeinR = makeVeinLines([
    new THREE.Vector3(0.45, 1.5, 0.32 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0.62, 1.15, 0.3 + LAYER.ORGAN_FRONT),
    new THREE.Vector3(0.74, 0.8, 0.28 + LAYER.ORGAN_FRONT)
  ], matCir);
  sysCir.add(armVeinL, armVeinR);

  // ========== 呼吸系统（中层） ==========
  const lungL = new THREE.Mesh(new THREE.SphereGeometry(0.23, 20, 20), matRes);
  lungL.scale.set(0.85, 1.15, 0.9);
  lungL.position.set(-0.3, 0.5, 0.3 + LAYER.ORGAN_MIDDLE);
  sysRes.add(lungL);

  const lungR = new THREE.Mesh(new THREE.SphereGeometry(0.23, 20, 20), matRes);
  lungR.scale.set(0.85, 1.15, 0.9);
  lungR.position.set(0.3, 0.5, 0.3 + LAYER.ORGAN_MIDDLE);
  sysRes.add(lungR);

  const trachea = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.35, 12), matRes);
  trachea.position.set(0, 0.85, 0.35 + LAYER.ORGAN_MIDDLE);
  sysRes.add(trachea);

  // ========== 消化系统（深层靠后） ==========
  const liver = new THREE.Mesh(new THREE.SphereGeometry(0.21, 20, 20), matDig);
  liver.scale.set(1.2, 0.85, 0.9);
  liver.position.set(0.28, 0.12, 0.2 + LAYER.ORGAN_BACK);
  sysDig.add(liver);

  const stomach = new THREE.Mesh(new THREE.SphereGeometry(0.16, 20, 20), matDig);
  stomach.position.set(-0.18, 0.08, 0.22 + LAYER.ORGAN_BACK);
  sysDig.add(stomach);

  const intestine = new THREE.Mesh(new THREE.TorusGeometry(0.14, 0.04, 12, 40), matDig);
  intestine.position.set(0, -0.08, 0.18 + LAYER.ORGAN_BACK);
  intestine.rotation.x = Math.PI / 2;
  sysDig.add(intestine);

  // ========== 神经系统（深层） ==========
  const brain = new THREE.Mesh(new THREE.SphereGeometry(0.22, 20, 20), matNer);
  brain.position.set(0, 2.12, 0.15 + LAYER.ORGAN_BACK);
  sysNer.add(brain);

  const nerve = makeVeinLines([
    new THREE.Vector3(0, 1.95, 0.18 + LAYER.ORGAN_BACK),
    new THREE.Vector3(0, 1.4, 0.2 + LAYER.ORGAN_BACK),
    new THREE.Vector3(0, 0.8, 0.22 + LAYER.ORGAN_BACK),
    new THREE.Vector3(0, 0.2, 0.24 + LAYER.ORGAN_BACK)
  ], matNer);
  sysNer.add(nerve);

  // ========== 泌尿系统（深层） ==========
  const kidneyL = new THREE.Mesh(new THREE.SphereGeometry(0.13, 18, 18), matUri);
  kidneyL.position.set(-0.28, -0.1, 0.18 + LAYER.ORGAN_BACK);
  sysUri.add(kidneyL);

  const kidneyR = new THREE.Mesh(new THREE.SphereGeometry(0.13, 18, 18), matUri);
  kidneyR.position.set(0.28, -0.1, 0.18 + LAYER.ORGAN_BACK);
  sysUri.add(kidneyR);

  const bladder = new THREE.Mesh(new THREE.SphereGeometry(0.1, 16, 16), matUri);
  bladder.position.set(0, -0.38, 0.16 + LAYER.ORGAN_BACK);
  sysUri.add(bladder);

  // ========== 器官信息映射 ==========
  const organMap = {
    heart:    { name: "心脏", system: "循环系统", layer: "中层靠前", desc: "血液循环动力器官，监测心率、血压、心输出量。" },
    lungL:    { name: "左肺", system: "呼吸系统", layer: "中层", desc: "气体交换器官，关注血氧饱和度、通气效率。" },
    lungR:    { name: "右肺", system: "呼吸系统", layer: "中层", desc: "气体交换器官，关注血氧饱和度、通气效率。" },
    liver:    { name: "肝脏", system: "消化系统", layer: "深层靠后", desc: "代谢与解毒器官，关注转氨酶、胆红素等指标。" },
    stomach:  { name: "胃", system: "消化系统", layer: "深层靠后", desc: "消化器官，关注胃酸水平与胃动力。" },
    intestine:{ name: "肠道", system: "消化系统", layer: "深层靠后", desc: "营养吸收与排泄通道，关注蠕动与通畅状态。" },
    brain:    { name: "大脑", system: "神经系统", layer: "深层", desc: "神经中枢，关注脑电活动与血氧供应。" },
    kidneyL:  { name: "左肾", system: "泌尿系统", layer: "深层", desc: "泌尿器官，关注肌酐、尿酸与滤过功能。" },
    kidneyR:  { name: "右肾", system: "泌尿系统", layer: "深层", desc: "泌尿器官，关注肌酐、尿酸与滤过功能。" },
    bladder:  { name: "膀胱", system: "泌尿系统", layer: "深层", desc: "储尿器官，关注容量与排尿功能。" }
  };

  // ========== UI 绑定 ==========
  const organMats = [matSke, matCir, matRes, matDig, matNer, matUri];

  document.getElementById("sys-skin").onchange = e => bodyShell.visible = e.target.checked;
  document.getElementById("sys-ske").onchange = e => sysSke.visible = e.target.checked;
  document.getElementById("sys-cir").onchange = e => sysCir.visible = e.target.checked;
  document.getElementById("sys-res").onchange = e => sysRes.visible = e.target.checked;
  document.getElementById("sys-dig").onchange = e => sysDig.visible = e.target.checked;
  document.getElementById("sys-ner").onchange = e => sysNer.visible = e.target.checked;
  document.getElementById("sys-uri").onchange = e => sysUri.visible = e.target.checked;

  document.getElementById("skin-opacity").oninput = e => {
    const v = parseFloat(e.target.value);
    skinMat.opacity = v;
    document.getElementById("skin-val").innerText = v.toFixed(2);
  };

  document.getElementById("resetCam").onclick = () => {
    camera.position.set(0, 1.6, 4.2);
    controls.target.set(0, 0.95, 0);
    controls.update();
  };

  document.getElementById("autoRotate").onclick = (e) => {
    controls.autoRotate = !controls.autoRotate;
    e.target.innerText = controls.autoRotate ? "停止旋转" : "自动旋转";
  };

  // ========== 自适应 ==========
  window.addEventListener("resize", () => {
    const wrap = document.getElementById("canvas-wrap");
    camera.aspect = wrap.clientWidth / wrap.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
    drawBg();
  });

  // ========== 渲染循环 ==========
  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  window.dispatchEvent(new Event('resize'));
  initAnatomyBridge({THREE,scene,camera,renderer,controls,bodyShell,skinMat,
    groups:{ske:sysSke,cir:sysCir,res:sysRes,dig:sysDig,ner:sysNer,uri:sysUri},
    organs:{heart,lungL,lungR,liver,stomach,intestine,brain,kidneyL,kidneyR,bladder}});
  animate();

  document.getElementById("loading").style.display = "none";
