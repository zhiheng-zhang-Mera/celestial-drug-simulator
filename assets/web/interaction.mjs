// Pure interaction helpers. Kept dependency-free so Node can test them.
//
// Semantics that must not change:
// - isVisible: an object is pickable only when no ancestor is hidden.
// - isClick: a press that never moved far enough is a click, not a drag.
// - visualStyle: source-backed evidence categories are the *only* thing that
//   changes an organ's evidence colour. Structural membership (members) is
//   navigation, never evidence.
export function isVisible(object) {
  for (let part = object; part; part = part.parent) {
    if (part.visible === false) return false;
  }
  return true;
}

export function isClick(start, end) {
  return !!start && !start.moved && Math.hypot(end.x - start.x, end.y - start.y) < 6;
}

export function trackMovement(start, point) {
  if (start && Math.hypot(point.x - start.x, point.y - start.y) >= 6) start.moved = true;
}

// Restricted category palette: low-chroma clinical accents, not neon.
export const EVIDENCE_COLORS = {
  mechanism: 0x74E3C8,
  metabolism: 0x8FB4D8,
  excretion: 0xA8CCDC,
  label_concern: 0xE2BE7E,
};

// Neutral tissue tint used by the evidence mode when an organ has no source
// association (uniform so that highlighted organs read first).
export const NEUTRAL_ORGAN = 0x9FB8CC;

export function visualStyle(region, state, systemColors, baseColor) {
  const category = state && state.effects ? state.effects[region] : undefined;
  const effect = Object.prototype.hasOwnProperty.call(EVIDENCE_COLORS, category);
  return {
    color: effect ? EVIDENCE_COLORS[category] : (systemColors ? baseColor : NEUTRAL_ORGAN),
    effect,
    category: effect ? category : null,
  };
}
