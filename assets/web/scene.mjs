import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {initAnatomyBridge} from './bridge.mjs';

// ========== 基础场景 ==========
const scene = new THREE.Scene();
scene.background = null;

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 1.05, 4.4);

const renderer = new THREE.WebGLRenderer({
  canvas: document.getElementById("three-canvas"),
  antialias: true,
  alpha: true
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(document.getElementById("canvas-wrap").clientWidth, document.getElementById("canvas-wrap").clientHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;

// 深色 ink 舞台背景：中心极暗暖灰，边缘几乎纯黑，无霓虹光晕。
const bgCanvas = document.createElement("canvas");
const bgCtx = bgCanvas.getContext("2d");
function drawBg() {
  const w = renderer.domElement.width;
  const h = renderer.domElement.height;
  bgCanvas.width = w;
  bgCanvas.height = h;
  const grad = bgCtx.createRadialGradient(w / 2, h * 0.44, 0, w / 2, h * 0.44, Math.max(w, h) * 0.72);
  grad.addColorStop(0, "#191C1F");
  grad.addColorStop(0.55, "#101214");
  grad.addColorStop(1, "#08090B");
  bgCtx.fillStyle = grad;
  bgCtx.fillRect(0, 0, w, h);

  // 极细网格：给出空间定位，不构成数据含义。
  bgCtx.strokeStyle = "rgba(255, 255, 255, 0.022)";
  bgCtx.lineWidth = 1;
  const step = Math.max(32, Math.round(w / 26));
  for (let x = 0; x < w; x += step) {
    bgCtx.beginPath(); bgCtx.moveTo(x, 0); bgCtx.lineTo(x, h); bgCtx.stroke();
  }
  for (let y = 0; y < h; y += step) {
    bgCtx.beginPath(); bgCtx.moveTo(0, y); bgCtx.lineTo(w, y); bgCtx.stroke();
  }

  renderer.domElement.style.backgroundImage = `url(${bgCanvas.toDataURL()})`;
  renderer.domElement.style.backgroundSize = "cover";
}
drawBg();

// ========== 控制器 ==========
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minPolarAngle = 0.08;
controls.maxPolarAngle = Math.PI - 0.08;
controls.minDistance = 2.6;
controls.maxDistance = 8;
controls.autoRotate = false;
controls.autoRotateSpeed = 1.2;
controls.target.set(0, 0.62, 0);
controls.enablePan = true;

// ========== 灯光 ==========
scene.add(new THREE.AmbientLight(0x9AA6B2, 0.75));
const keyLight = new THREE.DirectionalLight(0xF5F2EA, 0.9);
keyLight.position.set(3, 4, 4);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0xC9D6DC, 0.28);
fillLight.position.set(-4, 1.5, 3);
scene.add(fillLight);
const rimLight = new THREE.DirectionalLight(0x74E3C8, 0.22);
rimLight.position.set(-2, 2, -4);
scene.add(rimLight);

// ========== 系统分组 ==========
const bodyShell = new THREE.Group();
const sysSke = new THREE.Group();
const sysCir = new THREE.Group();
const sysRes = new THREE.Group();
const sysDig = new THREE.Group();
const sysNer = new THREE.Group();
const sysUri = new THREE.Group();

scene.add(bodyShell, sysSke, sysCir, sysRes, sysDig, sysNer, sysUri);

// 材质：低饱和解剖色，靠明度与结构分层，而不是发光。
const skinMat = new THREE.MeshPhongMaterial({
  color: 0x9FB3BD, transparent: true, opacity: 0.16,
  side: THREE.DoubleSide, depthWrite: false, shininess: 8
});
const organCommon = {
  transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false
};
const matSke = new THREE.MeshPhongMaterial({color: 0xD9D3C5, emissive: 0x3A382F, emissiveIntensity: 0.18, ...organCommon});
const matCir = new THREE.MeshPhongMaterial({color: 0xC98A80, emissive: 0x5A2F2A, emissiveIntensity: 0.2, ...organCommon});
const matRes = new THREE.MeshPhongMaterial({color: 0x86A9BA, emissive: 0x2C4A58, emissiveIntensity: 0.2, ...organCommon});
const matDig = new THREE.MeshPhongMaterial({color: 0xC2A678, emissive: 0x59452A, emissiveIntensity: 0.2, ...organCommon});
const matNer = new THREE.MeshPhongMaterial({color: 0xA79BC4, emissive: 0x453A5C, emissiveIntensity: 0.2, ...organCommon});
const matUri = new THREE.MeshPhongMaterial({color: 0x82AE99, emissive: 0x2C4A3C, emissiveIntensity: 0.2, ...organCommon});

// ========== 几何辅助 ==========
function sphere(group, material, x, y, z, sx, sy, sz, segments = 20) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, segments, Math.max(12, segments - 4)), material);
  mesh.position.set(x, y, z);
  mesh.scale.set(sx, sy, sz);
  group.add(mesh);
  return mesh;
}

