"""Build the Focus Buddy PCB with the KiCad 9 pcbnew API.

  python3 build_pcb.py place  OUT_DIR   -> focus-buddy.kicad_pcb (unrouted) + .dsn
  python3 build_pcb.py finish OUT_DIR   -> imports .ses, pours GND, saves

Run inside the kicad/kicad:9.0 docker image (see tools/make_all.sh).
"""
import json
import math
import os
import sys

import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist as N  # noqa: E402

NAME = "focus-buddy"
OX, OY = 50.0, 50.0  # place the board away from the page corner


def P(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))


# ------------------------------------------------------------------ helpers
def seg(board, layer, a, b, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*b))
    s.SetLayer(layer)
    s.SetWidth(FromMM(w))
    board.Add(s)


def arc(board, layer, center, start, angle_deg, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetCenter(P(*center))
    s.SetStart(P(*start))
    s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T), True)
    s.SetLayer(layer)
    s.SetWidth(FromMM(w))
    board.Add(s)


def rounded_rect(board, layer, x0, y0, x1, y1, r, w=0.1):
    seg(board, layer, (x0 + r, y0), (x1 - r, y0), w)
    seg(board, layer, (x1, y0 + r), (x1, y1 - r), w)
    seg(board, layer, (x1 - r, y1), (x0 + r, y1), w)
    seg(board, layer, (x0, y1 - r), (x0, y0 + r), w)
    arc(board, layer, (x1 - r, y0 + r), (x1 - r, y0), 90, w)
    arc(board, layer, (x1 - r, y1 - r), (x1, y1 - r), 90, w)
    arc(board, layer, (x0 + r, y1 - r), (x0 + r, y1), 90, w)
    arc(board, layer, (x0 + r, y0 + r), (x0, y0 + r), 90, w)


def text(board, s, x, y, layer, size=1.2, thick=0.18, mirror=False, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(thick))
    t.SetMirrored(mirror)
    t.SetBold(bold)
    board.Add(t)


