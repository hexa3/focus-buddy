"""Small 2-layer grid autorouter for the Focus Buddy board (A*, rip-up & retry).

  python3 route_pcb.py BOARD.kicad_pcb      (inside kicad/kicad:9.0)

Rules baked into the grid: 0.4 mm tracks, 0.25 mm clearance, 0.8/0.4 mm vias,
0.6 mm copper-to-edge. Preferred directions: F.Cu vertical, B.Cu horizontal.
KiCad's DRC is the referee afterwards; this only has to get close.
"""
import heapq
import math
import sys

import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

OX, OY = 50.0, 50.0
G = 0.25                     # grid pitch, mm
TRACK_W = 0.4
CLR = 0.25
VIA_D, VIA_DRILL = 0.8, 0.4
EDGE_CLR = 0.6               # copper to board edge (rule 0.4 + margin)
M = 0.06                     # discretisation margin

PAD_KEEP = CLR + TRACK_W / 2 + M          # foreign pad copper edge -> our centreline
TRACK_HALO = TRACK_W + CLR + M            # our centreline -> foreign centreline
VIA_HALO = VIA_D / 2 + CLR + TRACK_W / 2 + M
VIA_EXTRA = VIA_D / 2 - TRACK_W / 2       # extra room a via needs beyond a track
VIA_COST = 9.0
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)

FREE, HARD = -1, -2