function capsuleBetween(group, material, from, to, radius, radial = 10) {
  const a = new THREE.Vector3(...from);
  const b = new THREE.Vector3(...to);
  const direction = new THREE.Vector3().subVectors(b, a);
  const length = direction.length();
  const geometry = new THREE.CapsuleGeometry(radius, Math.max(0.001, length - radius * 2), 4, radial);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  group.add(mesh);
  return mesh;
}

function tube(group, material, points, radius, segments = 28) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)));
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, radius, 8, false), material);
  group.add(mesh);
  return mesh;
}

function stroke(group, material, points, opacity = 0.8) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(...p)));
  const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({
    color: material.color, transparent: true, opacity
  }));
  group.add(line);
  return line;
}

// ========== 人体外壳 ==========
// 躯干用旋转体而不是圆柱，肩、腰、胯有连续轮廓。
const torsoProfile = [
  [0.17, 0.02], [0.27, 0.06], [0.31, 0.20], [0.30, 0.42], [0.27, 0.62],
  [0.28, 0.86], [0.31, 1.08], [0.335, 1.30], [0.32, 1.48], [0.27, 1.60], [0.18, 1.68]
];
const torsoGeometry = new THREE.LatheGeometry(
  torsoProfile.map(([radius, y]) => new THREE.Vector2(radius, y)), 36);
const torso = new THREE.Mesh(torsoGeometry, skinMat);
bodyShell.add(torso);

// 头、颈、肩
sphere(bodyShell, skinMat, 0, 2.06, 0, 0.21, 0.245, 0.22);
capsuleBetween(bodyShell, skinMat, [0, 1.78, 0], [0, 1.94, 0], 0.075);
sphere(bodyShell, skinMat, -0.35, 1.55, 0, 0.15, 0.12, 0.13);
sphere(bodyShell, skinMat, 0.35, 1.55, 0, 0.15, 0.12, 0.13);

// 手臂：肩 → 肘 → 腕 → 手
for (const side of [-1, 1]) {
  capsuleBetween(bodyShell, skinMat, [side * 0.42, 1.52, 0], [side * 0.56, 1.18, 0.02], 0.072);
  capsuleBetween(bodyShell, skinMat, [side * 0.56, 1.18, 0.02], [side * 0.63, 0.82, 0.05], 0.058);
  sphere(bodyShell, skinMat, side * 0.64, 0.74, 0.06, 0.062, 0.085, 0.05);
}

// 胯、腿、脚
sphere(bodyShell, skinMat, 0, 0.06, 0, 0.27, 0.16, 0.19);
for (const side of [-1, 1]) {
  capsuleBetween(bodyShell, skinMat, [side * 0.17, 0.0, 0], [side * 0.19, -0.54, 0.01], 0.11);
  capsuleBetween(bodyShell, skinMat, [side * 0.19, -0.54, 0.01], [side * 0.19, -1.0, 0.02], 0.078);
  sphere(bodyShell, skinMat, side * 0.19, -1.05, 0.06, 0.075, 0.05, 0.15);
}

