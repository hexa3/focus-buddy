"""Tiny CPU-only STL renderer (numpy + PIL, painter's algorithm, flat shading).

  python3 render_stl.py out.png yaw pitch  file.stl:#rrggbb [file2.stl:#rrggbb ...]

yaw/pitch in degrees. Used to make the preview images in hardware/cad/render
because the OpenSCAD docker image has no OpenGL.
"""
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw


def load_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:300]:
        v = [list(map(float, ln.split()[1:4])) for ln in data.decode().splitlines() if ln.strip().startswith("vertex")]
        return np.array(v, dtype=np.float32).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return arr["v"].reshape(-1, 3, 3).astype(np.float32)


def render(out, yaw, pitch, items, size=(1600, 1100), ss=2, bg=(246, 245, 241)):
    meshes = [(load_stl(p), np.array(c, float)) for p, c in items]
    allv = np.concatenate([m.reshape(-1, 3) for m, _ in meshes])
    center = (allv.min(0) + allv.max(0)) / 2
    y, p = np.radians(yaw), np.radians(pitch)
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    R = Rx @ Rz
    light = np.array([-0.4, 0.5, 0.75])
    light /= np.linalg.norm(light)
    W, H = size[0] * ss, size[1] * ss
    pv = (allv - center) @ R.T
    span = max(np.ptp(pv[:, 0]), np.ptp(pv[:, 1]))
    scale = 0.86 * min(W, H) / span
    polys = []
    for tris, col in meshes:
        t = (tris - center) @ R.T
        nrm = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ok = ln > 1e-9
        t, nrm = t[ok], nrm[ok] / ln[ok, None]
        shade = 0.35 + 0.65 * np.abs(nrm @ light)
        depth = t[:, :, 2].mean(1)
        cols = np.clip(col[None, :] * shade[:, None], 0, 255).astype(int)
        xy = np.stack([W / 2 + t[:, :, 0] * scale, H / 2 - t[:, :, 1] * scale], -1)
        polys.append((depth, xy, cols))
    depth = np.concatenate([d for d, _, _ in polys])
    xy = np.concatenate([x for _, x, _ in polys])
    cols = np.concatenate([c for _, _, c in polys])
    order = np.argsort(depth)  # far (most negative z) first; camera looks down -z
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    for i in order:
        c = tuple(cols[i])
        d.polygon([tuple(pt) for pt in xy[i]], fill=c, outline=c)
    im.resize(size, Image.LANCZOS).save(out)


if __name__ == "__main__":
    out, yaw, pitch = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    items = []
    for a in sys.argv[4:]:
        path, hexc = a.rsplit(":", 1)
        hexc = hexc.lstrip("#")
        items.append((path, tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4))))
    render(out, yaw, pitch, items)
