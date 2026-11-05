"""Rebuild the embedded reference with explicit compatibility/bridge adaptations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'assets/reference/doubao_html_20261105_155000.html').read_text(encoding='utf-8')
page, scene = source.split('<script src=', 1)
scene = scene.split('<script>\n', 1)[1].split('</script>', 1)[0]
scene = scene.replace('new THREE.OrbitControls(', 'new OrbitControls(')
scene = scene.replace('controls.minPolarAngle = Math.PI / 2 - 0.45;', 'controls.minPolarAngle = 0.08;')
scene = scene.replace('controls.maxPolarAngle = Math.PI / 2 + 0.45;', 'controls.maxPolarAngle = Math.PI - 0.08;')
scene = scene.replace('controls.autoRotateSpeed = 1.2;', 'controls.autoRotateSpeed = 1.2;\n  controls.target.set(0, 0.95, 0);\n  controls.enablePan = true;')
scene = scene.replace('renderer.setPixelRatio(window.devicePixelRatio);', 'renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));')
# Original name-based picking never assigned mesh names, selected on pointerdown,
# and ignored hidden ancestors. The integration owns these behaviors instead.
begin = scene.index('  // 点击拾取')
end = scene.index('  // ========== UI 绑定', begin)
scene = scene[:begin]+scene[end:]
begin = scene.index('  document.getElementById("organ-opacity").oninput')
end = scene.index('  document.getElementById("resetCam").onclick', begin)
scene = scene[:begin]+scene[end:]
scene = scene.replace('camera.position.set(0, 1.6, 4.2);\n    controls.target.set(0, 1.0, 0);', 'camera.position.set(0, 1.6, 4.2);\n    controls.target.set(0, 0.95, 0);')
scene = scene.replace('  animate();', '''  window.dispatchEvent(new Event('resize'));
  initAnatomyBridge({THREE,scene,camera,renderer,controls,bodyShell,skinMat,
    groups:{ske:sysSke,cir:sysCir,res:sysRes,dig:sysDig,ner:sysNer,uri:sysUri},
    organs:{heart,lungL,lungR,liver,stomach,intestine,brain,kidneyL,kidneyR,bladder}});
  animate();''')
page = page.replace('<head>', '''<head>
<meta http-equiv="Content-Security-Policy" content="default-src 'self' qrc: data:; script-src 'self' qrc: 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'">
''')
page = page.replace('</style>', '''
  #app {grid-template-columns: 228px minmax(0,1fr);}
  #canvas-wrap {min-width:0;min-height:0;}
  .dashboard {padding:14px;scrollbar-width:thin;}
  .title {font-size:17px;} .subtitle {margin-bottom:12px;}
  .group {padding:12px;margin-bottom:10px;} .sys-item {padding:5px 6px;}
  .hint {width:90%;text-align:center;bottom:12px;font-size:11px;padding:8px;}
  select {width:100%;background:#102b48;color:#dff4ff;border:1px solid #366083;border-radius:6px;padding:7px;margin:6px 0;}
  .info-card {margin-top:10px;padding:12px;}
  #source-legend {font-size:11px;color:#b9dcff;margin:8px 0;line-height:1.6;}
  #viewport-status {position:absolute;right:12px;top:12px;font-size:11px;color:#b9dcff;pointer-events:none;}
</style>''')
page = page.replace('<div class="group">', '''<div class="group">
      <h3>器官 / 肌群 / 系统</h3>
      <select id="region-select" aria-label="区域目录"></select>
      <select id="color-mode" aria-label="颜色模式"><option value="source">药物证据 · 默认透明蒙版</option><option value="system">原稿系统配色 · 非药物影响</option></select>
      <select id="reproductive" aria-label="生殖器官分层"><option value="none">隐藏生殖分层</option><option value="testes">睾丸示意层</option><option value="uterus">子宫示意层</option></select>
      <div id="source-legend">亮色仅表示文献关联，不是个人反应。</div>
    </div>
    <div class="group">''',1)
page = page.replace('<h3>可视化调节</h3>', '<h3>可视化调节</h3>')
page = page.replace('id="sys-ner" />', 'id="sys-ner" checked />')
page = page.replace('    <div class="hint">', '    <div id="viewport-status">正在准备渲染</div>\n    <div class="hint">')
page = page.replace('横向拖拽旋转人体 · 滚轮缩放 · 点击器官查看详情', '拖拽全向旋转 · 右键平移 · 滚轮缩放 · 点击器官联动证据')
page = page.replace('点击人体器官查看分层位置与生理指标。建议先关闭无关系统，单独观察骨骼、循环或消化系统，辨识更清晰。', 'HTML 原稿示意几何；点击器官联动右侧证据。显示不构成生理指标测量。')
page += '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>\n<script type="module" src="./scene.mjs"></script>\n</body></html>\n'
(ROOT/'assets/web/index.html').write_text(page,encoding='utf-8')
(ROOT/'assets/web/scene.mjs').write_text("import * as THREE from './vendor/three.module.min.js';\nimport {OrbitControls} from './vendor/OrbitControls.js';\nimport {initAnatomyBridge} from './bridge.mjs';\n"+scene,encoding='utf-8')