def make_xiao_footprint(board):
    """Seeed XIAO (any variant) as a through-hole part: 2x7 pins, 2.54 mm, rows 15.24 mm apart.
    Top view, USB at -y. Pads numbered counter-clockwise like Seeed's pinout."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("focusbuddy", "Seeed_XIAO_THT"))
    fp.SetLibDescription("Seeed Studio XIAO module on 2.54mm headers, through hole")
    fp.SetKeywords("XIAO ESP32C3 RP2040 SAMD21 nRF52840")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    for i in range(14):
        if i < 7:
            x, y = -7.62, -7.62 + 2.54 * i
        else:
            x, y = 7.62, 7.62 - 2.54 * (i - 7)
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i + 1))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if i == 0 else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(VECTOR2I(FromMM(1.7), FromMM(1.7)))
        pad.SetDrillSize(VECTOR2I(FromMM(1.0), FromMM(1.0)))
        pad.SetLayerSet(pcbnew.PAD.PTHMask())
        pad.SetFPRelativePosition(VECTOR2I(FromMM(x), FromMM(y)))
        fp.Add(pad)

    def fpline(layer, a, b, w):
        s = pcbnew.PCB_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(VECTOR2I(FromMM(a[0]), FromMM(a[1])))
        s.SetEnd(VECTOR2I(FromMM(b[0]), FromMM(b[1])))
        s.SetLayer(layer)
        s.SetWidth(FromMM(w))
        fp.Add(s)

    def fprect(layer, x0, y0, x1, y1, w):
        for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
            fpline(layer, a, b, w)

    fprect(pcbnew.F_SilkS, -8.95, -10.7, 8.95, 10.7, 0.15)
    fprect(pcbnew.F_Fab, -4.6, -12.0, 4.6, -9.2, 0.1)  # USB-C (fab only: it overhangs the edge)
    fprect(pcbnew.F_Fab, -8.75, -10.5, 8.75, 10.5, 0.1)
    fprect(pcbnew.F_CrtYd, -9.2, -12.3, 9.2, 10.95, 0.05)
    # pin 1 marker
    fpline(pcbnew.F_SilkS, (-10.2, -8.4), (-10.2, -6.8), 0.2)
    fp.Reference().SetFPRelativePosition(VECTOR2I(0, FromMM(-2)))
    fp.Value().SetFPRelativePosition(VECTOR2I(0, FromMM(2)))
    fp.Value().SetLayer(pcbnew.F_Fab)
    return fp


_IO = None


def save_fp(libdir, fp):
    global _IO
    if _IO is None:
        _IO = pcbnew.PCB_IO_KICAD_SEXPR()
    _IO.FootprintSave(libdir, fp)


def pad_center(fp):
    xs = [p.GetPosition().x for p in fp.Pads()]
    ys = [p.GetPosition().y for p in fp.Pads()]
    return (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2


def place(fp, cx, cy, rot, side):
    fp.SetPosition(P(0, 0))
    if side == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    pcx, pcy = pad_center(fp)
    tgt = P(cx, cy)
    fp.Move(VECTOR2I(tgt.x - pcx, tgt.y - pcy))


def stage_place(out):
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(FromMM(0.4))
    nc.SetClearance(FromMM(0.25))
    nc.SetViaDiameter(FromMM(0.8))
    nc.SetViaDrill(FromMM(0.4))
    ds.m_TrackMinWidth = FromMM(0.2)
    ds.m_ViasMinSize = FromMM(0.6)
    ds.m_MinThroughDrill = FromMM(0.3)
    ds.m_CopperEdgeClearance = FromMM(0.4)

    tb = board.GetTitleBlock()
    tb.SetTitle("Focus Buddy - e-ink Pomodoro desk companion")
    tb.SetRevision("A")
    tb.SetDate("2026-11-01")
    tb.SetCompany("open hardware, CERN-OHL-P")

    # nets
    netobjs = {}
    for name in sorted(N.nets()):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netobjs[name] = ni

    # outline + cable slot
    rounded_rect(board, pcbnew.Edge_Cuts, 0, 0, N.BOARD_W, N.BOARD_H, N.CORNER_R, 0.1)
    x0, y0, x1, y1 = N.CABLE_SLOT
    r = (x1 - x0) / 2
    seg(board, pcbnew.Edge_Cuts, (x0, y0 + r), (x0, y1 - r))
    seg(board, pcbnew.Edge_Cuts, (x1, y0 + r), (x1, y1 - r))
    arc(board, pcbnew.Edge_Cuts, (x0 + r, y0 + r), (x0, y0 + r), 180)  # top cap
    arc(board, pcbnew.Edge_Cuts, (x0 + r, y1 - r), (x1, y1 - r), 180)  # bottom cap

    # custom XIAO footprint, saved to the project library too
    libdir = os.path.join(out, "focusbuddy.pretty")
    os.makedirs(libdir, exist_ok=True)
    xiao = make_xiao_footprint(board)
    save_fp(libdir, xiao)

    placed = {}
    for ref, (val, fpname, cx, cy, rot, side, padnets, desc, _pn) in N.PARTS.items():
        lib, name = fpname.split(":")
        if lib == "focusbuddy":
            fp = pcbnew.FOOTPRINT(xiao)
        else:
            fp = pcbnew.FootprintLoad(N.KLIB + lib + ".pretty", name)
            # keep a copy in the project library so the project is self-contained
            save_fp(libdir, fp)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(val)
        board.Add(fp)
        place(fp, cx, cy, rot, side)
        for pad in fp.Pads():
            n = padnets.get(pad.GetNumber())
            if n:
                pad.SetNet(netobjs[n])
        placed[ref] = fp

    # XIAO orientation search: USB end (pads 1 & 14) must face +x (board edge)
    u1 = placed["U1"]
    cx, cy = N.PARTS["U1"][2:4]
    for rot in (0, 90, 180, 270):
        u1.SetOrientationDegrees(rot)
        pcx, pcy = pad_center(u1)
        t = P(cx, cy)
        u1.Move(VECTOR2I(t.x - pcx, t.y - pcy))
        pads = {p.GetNumber(): p.GetPosition() for p in u1.Pads()}
        if pads["1"].x > pads["7"].x and abs(pads["1"].y - pads["7"].y) < FromMM(0.1):
            break
    pads = {p.GetNumber(): p.GetPosition() for p in u1.Pads()}
    assert pads["1"].y > pads["14"].y, "XIAO chirality wrong"
    print("U1 rotation", u1.GetOrientationDegrees(), "pad1", ToMM(pads["1"].x) - OX, ToMM(pads["1"].y) - OY)

    # mounting holes
    for i, (hx, hy) in enumerate(N.MOUNT_HOLES):
        fp = pcbnew.FootprintLoad(N.KLIB + "MountingHole.pretty", "MountingHole_3.2mm_M3")
        fp.SetReference(f"H{i + 1}")
        fp.Reference().SetVisible(False)
        fp.SetBoardOnly(True)
        board.Add(fp)
        fp.SetPosition(P(hx, hy))

    # tidy reference text: put refs on the silk centred on the part, values on fab
    for ref, fp in placed.items():
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(VECTOR2I(FromMM(1.0), FromMM(1.0)))
        fp.Reference().SetTextThickness(FromMM(0.15))
    offsets = {"U1": (0, 0), "J1": (-3.2, 0), "J2": (0, -3.6), "J3": (-2.6, 0), "BZ1": (0, 0),
               "Q1": (0, -3.4), "D1": (0, -2.2), "R1": (0, -2.0), "R2": (0, -2.0), "C1": (0, 2.6),
               "R3": (0, 2.2), "R7": (0, 2.2), "R4": (0, -2.2), "R5": (0, -2.2), "R6": (0, -2.2),
               "SW1": (-5.5, 0), "SW2": (-5.5, 0), "SW3": (-5.5, 0)}
    for ref, (dx, dy) in offsets.items():
        cx, cy = N.PARTS[ref][2:4]
        fp = placed[ref]
        fp.Reference().SetPosition(P(cx + dx, cy + dy))
        fp.Reference().SetTextAngleDegrees(90 if ref in ("J1", "J3") else 0)

    BS, FS = pcbnew.B_SilkS, pcbnew.F_SilkS
    # back silkscreen (mirrored so it reads correctly from the back)
    text(board, "FOCUS BUDDY  rev A", 30, 61.0, BS, 1.6, 0.25, True, True)
    text(board, "2026  CERN-OHL-P", 80, 61.0, BS, 1.0, 0.15, True)
    for i, lab in enumerate(["VCC", "GND", "DIN", "CLK", "CS", "DC", "RST", "BUSY"]):
        text(board, lab, 22.3, 24.0 - 8.89 + 2.54 * i, BS, 0.9, 0.14, True)
    text(board, "EPD cable", 18.0, 35.4, BS, 0.9, 0.14, True)
    text(board, "+", 64.2, 12.4, BS, 1.4, 0.25, True, True)
    text(board, "-", 67.8, 12.4, BS, 1.4, 0.25, True, True)
    text(board, "LiPo 3.7V", 73.5, 9.0, BS, 0.9, 0.14, True)
    text(board, "BAT+", 78.5, 25.6, BS, 0.8, 0.12, True)
    text(board, "BAT-", 78.5, 34.4, BS, 0.8, 0.12, True)
    text(board, "XIAO ESP32-C3  (USB-C to edge)", 94.0, 42.0, BS, 0.9, 0.14, True)
    text(board, "1N4148 band -> 3V3", 41.0, 29.0, BS, 0.8, 0.12, True)
    # front silkscreen
    text(board, "A start/pause", 33.0, 61.0, FS, 1.0, 0.15)
    text(board, "B skip/reset", 53.0, 61.0, FS, 1.0, 0.15)
    text(board, "C preset/mute", 73.0, 61.0, FS, 1.0, 0.15)
    text(board, "display goes here, glass toward you", 53.0, 23.0, FS, 1.4, 0.2)

    path = os.path.join(out, NAME + ".kicad_pcb")
    pcbnew.SaveBoard(path, board)
    ok = pcbnew.ExportSpecctraDSN(board, os.path.join(out, NAME + ".dsn"))
    print("saved", path, "dsn", ok)

    # positions for the enclosure model (front view, origin = board top-left)
    sw = {r: N.PARTS[r][2:4] for r in ("SW1", "SW2", "SW3")}
    u1p = {p.GetNumber(): (ToMM(p.GetPosition().x) - OX, ToMM(p.GetPosition().y) - OY) for p in u1.Pads()}
    json.dump({"board": [N.BOARD_W, N.BOARD_H], "holes": N.MOUNT_HOLES, "switches": sw,
               "xiao_pads": u1p, "display": N.DISPLAY_MODULE, "slot": N.CABLE_SLOT},
              open(os.path.join(out, "positions.json"), "w"), indent=1)


def stage_finish(out):
    path = os.path.join(out, NAME + ".kicad_pcb")
    board = pcbnew.LoadBoard(path)
    ses = os.path.join(out, NAME + ".ses")
    if os.path.exists(ses):  # Freerouting result, if you used it instead of tools/route_pcb.py
        if not pcbnew.ImportSpecctraSES(board, ses):
            raise SystemExit("SES import failed")
    for z in list(board.Zones()):
        board.Remove(z)
    # GND pour on both layers
    gnd = board.FindNet("GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(FromMM(0.3))
        z.SetMinThickness(FromMM(0.25))
        z.SetThermalReliefGap(FromMM(0.4))
        z.SetThermalReliefSpokeWidth(FromMM(0.5))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIsFilled(False)
        ol = z.Outline()
        ol.NewOutline()
        m = 0.5
        for x, y in [(m, m), (N.BOARD_W - m, m), (N.BOARD_W - m, N.BOARD_H - m), (m, N.BOARD_H - m)]:
            ol.Append(P(x, y))
        z.SetAssignedPriority(0)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    print(f"finished: {len(tracks)} tracks, {len(vias)} vias")


if __name__ == "__main__":
    {"place": stage_place, "finish": stage_finish}[sys.argv[1]](sys.argv[2])