// ========== 骨骼系统 ==========
sphere(sysSke, matSke, 0, 2.07, 0, 0.165, 0.195, 0.175, 16);
capsuleBetween(sysSke, matSke, [0, 1.72, -0.02], [0, 0.18, -0.02], 0.028, 8);
for (let i = 0; i < 13; i++) {
  sphere(sysSke, matSke, 0, 1.66 - i * 0.115, -0.02, 0.045, 0.028, 0.038, 10);
}
for (let i = 0; i < 7; i++) {
  const rib = new THREE.Mesh(
    new THREE.TorusGeometry(0.19 + i * 0.005, 0.011, 6, 32),
    matSke);
  rib.rotation.x = Math.PI / 2;
  rib.scale.set(1.25, 1.15, 0.72);
  rib.position.set(0, 1.5 - i * 0.105, -0.01);
  sysSke.add(rib);
}
// 骨盆
const pelvisBone = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.026, 8, 28), matSke);
pelvisBone.rotation.x = Math.PI / 2;
pelvisBone.scale.set(1.15, 1.0, 0.62);
pelvisBone.position.set(0, 0.06, 0);
sysSke.add(pelvisBone);
// 四肢骨
for (const side of [-1, 1]) {
  capsuleBetween(sysSke, matSke, [side * 0.08, 1.58, 0.04], [side * 0.36, 1.55, 0.02], 0.016, 6);
  capsuleBetween(sysSke, matSke, [side * 0.42, 1.5, 0], [side * 0.55, 1.18, 0.02], 0.02, 6);
  capsuleBetween(sysSke, matSke, [side * 0.55, 1.18, 0.02], [side * 0.62, 0.83, 0.05], 0.014, 6);
  capsuleBetween(sysSke, matSke, [side * 0.16, 0.04, 0], [side * 0.18, -0.53, 0.01], 0.025, 6);
  capsuleBetween(sysSke, matSke, [side * 0.18, -0.53, 0.01], [side * 0.19, -0.98, 0.02], 0.019, 6);
  sphere(sysSke, matSke, side * 0.19, -1.05, 0.05, 0.06, 0.035, 0.13, 10);
}

// ========== 循环系统 ==========
const heart = sphere(sysCir, matCir, 0.06, 1.12, 0.12, 0.105, 0.13, 0.095);
sphere(sysCir, matCir, 0.13, 1.22, 0.10, 0.05, 0.06, 0.05);
// 主动脉弓与降主动脉
tube(sysCir, matCir, [
  [0.02, 1.22, 0.10], [0.02, 1.38, 0.08], [0.10, 1.46, 0.04],
  [0.16, 1.34, 0.0], [0.16, 1.0, -0.01], [0.15, 0.55, 0.0], [0.12, 0.18, 0.02]
], 0.018, 40);
// 腔静脉与四肢血管
for (const side of [-1, 1]) {
  stroke(sysCir, matCir, [
    [side * 0.10, 1.5, 0.02], [side * 0.22, 1.28, 0.04], [side * 0.34, 1.1, 0.06],
    [side * 0.5, 1.16, 0.04], [side * 0.58, 0.98, 0.05], [side * 0.62, 0.82, 0.06]
  ], 0.55);
  stroke(sysCir, matCir, [
    [side * 0.06, 0.2, 0.02], [side * 0.13, -0.1, 0.03], [side * 0.18, -0.5, 0.04],
    [side * 0.19, -0.9, 0.05]
  ], 0.45);
}