class Grid:
    def __init__(self, w, h):
        self.nx, self.ny = int(w / G) + 1, int(h / G) + 1
        self.n = self.nx * self.ny
        self.own = [[FREE] * self.n for _ in LAYERS]

    def idx(self, ix, iy):
        return iy * self.nx + ix

    def xy(self, i):
        return (i % self.nx) * G, (i // self.nx) * G

    def cell(self, x, y):
        return int(round(x / G)), int(round(y / G))

    def mark_disc(self, layer, x, y, r, net, hard_if_foreign=True):
        cx, cy = self.cell(x, y)
        rc = int(math.ceil(r / G)) + 1
        own = self.own[layer]
        for iy in range(max(0, cy - rc), min(self.ny, cy + rc + 1)):
            for ix in range(max(0, cx - rc), min(self.nx, cx + rc + 1)):
                if (ix * G - x) ** 2 + (iy * G - y) ** 2 <= r * r:
                    i = iy * self.nx + ix
                    o = own[i]
                    if o == FREE:
                        own[i] = net
                    elif o != net and o != HARD:
                        own[i] = HARD

    def mark_rect(self, layer, x0, y0, x1, y1, infl, net):
        """rect copper [x0,x1]x[y0,y1] inflated by infl (rounded corners)."""
        own = self.own[layer]
        for iy in range(max(0, int((y0 - infl) / G) - 1), min(self.ny, int((y1 + infl) / G) + 2)):
            for ix in range(max(0, int((x0 - infl) / G) - 1), min(self.nx, int((x1 + infl) / G) + 2)):
                px, py = ix * G, iy * G
                dx = max(x0 - px, 0, px - x1)
                dy = max(y0 - py, 0, py - y1)
                if dx * dx + dy * dy <= infl * infl:
                    i = iy * self.nx + ix
                    o = own[i]
                    if o == FREE:
                        own[i] = net
                    elif o != net and o != HARD:
                        own[i] = HARD


def board_geometry(board):
    pads = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            pos = p.GetPosition()
            bb = p.GetBoundingBox()
            pads.append(dict(
                net=p.GetNetname(), x=ToMM(pos.x) - OX, y=ToMM(pos.y) - OY,
                x0=ToMM(bb.GetLeft()) - OX, y0=ToMM(bb.GetTop()) - OY,
                x1=ToMM(bb.GetRight()) - OX, y1=ToMM(bb.GetBottom()) - OY,
                round=p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE,
                r=ToMM(p.GetSizeX()) / 2, drill=ToMM(p.GetDrillSizeX()), ref=fp.GetReference(), num=p.GetNumber(),
                obj=p))
    return pads


def build_static(netidx, pads, bw, bh, cr, slot, holes):
    g = Grid(bw, bh)
    # board edge (rounded rectangle) and slot
    for L in range(2):
        own = g.own[L]
        for iy in range(g.ny):
            for ix in range(g.nx):
                x, y = ix * G, iy * G
                e = EDGE_CLR
                bad = x < e or y < e or x > bw - e or y > bh - e
                # rounded corners
                for cx, cy in ((cr, cr), (bw - cr, cr), (cr, bh - cr), (bw - cr, bh - cr)):
                    if (x - cx) * (cx - bw / 2) > 0 and (y - cy) * (cy - bh / 2) > 0:
                        if math.hypot(x - cx, y - cy) > cr - e:
                            bad = True
                sx0, sy0, sx1, sy1 = slot
                if sx0 - e <= x <= sx1 + e and sy0 - e <= y <= sy1 + e:
                    bad = True
                if bad:
                    own[iy * g.nx + ix] = HARD
        for hx, hy in holes:
            g.mark_disc(L, hx, hy, 1.6 + 0.4 + TRACK_W / 2 + M, HARD)
    # pads: own copper + keepout for others
    for p in pads:
        k = netidx.get(p["net"], HARD)
        for L in range(2):
            if p["round"]:
                g.mark_disc(L, p["x"], p["y"], p["r"] + PAD_KEEP, k)
            else:
                g.mark_rect(L, p["x0"], p["y0"], p["x1"], p["y1"], PAD_KEEP, k)
    return g


def pad_cells(g, p):
    """grid cells whose centre lies inside the pad copper (route targets)."""
    out = []
    r = p["r"] * 0.8
    cx, cy = g.cell(p["x"], p["y"])
    rc = int(r / G) + 1
    for iy in range(cy - rc, cy + rc + 1):
        for ix in range(cx - rc, cx + rc + 1):
            if 0 <= ix < g.nx and 0 <= iy < g.ny and (ix * G - p["x"]) ** 2 + (iy * G - p["y"]) ** 2 <= r * r:
                out.append(iy * g.nx + ix)
    return out


DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


def astar(g, k, sources, targets, tx, ty):
    nx, ny, n = g.nx, g.ny, g.n
    own = g.own
    tset = set(targets)
    best = {}
    prev = {}
    h = []
    for s in sources:
        key = s
        best[key] = 0.0
        prev[key] = None
        i = s % n
        x, y = i % nx, i // nx
        heapq.heappush(h, (math.hypot(x - tx, y - ty) * 0.98, 0.0, key))
    vr = int(math.ceil(VIA_EXTRA / G))
    expanded = 0
    while h:
        f, gc, key = heapq.heappop(h)
        if gc > best.get(key, 1e18):
            continue
        L, i = divmod(key, n)
        if i in tset:
            path = []
            while key is not None:
                path.append(key)
                key = prev[key]
            return path[::-1]
        expanded += 1
        if expanded > 400000:
            return None
        x, y = i % nx, i // nx
        o = own[L]
        for dx, dy, c in DIRS:
            xx, yy = x + dx, y + dy
            if not (0 <= xx < nx and 0 <= yy < ny):
                continue
            j = yy * nx + xx
            v = o[j]
            if v != FREE and v != k:
                continue
            if dx and dy:  # no corner cutting
                a, b = o[y * nx + xx], o[yy * nx + x]
                if (a != FREE and a != k) or (b != FREE and b != k):
                    continue
            # preferred direction: F.Cu vertical, B.Cu horizontal
            pen = 1.0
            if L == 0 and dx and not dy:
                pen = 1.6
            elif L == 1 and dy and not dx:
                pen = 1.6
            nk = L * n + j
            ng = gc + c * pen
            if ng < best.get(nk, 1e18):
                best[nk] = ng
                prev[nk] = key
                heapq.heappush(h, (ng + math.hypot(xx - tx, yy - ty) * 0.98, ng, nk))
        # via
        L2 = 1 - L
        ok = True
        for oy in range(-vr, vr + 1):
            for ox in range(-vr, vr + 1):
                xx, yy = x + ox, y + oy
                if not (0 <= xx < nx and 0 <= yy < ny):
                    ok = False
                    break
                j = yy * nx + xx
                for LL in (0, 1):
                    v = own[LL][j]
                    if v != FREE and v != k:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            nk = L2 * n + i
            ng = gc + VIA_COST
            if ng < best.get(nk, 1e18):
                best[nk] = ng
                prev[nk] = key
                heapq.heappush(h, (ng + math.hypot(x - tx, y - ty) * 0.98, ng, nk))
    return None


def route_all(board, order, netidx, pads, static_fn):
    g = static_fn()
    n = g.n
    routes = {}
    failed = []
    for net in order:
        k = netidx[net]
        ps = [p for p in pads if p["net"] == net]
        # Prim-like order: start at the first pad, always connect the nearest unconnected pad
        connected = [ps[0]]
        todo = ps[1:]
        tree = set(L * n + c for c in pad_cells(g, ps[0]) for L in (0, 1))
        segs = []
        ok_net = True
        while todo:
            todo.sort(key=lambda p: min(math.hypot(p["x"] - q["x"], p["y"] - q["y"]) for q in connected))
            tgt = todo.pop(0)
            tc = pad_cells(g, tgt)
            tx, ty = tgt["x"] / G, tgt["y"] / G
            path = astar(g, k, list(tree), tc, tx, ty)
            if path is None:
                ok_net = False
                break
            segs.append((path, tgt))
            # occupy
            for key in path:
                L, i = divmod(key, n)
                x, y = g.xy(i)
                g.mark_disc(L, x, y, TRACK_HALO, k)
                tree.add(key)
            for a, b in zip(path, path[1:]):
                if a % n == b % n:  # via
                    x, y = g.xy(a % n)
                    for L in (0, 1):
                        g.mark_disc(L, x, y, VIA_HALO, k)
            for c in tc:
                tree.add(c)
                tree.add(n + c)
            connected.append(tgt)
        if ok_net:
            routes[net] = segs
        else:
            failed.append(net)
    return routes, failed, g


def emit(board, g, routes, netobjs):
    n = g.n
    count_t = count_v = 0
    for net, segs in routes.items():
        ni = netobjs[net]
        for path, _tgt in segs:
            pts = []
            for key in path:
                L, i = divmod(key, n)
                x, y = g.xy(i)
                pts.append((L, x, y))
            # split into runs per layer, simplify collinear
            run = [pts[0]]
            runs = []
            for p in pts[1:]:
                if p[0] != run[-1][0]:
                    runs.append(run)
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(VECTOR2I(FromMM(OX + p[1]), FromMM(OY + p[2])))
                    v.SetWidth(FromMM(VIA_D))
                    v.SetDrill(FromMM(VIA_DRILL))
                    v.SetNet(ni)
                    board.Add(v)
                    count_v += 1
                    run = [p]
                else:
                    run.append(p)
            runs.append(run)
            for run in runs:
                simp = [run[0]]
                for p in run[1:]:
                    if len(simp) >= 2:
                        a, b = simp[-2], simp[-1]
                        d1 = (round((b[1] - a[1]) / G), round((b[2] - a[2]) / G))
                        d2 = (round((p[1] - b[1]) / G), round((p[2] - b[2]) / G))
                        if d1[0] * d2[1] == d1[1] * d2[0] and d1[0] * d2[0] + d1[1] * d2[1] > 0:
                            simp[-1] = p
                            continue
                    simp.append(p)
                for a, b in zip(simp, simp[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(VECTOR2I(FromMM(OX + a[1]), FromMM(OY + a[2])))
                    t.SetEnd(VECTOR2I(FromMM(OX + b[1]), FromMM(OY + b[2])))
                    t.SetWidth(FromMM(TRACK_W))
                    t.SetLayer(LAYERS[a[0]])
                    t.SetNet(ni)
                    board.Add(t)
                    count_t += 1
    return count_t, count_v


def add_pad_stubs(board, g, routes, pads, netobjs):
    """Connect each path end/start cell to the exact pad centre (grid is off-centre)."""
    n = g.n
    for net, segs in routes.items():
        ps = [p for p in pads if p["net"] == net]
        for path, _ in segs:
            for key in (path[0], path[-1]):
                L, i = divmod(key, n)
                x, y = g.xy(i)
                p = min(ps, key=lambda q: math.hypot(q["x"] - x, q["y"] - y))
                if math.hypot(p["x"] - x, p["y"] - y) < 1e-3 or math.hypot(p["x"] - x, p["y"] - y) > p["r"]:
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(VECTOR2I(FromMM(OX + x), FromMM(OY + y)))
                t.SetEnd(VECTOR2I(FromMM(OX + p["x"]), FromMM(OY + p["y"])))
                t.SetWidth(FromMM(TRACK_W))
                t.SetLayer(LAYERS[L])
                t.SetNet(netobjs[net])
                board.Add(t)


def main(path):
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    import netlist as N
    board = pcbnew.LoadBoard(path)
    for t in list(board.GetTracks()):
        board.Remove(t)
    pads = board_geometry(board)
    nets = sorted({p["net"] for p in pads if p["net"]})
    nets = [n_ for n_ in nets if sum(1 for p in pads if p["net"] == n_) > 1]
    netidx = {n_: i for i, n_ in enumerate(nets)}
    netobjs = {n_: board.FindNet(n_) for n_ in nets}

    def span(n_):
        ps = [p for p in pads if p["net"] == n_]
        return (max(p["x"] for p in ps) - min(p["x"] for p in ps)) + (max(p["y"] for p in ps) - min(p["y"] for p in ps))

    order = sorted([n_ for n_ in nets if n_ not in ("GND", "+3V3")], key=span) + ["+3V3", "GND"]

    static = None

    def static_fn():
        nonlocal static
        g = build_static(netidx, pads, N.BOARD_W, N.BOARD_H, N.CORNER_R, N.CABLE_SLOT, N.MOUNT_HOLES)
        return g

    for attempt in range(8):
        routes, failed, g = route_all(board, order, netidx, pads, static_fn)
        print(f"attempt {attempt}: routed {len(routes)}/{len(nets)} failed={failed}", flush=True)
        if not failed:
            break
        order = failed + [n_ for n_ in order if n_ not in failed]
    nt, nv = emit(board, g, routes, netobjs)
    add_pad_stubs(board, g, routes, pads, netobjs)
    pcbnew.SaveBoard(path, board)
    print(f"tracks {nt}, vias {nv}, unrouted nets: {failed}")


if __name__ == "__main__":
    main(sys.argv[1])
