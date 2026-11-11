import {isClick, trackMovement} from './interaction.mjs';

// Bridge between the embedded page and the Python-owned region state.
// Protocol (unchanged):
// - after QWebChannel is open, call anatomy.ready();
// - expose window.applyAnatomyState(state);
// - region clicks call anatomy.selectRegion(region) with a catalog region id.
export function initAnatomyBridge(ctx) {
  const {renderer, stage} = ctx;
  const canvas = renderer.domElement;
  const wrap = document.getElementById('canvas-wrap');

  const ui = {
    skin: document.getElementById('skin-opacity'),
    skinVal: document.getElementById('skin-val'),
    organ: document.getElementById('organ-opacity'),
    organVal: document.getElementById('organ-val'),
    glow: document.getElementById('glow'),
    glowVal: document.getElementById('glow-val'),
    colorMode: document.getElementById('color-mode'),
    reproductive: document.getElementById('reproductive'),
    regionSelect: document.getElementById('region-select'),
    selectionName: document.getElementById('selection-name'),
    selectionMeta: document.getElementById('selection-meta'),
    legendEvidence: document.getElementById('legend-evidence'),
    tooltip: document.getElementById('tooltip'),
    tooltipName: document.getElementById('tooltip-name'),
    tooltipTag: document.getElementById('tooltip-tag'),
    autoRotate: document.getElementById('autoRotate'),
    status: document.getElementById('viewport-status'),
  };

  const layerInputs = {
    shell: document.getElementById('layer-shell'),
    cir: document.getElementById('layer-cir'),
    res: document.getElementById('layer-res'),
    dig: document.getElementById('layer-dig'),
    ner: document.getElementById('layer-ner'),
    uri: document.getElementById('layer-uri'),
    mus: document.getElementById('layer-mus'),
    rep: document.getElementById('layer-rep'),
  };

  let current = {
    effects: {}, selected: 'brain', members: [], evidence: [],
    name: '大脑', substance: '未选择物质', regions: [],
  };
  let bridge = null;
  let start = null;
  let hoverFrame = 0;
  let pendingPointer = null;

  // ------------------------------------------------------------- controls
  stage.setSkinOpacity(parseFloat(ui.skin.value));
  stage.setOrganOpacity(parseFloat(ui.organ.value));
  stage.setGlow(parseFloat(ui.glow.value));
  stage.setRepro(ui.reproductive.value);

  ui.skin.addEventListener('input', () => {
    const value = parseFloat(ui.skin.value);
    stage.setSkinOpacity(value);
    ui.skinVal.textContent = `${Math.round(value * 100)}%`;
  });
  ui.organ.addEventListener('input', () => {
    const value = parseFloat(ui.organ.value);
    stage.setOrganOpacity(value);
    ui.organVal.textContent = `${Math.round(value * 100)}%`;
  });
  ui.glow.addEventListener('input', () => {
    const value = parseFloat(ui.glow.value);
    stage.setGlow(value);
    ui.glowVal.textContent = value.toFixed(1);
  });

  function paintColorMode() {
    const system = stage.systemColors;
    ui.colorMode.dataset.mode = system ? 'system' : 'evidence';
    ui.colorMode.setAttribute('aria-pressed', String(system));
    ui.colorMode.textContent = system ? '系统配色' : '证据模式';
    ui.legendEvidence.textContent = system
      ? '亮色 = 文献关联'
      : '中性色 = 无文献关联；亮色 = 文献关联';
  }
  ui.colorMode.addEventListener('click', () => {
    stage.setSystemColors(!stage.systemColors);
    paintColorMode();
  });
  paintColorMode();

  for (const [key, input] of Object.entries(layerInputs)) {
    input.addEventListener('change', () => stage.setLayer(key, input.checked));
  }
  ui.reproductive.addEventListener('change', () => stage.setRepro(ui.reproductive.value));

  for (const [id, view] of [['view-front', 'front'], ['view-back', 'back'], ['resetCam', 'front']]) {
    document.getElementById(id).addEventListener('click', () => {
      stage.setView(view);
      syncAutoRotate();
    });
  }
  ui.autoRotate.addEventListener('click', () => {
    stage.toggleAutoRotate();
    syncAutoRotate();
  });
  function syncAutoRotate() {
    const on = stage.autoRotating;
    ui.autoRotate.setAttribute('aria-pressed', String(on));
    ui.autoRotate.textContent = on ? '停止旋转' : '自动旋转';
  }

  window.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const tag = (event.target && event.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
    const key = event.key.toLowerCase();
    if (key === 'f') { stage.setView('front'); syncAutoRotate(); }
    else if (key === 'b') { stage.setView('back'); syncAutoRotate(); }
    else if (key === 'r') { stage.setView('front'); syncAutoRotate(); }
    else if (event.key === ' ') {
      event.preventDefault();
      stage.toggleAutoRotate();
      syncAutoRotate();
    }
  });

  // ------------------------------------------------------------- protocol
  function pickRegion(region) {
    if (!region) return;
    if (bridge) bridge.selectRegion(region);
  }
  ui.regionSelect.addEventListener('change', () => pickRegion(ui.regionSelect.value));

  function syncLayerCheckboxes() {
    const layers = stage.layerState;
    for (const [key, input] of Object.entries(layerInputs)) input.checked = !!layers[key];
    const repro = stage.reproChoice;
    ui.reproductive.value = repro;
  }

  function renderInfo() {
    const state = current;
    const region = state.selected;
    const name = state.name || stage.regionName(region);
    const evidence = Array.isArray(state.evidence) ? state.evidence : [];
    const schematic = stage.isSchematic(region);
    const hasMesh = stage.model.regions.has(region);
    if (ui.selectionName) ui.selectionName.textContent = name;
    if (ui.selectionMeta) {
      const parts = [schematic ? '示意层' : hasMesh ? '真实网格' : '系统区域'];
      if (evidence.length) parts.push(`文献关联 ${evidence.length}`);
      if (Array.isArray(state.members) && state.members.length) {
        parts.push('关联 ' + state.members.map(member => stage.regionName(member)).join('、'));
      }
      ui.selectionMeta.textContent = parts.join(' · ');
    }
  }

  window.applyAnatomyState = incoming => {
    if (!incoming || typeof incoming !== 'object') return;
    current = Object.assign(current, incoming);
    if (ui.regionSelect.options.length === 0 && Array.isArray(current.regions)) {
      for (const region of current.regions) {
        const option = document.createElement('option');
        option.value = region.id;
        option.textContent = region.name;
        ui.regionSelect.append(option);
      }
    }
    if (current.selected) ui.regionSelect.value = current.selected;
    stage.applyState(current);
    syncLayerCheckboxes();
    paintColorMode();
    renderInfo();
  };

  // ------------------------------------------------------------ pointer
  function hideTooltip() {
    ui.tooltip.hidden = true;
    canvas.classList.remove('can-pick');
  }

  function showTooltip(name, schematic, clientX, clientY) {
    ui.tooltipName.textContent = name;
    ui.tooltipTag.textContent = schematic ? '示意层' : '真实网格';
    ui.tooltipTag.className = 'tag ' + (schematic ? 'tag-schematic' : 'tag-real');
    const rect = wrap.getBoundingClientRect();
    const x = Math.min(Math.max(0, clientX - rect.left), Math.max(0, rect.width - 190));
    const y = Math.min(Math.max(0, clientY - rect.top), Math.max(0, rect.height - 48));
    ui.tooltip.style.left = `${x}px`;
    ui.tooltip.style.top = `${y}px`;
    ui.tooltip.hidden = false;
    canvas.classList.add('can-pick');
  }

  function handleHover() {
    if (hoverFrame || !pendingPointer) return;
    const point = pendingPointer;
    pendingPointer = null;
    hoverFrame = requestAnimationFrame(() => {
      hoverFrame = 0;
      if (start && start.moved) { hideTooltip(); return; }
      const hit = stage.pick(point.x, point.y);
      if (hit) showTooltip(hit.name, hit.schematic, point.x, point.y);
      else hideTooltip();
    });
  }

  canvas.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    start = {x: event.clientX, y: event.clientY};
    canvas.classList.add('is-dragging');
    hideTooltip();
  });
  canvas.addEventListener('pointermove', event => {
    if (start) trackMovement(start, {x: event.clientX, y: event.clientY});
    pendingPointer = {x: event.clientX, y: event.clientY};
    handleHover();
  });
  canvas.addEventListener('pointercancel', () => {
    start = null;
    canvas.classList.remove('is-dragging');
  });
  canvas.addEventListener('pointerleave', () => {
    start = null;
    canvas.classList.remove('is-dragging');
    hideTooltip();
  });
  canvas.addEventListener('pointerup', event => {
    const initial = start;
    start = null;
    canvas.classList.remove('is-dragging');
    if (!isClick(initial, {x: event.clientX, y: event.clientY})) return;
    const hit = stage.pick(event.clientX, event.clientY);
    if (hit) pickRegion(hit.region);
  });
  canvas.addEventListener('contextmenu', event => event.preventDefault());

  // ---------------------------------------------------------- QWebChannel
  if (window.qt && window.QWebChannel) {
    try {
      new QWebChannel(qt.webChannelTransport, channel => {
        bridge = (channel.objects && channel.objects.anatomy) || null;
        if (bridge) bridge.ready();
      });
    } catch (error) {
      console.error('[anatomy] QWebChannel init failed', error);
      ui.status.textContent = '未连接 Python 状态';
    }
  } else {
    ui.status.textContent = '预览模式 · 未连接 Python';
  }
}
