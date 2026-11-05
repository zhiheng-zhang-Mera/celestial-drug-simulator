# DEV-08 open anatomy adaptation plan

Goal: replace primitive organ/muscle volumes with source-backed anatomical contours while preserving existing evidence interactions.
Architecture: pinned BodyParts3D3.0 binary STL inputs -> deterministic vertex clustering -> small committed JSON mesh bundle. Standard-library build script; Tk runtime only. Original license/attribution separate from product code.
Spec: latest Owner request and docs/BODY_UI_FIGMA.md; same external feature checkout, no release/merge.

Approaches considered: enrich procedural ellipsoids (insufficient contour fidelity); import whole Z-Anatomy atlas (large toolchain/mixed source licenses); selected pinned BodyParts3D meshes (chosen implementation judgment: accurate provenance and small runtime subset).

- [x] Asset pipeline: download pinned selected STL + mapping/license, verify hashes, simplify with triangle budget, preserve named muscle heads and atlas spatial alignment. Tests: finite vertices, valid/nondegenerate triangles, source IDs, explicit license, expected regions, bounded triangles, determinism.
- [x] Viewer: load offline asset, normalize common coordinates, retain uterus schematic only; normal-based surface shading, faint body silhouette, lower detail while dragging if required. Preserve all identities, neutral/highlight states, zoom bounds, drag/click separation.
- [x] Validation: full tests and actual native-window orbit/zoom/organ/muscle evidence/None clearing recording; check clip duration/decode/hash.
- [ ] Freeze source, push existing feature branch, independent verifier fresh process/actions/video at exact SHA. Fix actionable findings once, preserve failure history, synchronize Evidence/Function/Mission/Verification receipts. Remote media pending remains explicit.

Review focus: orientation/mirroring; missing atlas region fallback disclosure; muscle surfaces obscuring organs; selection after orbit; source licensing not confused with code licensing or drug evidence. No inferred clinical effect/medical dataset change.

