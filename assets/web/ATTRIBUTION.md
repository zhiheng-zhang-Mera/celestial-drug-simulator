# Embedded anatomy reference

## Body surface and organs

BodyParts3D, © The Database Center for Life Science, licensed under CC Attribution-Share Alike 2.1 Japan.
Source: BodyParts3D 3.0 (20110915), binary STL mirror by Kevin Mattheus Moerman, commit
`f0eeb6e843380cfe6b83797cf8c3e1af74de5e61`
(<https://github.com/Kevin-Mattheus-Moerman/BodyParts3D/tree/f0eeb6e843380cfe6b83797cf8c3e1af74de5e61>).
License: <https://creativecommons.org/licenses/by-sa/2.1/jp/>. Full upstream notice:
`assets/anatomy/LICENSE-BodyParts3D.txt`. Citation: Mitsuhashi N et al. *BodyParts3D: 3D structure
database for anatomical concepts.* Nucleic Acids Res. 2009;37:D782–5.
<https://doi.org/10.1093/nar/gkn613>

The mirror's MIT software license does not relicense the models. The derived Web data is distributed
under CC BY-SA 2.1 Japan. No Z-Anatomy or noncommercial model assets are included.

### What the embedded page loads

`assets/web/data/bodyparts3d.json` is a byte-for-byte copy of the canonical bundle
`assets/anatomy/bodyparts3d.json` (SHA256 `32a6dff285793571bc4f48a9d823086c265e33af33bf84d1b84b30efb05e6cfc`).
It records the organ geometry and the exact upstream commit. The active module is
`assets/web/data/bodyparts3d.mjs`, generated deterministically by `tools/build_web_anatomy.py` because the
page's `connect-src 'none'` CSP does not allow `fetch()`.

The organ components (`brain`, `heart`, `lungs`, `liver`, `stomach`, `kidneys`, `bladder`, `testes`,
`biceps`, `triceps`, `quadriceps`) come from that bundle: selected source structures, welded/clustered by
the original Celestial adapter, converted from millimetres to metres and from the source axes
(x left / y posterior / z superior) to the viewer axes (x patient-left / y up / z anterior). Local
winding repair is applied to triangles that disagree with their manifold neighbours. No vertices are
invented. The bundle is a display simplification, not a measurement.

### Why the shell is re-derived from FMA7163.stl

The organ bundle's `shell` region is a uniform-grid reduction of the BodyParts3D FMA7163 skin mesh to
12,000 faces. At that budget the grid is much coarser than the source and joins vertices across the body,
producing triangles up to ~1.6 m long. Rendered as skin it reads as spikes, not a human. The Web shell is
therefore re-derived from the same pinned FMA7163 skin STL:

- file: `FMA7163.stl` from the mirror commit above; SHA256
  `c7762a9b5044a7329ac99403b42551571a28325472103cf1900c379cd8dfcfb7`
- fixed 12 mm deterministic vertex grid; mean of vertices per cell; duplicate face removal; the same
  winding repair
- 32,451 vertices / 87,302 triangles; median edge ≈ 13.0 mm, maximum ≈ 78 mm
- no resampling or invented anatomy; this is the real BodyParts3D skin surface at a display LOD

The canonical `assets/anatomy/bodyparts3d.json` is not modified. The Tk Simplified View continues to use
its own renderer and assets unchanged.

### Explicitly not source geometry

- **Uterus**: BodyParts3D data in this bundle does not include a uterus mesh. The existing reproductive
  entry is kept as a small procedural schematic (translucent body + wireframe) and is labelled
  `示意层` in the page, tooltip and module report. It is not presented as source geometry.
- **Bones**: the source bundle contains no skeleton. There is no bone switch and no procedural bone mesh;
  the panel states `骨骼 · 来源数据未含`.

## Renderer and runtime

Vendor: Three.js r164 (<https://github.com/mrdoob/three.js/tree/r164>, MIT; full license in
`vendor/THREE-LICENSE.txt`). `build/three.module.min.js` SHA256
`6c2bfdf07626404916f34aef8cf57992926d849526bc6eb4556da96a3ba4e78c`; `examples/jsm/controls/OrbitControls.js`
has only its import rewritten to the local module (SHA256
`61b1f6c8a13552b8ec666b5723bea1951bd110f3ed3767a37d041304389992b2`). No runtime CDN, npm, server or
download is used.

Qt WebEngine 6.12 and `qrc:///qtwebchannel/qwebchannel.js` are supplied by the already-installed PySide6
runtime; Qt is not vendored or installed by this change and its existing license terms remain applicable.

## Scope and limitations

This is a single adult male reference, not patient-specific anatomy. Colors, transparency, selection
highlighting and evidence colors are interface conventions, not tissue appearance. Literature association
color does not establish drug mechanism, dose response, organ concentration, damage or clinical validity.
The uterus schematic and clustered/simplified LODs are display adaptations, not additional anatomical
measurements or clinical validation.
