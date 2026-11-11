"""Derive offline Web anatomy data from the pinned BodyParts3D assets.

The canonical organ bundle stays at ``assets/anatomy/bodyparts3d.json`` and is
not modified. This tool:

1. copies that file byte-for-byte to ``assets/web/data/bodyparts3d.json`` so the
   embedded page records exactly which bundle supplied the organs; and
2. derives ``assets/web/data/bodyparts3d.mjs`` with a deterministic, explicit ES
   module (the page cannot ``fetch()`` under its ``connect-src 'none'`` CSP).

The body surface needs one extra step. The organ bundle's ``shell`` region is a
12000-face uniform-grid clustering of the FMA7163 skin STL; at that budget the
grid is far coarser than the source and connects distant vertices, producing
metre-long triangles. Rendering it as skin shows spikes rather than a body, so
the Web shell is re-derived from the same pinned FMA7163 STL with a finer
deterministic grid (12 mm). Geometry is still the real BodyParts3D surface; no
vertices are invented. The source file's SHA256 is recorded in the page data and
in ``assets/web/ATTRIBUTION.md``.

Run from the repository root:

    python tools/build_web_anatomy.py
    python tools/build_web_anatomy.py --check
    python tools/build_web_anatomy.py --skin-stl <FMA7163.stl>

Build-only requirements: Python 3.14 with numpy (bundled in this workspace) and
the pinned ``FMA7163.stl`` from the BodyParts3D mirror. Runtime needs neither.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets' / 'anatomy' / 'bodyparts3d.json'
WEB_DATA = ROOT / 'assets' / 'web' / 'data'
COPIED_JSON = WEB_DATA / 'bodyparts3d.json'
MODULE_JS = WEB_DATA / 'bodyparts3d.mjs'

SCALE = 0.001
DECIMALS = 5
SKIN_CELL_MM = 12.0
SKIN_REGION = 'shell'

# Local development copies of the pinned upstream skin STL. The file is not
# committed (79 MB); build output is, so runtime never needs it.
SKIN_CANDIDATES = (
    ROOT / 'assets' / 'anatomy' / 'upstream' / 'FMA7163.stl',
    ROOT.parents[1] / '_evidence' / 'CEL-DRUG-20261105-DEV-08' / 'upstream' / 'FMA7163.stl',
)


def _connectivity(faces):
    """Return per-face neighbours across edges used by exactly two faces."""
    edge_uses = collections.defaultdict(list)
    for index, (a, b, c) in enumerate(faces):
        for u, v in ((a, b), (b, c), (c, a)):
            edge_uses[(min(u, v), max(u, v))].append((index, u, v))
    neighbours = collections.defaultdict(list)
    for uses in edge_uses.values():
        if len(uses) != 2:
            continue
        (i, u1, v1), (j, u2, v2) = uses
        same = (u1 == u2 and v1 == v2)
        neighbours[i].append((j, same))
        neighbours[j].append((i, same))
    return neighbours


def orient_faces(faces):
    """Propagate a consistent winding, then keep the source's global facing.

    Uniform-grid welding creates a handful of non-manifold edges; only edges
    used by exactly two faces are used for propagation. The global direction is
    chosen to disagree with as few source triangles as possible, so the raw
    STL's outward convention is preserved rather than re-invented.
    """
    neighbours = _connectivity(faces)
    flip = [None] * len(faces)
    for seed in range(len(faces)):
        if flip[seed] is not None:
            continue
        flip[seed] = False
        queue = collections.deque([seed])
        while queue:
            i = queue.popleft()
            for j, same in neighbours[i]:
                want = flip[i] ^ same
                if flip[j] is None:
                    flip[j] = want
                    queue.append(j)
    if sum(1 for value in flip if value) * 2 > len(flip):
        flip = [not value for value in flip]
    return flip


def _convert_points(points, cx, cy, z0):
    """Source mm (x left, y posterior, z superior) -> metres (y up, z anterior).

    The map (x, z, -y) is orientation preserving, so outward source winding
    remains outward for Three.js front faces.
    """
    out = []
    for x, y, z in points:
        out.extend((
            round((float(x) - cx) * SCALE, DECIMALS),
            round((float(z) - z0) * SCALE, DECIMALS),
            round((cy - float(y)) * SCALE, DECIMALS),
        ))
    return out


def _indices_from_faces(faces, flips):
    indices = []
    for (a, b, c), reversed_ in zip(faces, flips):
        if reversed_:
            b, c = c, b
        indices.extend((int(a), int(b), int(c)))
    return indices


def cluster_skin_stl(path, cell_mm):
    """Deterministic uniform-grid reduction of the real FMA7163 skin STL.

    The grid size is fixed (not budget-searched) so the result is stable and
    never collapses to metre-long bridging triangles.
    """
    raw = path.read_bytes()
    triangle_count = struct.unpack_from('<I', raw, 80)[0]
    if len(raw) != 84 + triangle_count * 50:
        raise ValueError(f'Invalid binary STL: {path}')
    dtype = np.dtype([('normal', '<3f4'), ('vertices', '<9f4'), ('attribute', '<u2')])
    record = np.frombuffer(raw, dtype=dtype, count=triangle_count, offset=84)
    vertices = record['vertices'].reshape(-1, 3).astype(np.float64)
    origin = vertices.min(axis=0)
    keys = np.floor((vertices - origin) / cell_mm).astype(np.int32)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    face_bins = inverse.reshape(-1, 3)
    keep = ((face_bins[:, 0] != face_bins[:, 1]) &
            (face_bins[:, 1] != face_bins[:, 2]) &
            (face_bins[:, 0] != face_bins[:, 2]))
    faces = face_bins[keep]
    faces = np.unique(np.sort(faces, axis=1), axis=0)

    counts = np.bincount(inverse, minlength=len(unique))
    points = np.stack([
        np.bincount(inverse, weights=vertices[:, axis], minlength=len(unique))
        / np.maximum(counts, 1)
        for axis in range(3)
    ], axis=1)

    edges = np.stack([
        np.linalg.norm(points[faces[:, 0]] - points[faces[:, 1]], axis=1),
        np.linalg.norm(points[faces[:, 1]] - points[faces[:, 2]], axis=1),
        np.linalg.norm(points[faces[:, 2]] - points[faces[:, 0]], axis=1),
    ], axis=1)
    stats = {
        'sourceTriangles': int(triangle_count),
        'sourceVertices': int(len(vertices)),
        'gridMm': cell_mm,
        'vertices': int(len(points)),
        'faces': int(len(faces)),
        'medianEdgeMm': round(float(np.median(edges)), 3),
        'maxEdgeMm': round(float(edges.max()), 3),
    }
    return [tuple(float(v) for v in point) for point in points], [tuple(int(i) for i in face) for face in faces], stats


def build_document(source_bytes, skin_path):
    data = json.loads(source_bytes.decode('utf-8'))
    json_shell = next(part for part in data['parts'] if part['region'] == SKIN_REGION)

    if skin_path is not None:
        skin_points, skin_faces, skin_stats = cluster_skin_stl(skin_path, SKIN_CELL_MM)
        skin_sha = hashlib.sha256(skin_path.read_bytes()).hexdigest()
        skin_source = skin_path.name
    else:
        skin_points = [tuple(v) for v in json_shell['vertices']]
        skin_faces = [tuple(int(i) - 1 for i in face) for face in json_shell['faces']]
        skin_stats = {'source': 'bundled-json-shell'}
        skin_sha = None
        skin_source = 'assets/anatomy/bodyparts3d.json'

    sx = [point[0] for point in skin_points]
    sy = [point[1] for point in skin_points]
    sz = [point[2] for point in skin_points]
    cx = (min(sx) + max(sx)) / 2
    cy = (min(sy) + max(sy)) / 2
    z0 = min(sz)
    height = round((max(sz) - z0) * SCALE, DECIMALS)

    parts = [{
        'region': SKIN_REGION,
        'source': skin_source,
        'sourceSha256': skin_sha,
        'sourceIds': ['FMA7163'],
        'sourceName': 'skin',
        'decimation': skin_stats,
        'positions': _convert_points(skin_points, cx, cy, z0),
        'indices': _indices_from_faces(skin_faces, orient_faces(skin_faces)),
    }]
    for part in data['parts']:
        if part['region'] == SKIN_REGION:
            continue
        faces = [tuple(int(i) - 1 for i in face) for face in part['faces']]
        parts.append({
            'region': part['region'],
            # Upstream identity of this mesh part. The viewer uses these ids to
            # label individual muscle heads; no geometry is inferred from them.
            'sourceIds': list(part.get('source_ids', [])),
            'sourceName': (part.get('names') or [''])[0],
            'positions': _convert_points(part['vertices'], cx, cy, z0),
            'indices': _indices_from_faces(faces, orient_faces(faces)),
        })

    return {
        'source': 'BodyParts3D 3.0 (20110915) via pinned Moerman binary mirror',
        'sourceCommit': data['source_commit'],
        'license': data.get('license', 'CC-BY-SA-2.1-JP'),
        'sourceCoordinateSystem': data.get('coordinate_system', ''),
        'adaptation': data.get('adaptation', ''),
        'viewerCoordinateSystem': 'metres; x patient-left, y superior, z anterior',
        'height': height,
        'shellSource': {
            'file': skin_source,
            'sha256': skin_sha,
            'gridMm': SKIN_CELL_MM if skin_path is not None else None,
            'decimation': skin_stats,
        },
        'parts': parts,
        'derivation': (
            'Presentation only: unit/axis conversion, local winding repair and '
            'a fixed 12 mm grid reduction of the skin surface; organs keep the '
            'bundled selection. Not clinically validated.'
        ),
    }


def module_source(document):
    body = json.dumps(document, ensure_ascii=False, separators=(',', ':'))
    return (
        '// Generated by tools/build_web_anatomy.py. Do not edit by hand.\n'
        '// Geometry: BodyParts3D, CC BY-SA 2.1 Japan. See assets/web/ATTRIBUTION.md.\n'
        f'export const ANATOMY = {body};\n'
    )


def outputs(source_bytes, skin_path):
    document = build_document(source_bytes, skin_path)
    return {
        COPIED_JSON: source_bytes,
        MODULE_JS: module_source(document).encode('utf-8'),
    }


def resolve_skin(explicit):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f'skin STL not found: {path}')
        return path
    for candidate in SKIN_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='verify generated files match the source bundle')
    parser.add_argument('--skin-stl', help='pinned FMA7163.stl used for the body surface')
    args = parser.parse_args(argv)

    source_bytes = SOURCE.read_bytes()
    skin_path = resolve_skin(args.skin_stl)
    if skin_path is None:
        raise SystemExit(
            'FMA7163.stl not found. Pass --skin-stl <path>; the file is the pinned '
            'BodyParts3D skin STL, not committed because it is 79 MB.')
    expected = outputs(source_bytes, skin_path)
    WEB_DATA.mkdir(parents=True, exist_ok=True)

    stale = []
    for path, payload in expected.items():
        if args.check:
            if not path.exists() or path.read_bytes() != payload:
                stale.append(path)
        else:
            path.write_bytes(payload)

    if args.check:
        if stale:
            for path in stale:
                print(f'stale: {path.relative_to(ROOT)}', file=sys.stderr)
            return 1
        print('web anatomy data is current')
        return 0

    print(f'source  {SOURCE.relative_to(ROOT)}  sha256={sha256(SOURCE)}')
    print(f'skin    {skin_path}  sha256={sha256(skin_path)}')
    for path in expected:
        print(f'wrote   {path.relative_to(ROOT)}  sha256={sha256(path)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
