import {isClick, trackMovement} from './interaction.mjs';

// Bridge between the embedded page and the Python-owned region state.
// Protocol (unchanged):
// - after QWebChannel is open, call anatomy.ready();
// - expose window.applyAnatomyState(state);
// - region clicks call anatomy.selectRegion(region) with a catalog region id.
//
// The left panel is presentation only. It is rebuilt from state.regions /
// state.systems, so the Python catalog remains the single source of ids,
// membership and layer ownership.
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
    displayToggle: document.getElementById('display-toggle'),
    displayBody: document.getElementById('display-body'),
    systemList: document.getElementById('system-list'),
    selectionName: document.getElementById('selection-name'),
    selectionMeta: document.getElementById('selection-meta'),
    legendEvidence: document.getElementById('legend-evidence'),
    tooltip: document.getElementById('tooltip'),
    tooltipName: document.getElementById('tooltip-name'),
    tooltipTag: document.getElementById('tooltip-tag'),
    autoRotate: document.getElementById('autoRotate'),
    status: document.getElementById('viewport-status'),
  };

  let current = {
    effects: {}, selected: 'brain', members: [], evidence: [], name: '大脑',
    substance: '未选择物质', regions: [], systems: [],
  };
  let bridge = null;
  let start = null;
  let hoverFrame = 0;
  let pendingPointer = null;
  let expandedMuscle = '';

  // Compact labels for the short-stage two-column index. Full names stay in
  // the selection header, so a truncated grid cell loses no meaning.
  const SYSTEM_SHORT = {
    integumentary: '皮肤', nervous: '神经', cardiovascular: '心血管',
    respiratory: '呼吸', digestive: '消化', urinary: '泌尿',
    reproductive: '生殖', muscular: '肌肉', metabolic: '代谢',
  };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

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

  ui.displayToggle.addEventListener('click', () => {
    const open = ui.displayToggle.getAttribute('aria-expanded') !== 'true';
    ui.displayToggle.setAttribute('aria-expanded', String(open));
    ui.displayBody.hidden = !open;
  });

  function paintColorMode() {
    const on = stage.systemColors;
    ui.colorMode.textContent = '系统配色';
    ui.colorMode.setAttribute('aria-pressed', String(on));
    ui.colorMode.title = on
      ? '系统配色开启：器官按组织色显示；点击关闭恢复默认中性灰'
      : '系统配色关闭（默认）：仅选中与文献关联着色';
    ui.legendEvidence.textContent = on
      ? '系统配色开 · 亮色 = 证据'
      : '亮色 = 选中 / 文献关联';
  }
  ui.colorMode.addEventListener('click', () => {
    stage.setSystemColors(!stage.systemColors);
    paintColorMode();
  });
  paintColorMode();

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
    ui.autoRotate.textContent = on ? '停止' : '旋转';
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
    // Any explicit catalog pick is a reader action: reveal accent colour.
    stage.markSelectionActive();
    if (bridge) bridge.selectRegion(region);
    else renderPanel();
  }

  function regionMap() {
    return new Map((current.regions || []).map(region => [region.id, region]));
  }

  function selectedSystemId() {
    if (!current.selected) return '';
    const region = regionMap().get(current.selected);
    if (!region) return '';
    return region.kind === 'system' ? region.id : region.system;
  }

  function syncLayerToggles() {
    const layers = stage.layerState;
    for (const input of ui.systemList.querySelectorAll('input[data-layer]')) {
      const key = input.dataset.layer;
      input.checked = !!layers[key];
    }
    ui.reproductive.value = stage.reproChoice;
  }

  function memberButton(region, extraClass) {
    const button = el('button', 'member-row' + (extraClass ? ` ${extraClass}` : ''));
    button.type = 'button';
    button.dataset.region = region.id;
    button.setAttribute('aria-current', String(region.id === current.selected));
    const sw = el('span', 'sw');
    sw.style.setProperty('--c', region.id === current.selected ? 'var(--accent)' : 'var(--text-3)');
    button.append(sw);
    button.append(el('span', 'member-label', region.name));
    if (region.id === 'uterus') {
      button.append(el('span', 'tag tag-schematic', '示意'));
    } else if (region.id === 'shell') {
      button.append(el('span', 'tag tag-real', '全身'));
    }
    return button;
  }

  function memberList(system) {
    const list = el('div', 'member-list');
    const byId = regionMap();
    for (const id of system.members) {
      const region = byId.get(id);
      if (!region) continue;
      if (region.kind === 'muscle') {
        const group = memberButton(region, 'member-group');
        const heads = stage.headsFor(region.id);
        group.append(el('span', 'member-count', `${heads.length} 头`));
        const open = expandedMuscle === region.id || current.selected === region.id;
        group.setAttribute('aria-expanded', String(open));
        group.addEventListener('click', () => {
          expandedMuscle = open ? '' : region.id;
          if (current.selected !== region.id) pickRegion(region.id);
          else renderPanel();
        });
        list.append(group);
        if (open) {
          const headList = el('div', 'head-list');
          for (const head of heads) {
            const row = el('button', 'head-row');
            row.type = 'button';
            row.title = head.sourceId ? `来源 ${head.sourceId}` : '来源网格';
            row.append(el('span', 'head-label', head.label));
            if (head.sourceId) row.append(el('span', 'head-id', head.sourceId));
            // A head belongs to its muscle group; clicking a head selects the
            // group, matching the Python region catalog (no head-level ids).
            row.addEventListener('click', () => pickRegion(region.id));
            headList.append(row);
          }
          list.append(headList);
        }
      } else {
        const button = memberButton(region);
        button.addEventListener('click', () => pickRegion(region.id));
        list.append(button);
      }
    }
    return list;
  }

  function renderSystems() {
    const systems = Array.isArray(current.systems) ? current.systems : [];
    const activeSystem = selectedSystemId();
    const claimedLayers = new Set();
    ui.systemList.textContent = '';
    for (const system of systems) {
      const sharedLayer = !!(system.layer && claimedLayers.has(system.layer));
      const row = el('div', 'sys-row');
      const toggle = document.createElement('input');
      toggle.type = 'checkbox';
      toggle.dataset.layer = system.layer || '';
      toggle.checked = !!(system.layer && stage.layerState[system.layer]);
      toggle.disabled = !system.layer || sharedLayer;
      toggle.title = sharedLayer ? '与同层系统共用显示开关' : '';
      toggle.setAttribute('aria-label', `显示${system.name}图层`);
      toggle.addEventListener('change', () => {
        if (!system.layer) return;
        stage.setLayer(system.layer, toggle.checked);
        syncLayerToggles();
      });
      if (system.layer && !sharedLayer) claimedLayers.add(system.layer);
      const button = el('button', 'sys-btn');
      button.type = 'button';
      button.dataset.system = system.id;
      button.title = system.name;
      button.setAttribute('aria-current', String(system.id === current.selected));
      const sw = el('span', 'sw');
      sw.style.setProperty('--c', system.id === current.selected ? 'var(--accent)' : 'var(--text-3)');
      button.append(sw,
        el('span', 'member-label full', system.name),
        el('span', 'member-label short', SYSTEM_SHORT[system.id] || system.name),
        el('span', 'member-count', String(system.members.length)));
      button.addEventListener('click', () => {
        if (expandedMuscle && !system.members.includes(expandedMuscle)) expandedMuscle = '';
        pickRegion(system.id);
      });
      row.append(toggle, button);
      ui.systemList.append(row);
      if (system.id === activeSystem) ui.systemList.append(memberList(system));
    }
    syncLayerToggles();
  }

  function renderInfo() {
    const region = regionMap().get(current.selected);
    const name = current.name || stage.regionName(current.selected);
    const evidence = Array.isArray(current.evidence) ? current.evidence : [];
    const schematic = stage.isSchematic(current.selected);
    const hasMesh = stage.model.regions.has(current.selected);
    const members = Array.isArray(current.members) ? current.members : [];
    if (ui.selectionName) ui.selectionName.textContent = name;
    if (ui.selectionMeta) {
      const parts = [];
      if (region && region.kind === 'system') {
        parts.push('系统', `成员 ${members.length}`);
      } else if (region && region.kind === 'muscle') {
        parts.push('肌群', `${stage.headsFor(current.selected).length} 个肌肉头`);
      } else {
        parts.push('器官');
      }
      parts.push(schematic ? '示意层' : hasMesh ? '真实网格' : '系统区域');
      if (evidence.length) parts.push(`文献关联 ${evidence.length}`);
      ui.selectionMeta.textContent = parts.join(' · ');
    }
  }

  function renderPanel() {
    renderSystems();
    renderInfo();
    paintColorMode();
  }

  window.applyAnatomyState = incoming => {
    if (!incoming || typeof incoming !== 'object') return;
    current = Object.assign(current, incoming);
    stage.applyState(current);
    renderPanel();
  };

  // ------------------------------------------------------------ pointer
  function hideTooltip() {
    ui.tooltip.hidden = true;
    canvas.classList.remove('can-pick');
  }

  function showTooltip(name, tag, clientX, clientY) {
    ui.tooltipName.textContent = name;
    ui.tooltipTag.textContent = tag;
    ui.tooltipTag.className = 'tag ' + (tag === '示意层' ? 'tag-schematic' : 'tag-real');
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
      if (hit) {
        showTooltip(hit.name, hit.schematic ? '示意层' : hit.head ? '肌肉头' : '真实网格',
          point.x, point.y);
      } else {
        hideTooltip();
      }
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