// ========== 呼吸系统 ==========
const lungL = sphere(sysRes, matRes, -0.19, 1.13, 0.06, 0.125, 0.235, 0.115);
const lungR = sphere(sysRes, matRes, 0.19, 1.13, 0.06, 0.125, 0.235, 0.115);
capsuleBetween(sysRes, matRes, [0, 1.58, 0.04], [0, 1.35, 0.04], 0.032);
for (const side of [-1, 1]) {
  tube(sysRes, matRes, [
    [0, 1.38, 0.05], [side * 0.08, 1.3, 0.07], [side * 0.16, 1.22, 0.07]
  ], 0.018, 16);
}

// ========== 消化系统 ==========
const liver = sphere(sysDig, matDig, 0.12, 0.66, 0.05, 0.21, 0.125, 0.15);
liver.rotation.z = 0.16;
const stomach = sphere(sysDig, matDig, -0.11, 0.60, 0.07, 0.125, 0.105, 0.095);
stomach.rotation.z = -0.3;
const intestine = new THREE.Mesh(new THREE.TorusGeometry(0.115, 0.036, 10, 40), matDig);
intestine.rotation.x = Math.PI / 2;
intestine.position.set(0, 0.3, 0.07);
sysDig.add(intestine);
const intestine2 = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.026, 8, 32), matDig);
intestine2.rotation.x = Math.PI / 2;
intestine2.rotation.z = 0.4;
intestine2.position.set(0.0, 0.2, 0.1);
sysDig.add(intestine2);
capsuleBetween(sysDig, matDig, [0, 1.45, 0.02], [0, 0.72, 0.03], 0.022, 8);

// ========== 神经系统 ==========
const brain = sphere(sysNer, matNer, 0, 2.08, 0.02, 0.15, 0.135, 0.155);
sphere(sysNer, matNer, 0, 1.98, -0.02, 0.08, 0.055, 0.06);
stroke(sysNer, matNer, [
  [0, 1.95, 0.02], [0, 1.6, 0.0], [0, 1.2, -0.01], [0, 0.8, 0.0], [0, 0.4, 0.01]
], 0.8);
for (const side of [-1, 1]) {
  stroke(sysNer, matNer, [
    [0, 1.55, 0.0], [side * 0.16, 1.3, 0.02], [side * 0.3, 1.1, 0.03],
    [side * 0.46, 1.15, 0.03], [side * 0.58, 0.95, 0.04]
  ], 0.45);
  stroke(sysNer, matNer, [
    [0, 0.6, 0.0], [side * 0.1, 0.2, 0.02], [side * 0.15, -0.3, 0.03], [side * 0.18, -0.7, 0.04]
  ], 0.4);
}

// ========== 泌尿系统 ==========
const kidneyL = sphere(sysUri, matUri, -0.19, 0.46, -0.03, 0.065, 0.095, 0.055);
const kidneyR = sphere(sysUri, matUri, 0.19, 0.46, -0.03, 0.065, 0.095, 0.055);
const bladder = sphere(sysUri, matUri, 0, 0.10, 0.07, 0.085, 0.075, 0.075);
for (const side of [-1, 1]) {
  stroke(sysUri, matUri, [
    [side * 0.19, 0.4, -0.02], [side * 0.12, 0.28, 0.03], [side * 0.04, 0.16, 0.06]
  ], 0.7);
}

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
  const value = parseFloat(e.target.value);
  skinMat.opacity = value;
  document.getElementById("skin-val").innerText = value.toFixed(2);
};

document.getElementById("resetCam").onclick = () => {
  camera.position.set(0, 1.05, 4.4);
  controls.target.set(0, 0.62, 0);
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
initAnatomyBridge({THREE, scene, camera, renderer, controls, bodyShell, skinMat,
  groups: {ske: sysSke, cir: sysCir, res: sysRes, dig: sysDig, ner: sysNer, uri: sysUri},
  organs: {heart, lungL, lungR, liver, stomach, intestine, brain, kidneyL, kidneyR, bladder}});
animate();

document.getElementById("loading").style.display = "none";
