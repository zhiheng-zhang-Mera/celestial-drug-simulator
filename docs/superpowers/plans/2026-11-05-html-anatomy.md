# Embedded reference HTML anatomy plan

**Goal:** Embed the user-selected HTML's complete X-Ray rendering and controls in the desktop anatomy workspace, preserving substance/evidence and legacy workflows.
**Architecture:** Keep Tk as application owner. Installed PySide6 WebEngine is a native child in a Tk frame, with local validated JSON-line IPC. Vendor Three.js164 ES modules and retain the supplied file verbatim. No network/server, browser pop-out or clinical inference.
**Spec:** User request2026-11-05 and assets/reference/doubao_html_20261105_155000.html. Original scene/layout/materials are authoritative; fix broken imports, unnamed picks, drag selection and hidden-layer picking. Sidebar gains20existing regions/reproductive/muscle controls. Default translucent shell; source association mode uses neutral tissues, explicitly optional system colors are not effects. Retain full original scene geometry, add missing original regions as labeled schematic overlays.
**Approaches:** User explicitly chose HTML rendering. Native Canvas approximation cannot reproduce WebGL materials. Migrating all legacy forms to Qt is unnecessary. Native embedded existing WebEngine is selected as bounded adapter; existing Canvas is explicit fallback if dependency/graphics fails.

## Constraints and review focus
- External celestial-drug-simulator repository owns assets/cache/processes. No package installation, CI, merge/release. PySide6/WebEngine6.12 already available; document runtime dependency.
- Untrusted HTML has no shell/file API: whitelist region IDs, local asset requests only, no dynamic code from drug names. Source evidence Python remains authority.
- None/custom identity clears source colors; selection membership never invents evidence.
- Pointer drag does not click; hidden layers do not intercept picks. Orbit/zoom preserve selection; reset updates own state.
- Resizing/tab hiding/parent close must resize/hide/terminate child; load/process failure shows explicit fallback.
- Original geometry is schematic with known implausible positions, not BodyParts3D or clinical anatomy. Preserve previous atlas renderer as fallback.

## Tasks
- [ ] Test bridge payload/whitelist/identity and JS picking rules RED, then implement state contract and offline reference adapter.
- [ ] Embed WebEngine native child and keep existing toolbar/evidence/legacy tabs. Show meaningful loading/error and optional fallback, validate lifecycle.
- [ ] Run full tests, actual-window recording covering load, layer controls, source/None, orbit/zoom/picks, other tab and return; review and fix blockers.
- [ ] Freeze/push code and synchronize impacted Books, independent exact-source verification, retain media limits.

Native inline execution continues the already authorized implementation; approval of the selected HTML supplies the visual design, routine host/bridge choices belong to implementer.
