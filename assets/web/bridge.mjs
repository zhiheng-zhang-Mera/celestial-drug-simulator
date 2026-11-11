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
      color:0xC7A79C,transparent:true,opacity:.55,depthWrite:false,side:THREE.DoubleSide}));
    mesh.position.set(x,y,z);mesh.scale.set(sx,sy,sz);groups[regionGroups[region]].add(mesh);addNamed(mesh,region);
  }
  for(const side of [-1,1]){
    schematic('biceps',side*.55,1.33,.07,.065,.19,.055);
    schematic('triceps',side*.55,1.33,-.08,.07,.21,.06);
    schematic('quadriceps',side*.18,-.26,.03,.09,.25,.075);
    schematic('testes',side*.055,-.06,.10,.045,.06,.045);
  }
  schematic('uterus',0,-.01,.10,.09,.065,.045);
  for(const side of [-1,1])schematic('uterus',side*.09,.02,.10,.065,.016,.016);
  const layerRow=document.createElement('div');layerRow.className='sys-item';
  layerRow.innerHTML='<label for="sys-mus">肌肉群</label><input id="sys-mus" type="checkbox" checked>';
  const uri=document.getElementById('sys-uri');
  (uri.closest('.layers')||uri.closest('.group')).append(layerRow);
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
      if(mat.emissive){mat.emissive.setHex(selected&&!style.effect?0xBFD8D2:style.color);
        mat.emissiveIntensity=glow*(style.effect?.55:system?.12:selected?.25:.05);}
    }
    document.getElementById('source-legend').textContent=system?
      '系统配色仅辨识结构，不代表药物影响。':
      '青·机制 / 蓝·代谢 / 浅蓝·排泄 / 金·关注；亮色为文献关联。';
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
      if(state.selected==='triceps')camera.position.set(0,1.15,-4.9);
      if(state.selected==='biceps')camera.position.set(0,1.15,4.9);
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
