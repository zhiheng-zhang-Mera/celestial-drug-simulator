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
  const colors={mechanism:0x74E3C8,metabolism:0x8FB4D8,excretion:0xA8CCDC,label_concern:0xE2BE7E};
  const category=state.effects?.[region];
  return {color:colors[category]??(systemColors?baseColor:0x9FB3BD),effect:category in colors};
}
