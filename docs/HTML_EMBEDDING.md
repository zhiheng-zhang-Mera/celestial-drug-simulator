# DEV-09 desktop HTML anatomy (v3 — physiological systems, neutral default)

The anatomy stage is a native embedded WebEngine child of the existing Tk panel, started by the
unchanged `python -m src.app` entry. The page renders the real BodyParts3D body surface and the bundled
organ / muscle meshes. Windows Python with Tk and the installed PySide6/QtWebEngine 6.12 is still
required; no runtime package, CDN or network access is added. Missing runtime, load failure or WebGL
failure stays visible and the `简化视图` button keeps the prior offline Tk renderer.

## Scene

- **Body surface:** FMA7163 skin from the pinned BodyParts3D mirror, re-derived at a fixed 12 mm
  deterministic grid (32,451 vertices / 87,302 triangles). Default is a translucent warm-grey shell
  (slider 5–35%, default 30%) with a quiet rim and studio-neutral lights. No capsule/sphere body.
- **Organs:** real `brain`, `heart`, `lungs`, `liver`, `stomach`, `kidneys`, `bladder`, `testes` meshes.
  Default material is a neutral grey (82% opacity, faint self-tint). Selection adds the mint accent and
  an inverted-hull outline; source evidence associations use the existing
  `mechanism / metabolism / excretion / label_concern` colours. Structural membership (`members`) is
  navigation only, not evidence.
- **Muscles:** real `biceps`, `triceps`, `quadriceps` meshes. The generated data keeps the upstream
  `sourceIds`, so all 18 available heads are individual meshes with individual labels and click
  targets: biceps short/long (4), triceps medial/lateral/long (6), quadriceps
  rectus/lateralis/medialis/intermedius (8). Clicking a head selects its muscle group, because the
  Python region catalog has group-level ids only.
- **Reproductive layer:** real `testes`; the uterus entry is a clearly labelled procedural schematic
  (`示意层`) because the source bundle has no uterus mesh. It is neutral grey by default.
- **Skeleton:** the source bundle contains no bones. There is no bone switch or fake bone mesh; the
  panel states `骨骼：来源数据未含`.
- Ink stage `#0C0D0F`, no neon, no particles, no decorative animation. Stage overlay: vertical front /
  back / reset / auto-rotate / 系统配色 bar on the right edge, zoom/status, hover tooltip, loading
  progress and readable error state.

## Systems, layers and neutral default

`src/anatomy.py` now exposes the physiological systems as navigation metadata only:
`皮肤/体表`, `神经`, `心血管`, `呼吸`, `消化`, `泌尿`, `生殖`, `肌肉`, plus the existing
`代谢相关器官` alias. Each system lists its available real members; a system never invents evidence.
`src/web_anatomy.py` sends the system list, each region's owning system and its display layer to the
page. `interaction.mjs` remains the single source of evidence semantics.

- **Default is colourless.** No tissue/system colour is painted on the body. Only an explicit catalog
  selection (side panel, Tk region directory or a mesh click) receives the accent, or a source-backed
  evidence hit receives its `visualStyle` category colour. The initial Python cursor (`大脑`) is not a
  reader action, so it stays grey until something is selected.
- **System selection** highlights every available member; selecting one organ or muscle group
  highlights only that region.
- **`系统配色`** is an explicit stage-toolbar switch, default **off**; turning it on restores the muted
  tissue colours. It never adds evidence colour.
- **Layer switches** are grouped by system in the left panel; each row's checkbox controls its display
  layer. `代谢相关器官` shares the digestive layer (its checkbox is disabled and labelled as shared).
- **Very short stages** switch the system index to two columns with short labels so all systems, the
  selected members, the display disclosure and both provenance notes fit at 1024×720 / 1200×800
  without scrolling.

## Protocol (unchanged)

Python owns identities and evidence. HTML receives only the region catalog, system metadata, selected
identity-derived evidence, effect categories, members and the display substance name; no physiology,
genotype or regimen export is sent to the renderer. Selection returns a whitelisted region id via
Qt WebChannel → JSON-line stdout → Tk event queue.

The page still:
- calls `anatomy.ready()` after QWebChannel opens;
- exposes `window.applyAnatomyState(state)` and updates selection, evidence highlight, region label,
  system/member directory and layer switches from it;
- calls `anatomy.selectRegion(region)` on a mesh, system, member or muscle-head click, with a catalog
  region id.

## Offline and security

All resources are local files under `assets/web` (`file:`); CSP remains
`default-src 'self' qrc: data:` / `connect-src 'none'`; Three.js comes from the existing `vendor/`.
Qt's request interceptor still allows only `assets/web` files, the WebChannel qrc script and data URLs.
Drug text is rendered with `textContent`. External links remain Python's explicit browser action.

## Validation

Run from the repository root: `python -m unittest discover -s tests` (103 passed) and
`node --test tests/web_anatomy.test.mjs` (4 passed). Native validation used the same
`CELESTIAL_DRUG_TITLE='Celestial Drug (systems)'` override and the existing capture tooling. The page
logged a first frame of **687 ms** at 1440×900 (679–712 ms across runs, target < 2 s), with
`parts=33 · heads=18`; the WebEngine log contained no Traceback and no JavaScript error.

A real QWebEngine click-round-trip check loaded the page with a recording bridge and exercised the
actual DOM handlers: 9 system rows, system click → `digestive`/`muscular`, muscle group click →
`biceps`, 4 head rows, head click → `biceps`. Screenshots at 1440 / 1200 / 1024, default neutral,
system-selected and atomoxetine-evidence states are in
`_evidence/ui-modernization/final/medical/drug-body-v3-*.png`; the full report is
`_evidence/ui-modernization/modules/medical-systems-v3.md`.

The page text and data are not a clinical claim. The body is one adult male reference; uterus is a
schematic; the shell/organ LODs are display simplifications. No bones, intestines or additional muscle
groups exist in the pinned bundle and none are fabricated.
