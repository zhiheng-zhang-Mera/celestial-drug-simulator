import {isVisible,isClick,visualStyle,trackMovement} from './interaction.mjs';

export function initAnatomyBridge(ctx) {
  const {THREE,scene,camera,renderer,controls,groups,organs}=ctx;
  let state={effects:{},selected:'brain',members:[]},bridge=null,start=null,lastSelection=null;
  const names={heart:'heart',lungL:'lungs',lungR:'lungs',liver:'liver',stomach:'stomach',
    brain:'brain',kidneyL:'kidneys',kidneyR:'kidneys',bladder:'bladder'};
  const regionGroups={brain:'ner',heart:'cir',lungs:'res',liver:'dig',stomach:'dig',kidneys:'uri',bladder:'uri',
    biceps:'mus',triceps:'mus',quadriceps:'mus',testes:'rep',uterus:'rep'};
  const picker=[];
  const addNamed=(mesh,region)=>{mesh.userData.region=region;mesh.name=region;picker.push(mesh);};
  for(const [name,region] of Object.entries(names)) addNamed(organs[name],region);
  // The supplied intestine is a visual schematic only, with no independent evidence ID.
  addNamed(organs.intestine,'digestive');
  groups.mus=new THREE.Group();groups.rep=new THREE.Group();scene.add(groups.mus,groups.rep);
  function schematic(region,x,y,z,sx,sy,sz){
    const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,24,18),new THREE.MeshPhongMaterial({
      color:0xb6d6e9,transparent:true,opacity:.65,depthWrite:false,side:THREE.DoubleSide}));
    mesh.position.set(x,y,z);mesh.scale.set(sx,sy,sz);groups[regionGroups[region]].add(mesh);addNamed(mesh,region);
  }
  for(const side of [-1,1]){
    schematic('biceps',side*.64,1.28,.09,.07,.26,.06);
    schematic('triceps',side*.64,1.28,-.09,.075,.28,.065);
    schematic('quadriceps',side*.18,-.03,.08,.09,.3,.07);
    schematic('testes',side*.055,-.47,.13,.045,.065,.045);
  }
  schematic('uterus',0,-.32,.13,.09,.07,.045);
  for(const side of [-1,1])schematic('uterus',side*.09,-.28,.13,.07,.018,.018);
  const layerRow=document.createElement('div');layerRow.className='sys-item';
  layerRow.innerHTML='<label for="sys-mus">肌肉群 · 补充示意</label><input id="sys-mus" type="checkbox" checked>';
  document.getElementById('sys-uri').closest('.group').append(layerRow);
  document.getElementById('sys-mus').onchange=e=>groups.mus.visible=e.target.checked;
  // Each mesh gets its own material: highlighting one organ never colors a whole system.
  const renderables=[];
  for(const group of Object.values(groups))group.traverse(object=>{
    if(!object.material)return;
    object.material=object.material.clone();
    object.userData.baseColor=object.material.color.getHex();renderables.push(object);
  });
  function applyColors(){
    const system=document.getElementById('color-mode').value==='system';
    const opacity=+document.getElementById('organ-opacity').value;
    const glow=+document.getElementById('glow').value;
    for(const object of renderables){
      const region=object.userData.region;
      const style=visualStyle(region,state,system,object.userData.baseColor);
      const selected=region===state.selected||state.members?.includes(region);
      const mat=object.material;mat.color.setHex(style.color);
      mat.opacity=opacity*(style.effect||system?1:.45);
      if(mat.emissive){mat.emissive.setHex(selected&&!style.effect?0xd3edff:style.color);
        mat.emissiveIntensity=glow*(style.effect?1:system?.7:selected?.35:.08);}
    }
    document.getElementById('source-legend').textContent=system?
      '系统配色用于辨识结构，不表示药物影响。药物关联仍依右侧证据。':
      '青·机制 / 蓝·代谢 / 浅蓝·排泄 / 金·关注；亮色为文献关联，非个人反应。';
  }
  function reproductive(){
    const chosen=document.getElementById('reproductive').value;
    groups.rep.children.forEach(mesh=>mesh.visible=mesh.userData.region===chosen);
  }
  function reveal(region){
    const group=regionGroups[region];
    if(group&&group!=='rep'){
      groups[group].visible=true;document.getElementById('sys-'+group).checked=true;
    }
    if(group==='rep'){document.getElementById('reproductive').value=region;reproductive();}
  }
  const select=document.getElementById('region-select');
  function pickRegion(region){bridge?.selectRegion(region);}
  select.onchange=()=>pickRegion(select.value);
  window.applyAnatomyState=incoming=>{
    state=incoming;
    if(!select.options.length)for(const region of state.regions){
      const option=document.createElement('option');option.value=region.id;option.textContent=region.name;select.append(option);
    }
    select.value=state.selected;
    if(lastSelection!==state.selected){
      reveal(state.selected);state.members?.forEach(reveal);
      if(state.selected==='triceps')camera.position.set(0,1.6,-4.2);
      if(state.selected==='biceps')camera.position.set(0,1.6,4.2);
      lastSelection=state.selected;
    }
    for(const region of Object.keys(state.effects))reveal(region);
    document.getElementById('info').replaceChildren();
    const heading=document.createElement('h4');heading.textContent=state.name;
    const info=document.createElement('p');info.textContent=state.substance+' · '+
      (state.evidence?.length?'已收录文献关联，待人工审核；见右侧证据。':'此区域无已收录证据。');
    const geometry=document.createElement('p');geometry.textContent='HTML 原稿及补充示意几何；非真实组织或生理指标测量。';
    document.getElementById('info').append(heading,info,geometry);applyColors();
  };
  document.getElementById('color-mode').onclick=e=>{
    const button=e.currentTarget;button.value=button.value==='source'?'system':'source';
    button.textContent=button.value==='system'?'切换药物证据蒙版':'切换原稿系统配色';applyColors();
  };
  for(const id of ['organ-opacity','glow'])document.getElementById(id).addEventListener('input',()=>{
    document.getElementById(id==='glow'?'glow-val':'organ-val').textContent=(+document.getElementById(id).value).toFixed(id==='glow'?1:2);
    applyColors();
  });
  document.getElementById('reproductive').onchange=reproductive;reproductive();applyColors();
  const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();
  const canvas=renderer.domElement;
  canvas.addEventListener('pointerdown',e=>{start=e.button===0?{x:e.clientX,y:e.clientY}:null;});
  canvas.addEventListener('pointermove',e=>trackMovement(start,{x:e.clientX,y:e.clientY}));
  canvas.addEventListener('pointercancel',()=>start=null);
  canvas.addEventListener('pointerup',e=>{
    const initial=start;start=null;if(!isClick(initial,{x:e.clientX,y:e.clientY}))return;
    const rect=canvas.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);
    ray.setFromCamera(pointer,camera);
    const hit=ray.intersectObjects(picker.filter(isVisible),false)[0];
    if(hit)pickRegion(hit.object.userData.region);
  });
  controls.addEventListener('change',()=>{
    const zoom=4.25/camera.position.distanceTo(controls.target)*100;
    document.getElementById('viewport-status').textContent=`3D · ${zoom.toFixed(0)}% · 拖动旋转`;
  });
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();document.getElementById('loading').textContent='图形上下文已丢失，请重启视图或使用简化视图';document.getElementById('loading').style.display='block';});
  if(window.qt&&window.QWebChannel)new QWebChannel(qt.webChannelTransport,channel=>{
    bridge=channel.objects.anatomy;bridge.ready();
  });
}
