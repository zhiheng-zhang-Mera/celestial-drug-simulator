# Anatomy asset attribution

BodyParts3D, © The Database Center for Life Science licensed under CC Attribution-Share Alike 2.1 Japan.

Source: BodyParts3D 3.0 (20110915), binary STL mirror by Kevin Mattheus Moerman:
https://github.com/Kevin-Mattheus-Moerman/BodyParts3D/tree/f0eeb6e843380cfe6b83797cf8c3e1af74de5e61
Original archive: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
Pinned model license: https://creativecommons.org/licenses/by-sa/2.1/jp/
Full upstream notice: LICENSE-BodyParts3D.txt in this directory.

The mirror's MIT software license does NOT relicense these models. This adapted JSON model bundle is distributed under CC BY-SA 2.1 Japan. The official archive now lists CC BY 4.0; this adaptation retains the terms declared by the pinned source copy. No Z-Anatomy or noncommercial model assets are included.

Modifications by Celestial (2026-11-05): select source cortical structures, organs, skin and individual muscle heads; weld identical STL vertices; deterministic spatial vertex clustering; omit collapsed/duplicate triangles; preserve source-space coordinates; bundle as JSON with source identifiers and SHA256. Runtime applies one uniform scale, coordinate-axis conversion and reflection winding correction. Geometry is simplified for an offline Tk viewer. Original STL is reproducibly retrievable by the build tool and hashes. No source code from the mirror is executed or bundled.

This single adult male reference is not patient-specific anatomy. Cortex is a selected cortical subset, not every brain structure. The uterus display remains original schematic geometry, explicitly labeled and not part of the BodyParts3D bundle. Color and transparency are interface conventions, not original tissue appearance. Geometric resemblance does not establish drug mechanism, dose response or clinical validation.

Citation: Mitsuhashi N et al. BodyParts3D: 3D structure database for anatomical concepts. Nucleic Acids Res. 2009;37:D782–5. https://doi.org/10.1093/nar/gkn613

Reproduce: Python3.14 and Windows system curl.exe (asset preparation only), `python tools/build_anatomy_atlas.py --cache <local-source-directory>`. Runtime needs only bundled assets and existing Python/Tk; no network or external model runtime dependency.

The runtime skin display uses local convex envelopes of the source skin vertices as a faint approximate external mask. Organs and muscle heads use the independently simplified source triangle meshes; a lower-detail bundle is used during dragging and detailed surfaces return on release. These display simplifications are modifications, not additional anatomical measurements.
