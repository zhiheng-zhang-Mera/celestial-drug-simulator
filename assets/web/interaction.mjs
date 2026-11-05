export function isVisible(object) {
  for (let part=object; part; part=part.parent) if (part.visible===false) return false;
  return true;
}
export function isClick(start,end) {
  return !!start && !start.moved && Math.hypot(end.x-start.x,end.y-start.y)<6;
}
export function trackMovement(start,point){
  if(start&&Math.hypot(point.x-start.x,point.y-start.y)>=6)start.moved=true;
}
export function visualStyle(region,state,systemColors,baseColor) {
  const colors={mechanism:0x5bd8c7,metabolism:0x55aaff,excretion:0x87deff,label_concern:0xffd174};
  const category=state.effects?.[region];
  return {color:colors[category]??(systemColors?baseColor:0x9fb8cc),effect:category in colors};
}
