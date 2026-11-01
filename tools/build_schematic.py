"""Generate the Focus Buddy KiCad 9 schematic from tools/netlist.py.

Every pin gets a short wire stub and a net label, so connectivity is exactly
the netlist the PCB was built from. Symbols are copied from the stock KiCad
libraries; the XIAO symbol is generated.

  python3 build_schematic.py OUT_DIR      (inside kicad/kicad:9.0)
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist as N  # noqa: E402

SYMDIR = "/usr/share/kicad/symbols/"
ROOT_UUID = str(uuid.uuid4())


# ------------------------------------------------------------------ s-expressions
def parse(text):
    toks, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            toks.append(c); i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    buf.append(text[j:j + 2]); j += 2
                else:
                    buf.append(text[j]); j += 1
            toks.append(('"', "".join(buf))); i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            toks.append(text[i:j]); i = j
    stack = [[]]
    for t in toks:
        if t == "(":
            stack.append([])
        elif t == ")":
            e = stack.pop(); stack[-1].append(e)
        else:
            stack[-1].append(t)
    return stack[0][0]


def dump(e, ind=0):
    if isinstance(e, tuple):
        return '"' + e[1] + '"'
    if isinstance(e, str):
        return e
    if all(not isinstance(x, list) for x in e):
        return "(" + " ".join(dump(x) for x in e) + ")"
    pad = "\t" * (ind + 1)
    head = [dump(x) for x in e if not isinstance(x, list)]
    out = "(" + " ".join(head)
    for x in e:
        if isinstance(x, list):
            out += "\n" + pad + dump(x, ind + 1)
    return out + "\n" + "\t" * ind + ")"


def Q(s):
    return ('"', s)


def U():
    return ["uuid", Q(str(uuid.uuid4()))]


_libs = {}


def lib_symbol(lib, name):
    if lib not in _libs:
        _libs[lib] = parse(open(SYMDIR + lib + ".kicad_sym").read())
    for e in _libs[lib]:
        if isinstance(e, list) and e[0] == "symbol" and e[1][1] == name:
            if any(isinstance(x, list) and x[0] == "extends" for x in e):
                raise SystemExit(f"{lib}:{name} extends another symbol; pick the base symbol")
            out = [x for x in e]
            out[1] = Q(f"{lib}:{name}")
            return out
    raise SystemExit(f"symbol {lib}:{name} not found")


def pins_of(sym):
    """pin number -> (x, y, angle) in library coordinates (y up)."""
    res = {}

    def walk(e):
        if isinstance(e, list):
            if e and e[0] == "pin":
                at = next(x for x in e if isinstance(x, list) and x[0] == "at")
                num = next(x for x in e if isinstance(x, list) and x[0] == "number")
                res[num[1][1]] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
            for x in e:
                walk(x)
    walk(sym)
    return res


def xiao_symbol():
    """Box symbol, pins 1-7 left (D0..D6), 8-14 right (D7..5V) like the pinout card."""
    name = "focusbuddy:XIAO_ESP32C3"
    pins = []
    for i in range(14):
        num = str(i + 1)
        label = N.XIAO_PIN_NAMES[num]
        if i < 7:
            x, y, ang = -15.24, 7.62 - 2.54 * i, 0
        else:
            x, y, ang = 15.24, -7.62 + 2.54 * (i - 7), 180
        etype = "power_in" if label in ("3V3", "GND", "5V") else "bidirectional"
        etype = "passive"  # keep ERC quiet about undriven power: the XIAO regulates its own 3V3
        pins.append(["pin", etype, "line", ["at", str(x), str(y), str(ang)], ["length", "3.81"],
                     ["name", Q(label), ["effects", ["font", ["size", "1.27", "1.27"]]]],
                     ["number", Q(num), ["effects", ["font", ["size", "1.27", "1.27"]]]]])
    return ["symbol", Q(name), ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
            ["property", Q("Reference"), Q("U"), ["at", "0", "11.43", "0"], ["effects", ["font", ["size", "1.27", "1.27"]]]],
            ["property", Q("Value"), Q("XIAO_ESP32C3"), ["at", "0", "-11.43", "0"], ["effects", ["font", ["size", "1.27", "1.27"]]]],
            ["property", Q("Footprint"), Q("focusbuddy:Seeed_XIAO_THT"), ["at", "0", "0", "0"], ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]],
            ["property", Q("Datasheet"), Q("https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/"), ["at", "0", "0", "0"], ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]],
            ["symbol", Q("XIAO_ESP32C3_0_1"),
             ["rectangle", ["start", "-11.43", "10.16"], ["end", "11.43", "-10.16"],
              ["stroke", ["width", "0.254"], ["type", "default"]], ["fill", ["type", "background"]]]],
            ["symbol", Q("XIAO_ESP32C3_1_1")] + pins]


# ------------------------------------------------------------------ part -> symbol
SYM = {
    "U1": None,
    "J1": ("Connector_Generic", "Conn_01x08"),
    "J2": ("Connector_Generic", "Conn_01x02"),
    "J3": ("Connector_Generic", "Conn_01x02"),
    "BZ1": ("Device", "Buzzer"),
    "Q1": ("Transistor_BJT", "Q_NPN_EBC"),
    "D1": ("Device", "D"),
    "R1": ("Device", "R"), "R2": ("Device", "R"), "R3": ("Device", "R"), "R4": ("Device", "R"),
    "R5": ("Device", "R"), "R6": ("Device", "R"), "R7": ("Device", "R"),
    "C1": ("Device", "C"),
    "SW1": ("Switch", "SW_Push"), "SW2": ("Switch", "SW_Push"), "SW3": ("Switch", "SW_Push"),
}

# schematic placement (mm, A4 landscape, y down), grouped by function
PLACE = {
    "U1": (110.49, 90.17),
    "J1": (186.69, 80.01),
    "SW1": (35.56, 63.5), "R4": (35.56, 50.8),
    "SW2": (60.96, 63.5), "R5": (60.96, 50.8),
    "SW3": (86.36, 63.5), "R6": (86.36, 50.8),
    "J2": (35.56, 129.54), "J3": (35.56, 147.32),
    "R1": (67.31, 129.54), "R2": (67.31, 147.32), "C1": (96.52, 147.32),
    "R3": (124.46, 140.97), "Q1": (162.56, 140.97), "R7": (157.48, 156.21),
    "BZ1": (175.26, 125.73), "D1": (190.5, 125.73),
}
ROT = {"R4": 0, "R5": 0, "R6": 0, "R1": 90, "R2": 90, "C1": 0, "R7": 0, "R3": 90}
# reference/value text position relative to the symbol origin (dx, dy); value goes 2.54 below
REFPOS = {
    "SW1": (-2.54, 5.08), "SW2": (-2.54, 5.08), "SW3": (-2.54, 5.08),
    "R1": (-2.54, -5.08), "R2": (-2.54, -5.08), "R3": (-2.54, -5.08),
    "Q1": (5.08, -1.27), "BZ1": (-5.08, 6.35), "D1": (-2.54, -6.35),
    "J1": (5.08, -2.54), "J2": (5.08, -1.27), "J3": (5.08, -1.27), "U1": (-6.35, -15.24),
}

NOTES = [
    (20.32, 30.48, "BUTTONS: active low, 10k pull-ups. A/B on GPIO2/3 wake the ESP32-C3 from deep sleep."),
    (20.32, 116.84, "BATTERY (optional): LiPo on J2; J3 = wires to XIAO BAT+/BAT- pads. 1M/1M divider -> ADC."),
    (137.16, 116.84, "BUZZER: NPN low-side driver, 1N4148 flyback, 10k base pull-down."),
    (165.1, 60.96, "E-PAPER: Waveshare 2.9in V2 (SSD1680) via its 8-wire cable."),
]


def rot_pt(x, y, r):
    if r == 0:
        return x, y
    if r == 90:
        return -y, x
    if r == 180:
        return -x, -y
    return y, -x


def main(out):
    lib_syms, insts, wires, labels, ncs = [], [], [], [], []
    seen = {}
    for ref in N.PARTS:
        if SYM[ref] is None:
            s = xiao_symbol()
        else:
            s = lib_symbol(*SYM[ref])
        lid = s[1][1]
        if lid not in seen:
            seen[lid] = s
            lib_syms.append(s)
        sx, sy = PLACE[ref]
        r = ROT.get(ref, 0)
        val, fp = N.PARTS[ref][0], N.PARTS[ref][1]
        padnets = N.PARTS[ref][6]
        pins = pins_of(seen[lid])
        inst = ["symbol", ["lib_id", Q(lid)], ["at", f"{sx:.2f}", f"{sy:.2f}", str(r)], ["unit", "1"],
                ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], U()]
        off = 3.81 if ref.startswith(("R", "C", "D")) else 6.35
        lx, ly = (sx + off, sy) if r == 0 and ref[0] in "RC" else (sx, sy - off - 4)
        just_left = ref[0] in "RC" and r == 0
        if ref in REFPOS:
            lx, ly = sx + REFPOS[ref][0], sy + REFPOS[ref][1]
            just_left = True
        inst.append(["property", Q("Reference"), Q(ref), ["at", f"{lx:.2f}", f"{ly - 1.27:.2f}", str(r)],
                     ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left"] if just_left else ["justify"]]])
        inst.append(["property", Q("Value"), Q(val), ["at", f"{lx:.2f}", f"{ly + 1.27:.2f}", str(r)],
                     ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left"] if just_left else ["justify"]]])
        inst.append(["property", Q("Footprint"), Q(fp), ["at", f"{sx:.2f}", f"{sy:.2f}", "0"],
                     ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]])
        inst.append(["property", Q("Datasheet"), Q(""), ["at", f"{sx:.2f}", f"{sy:.2f}", "0"],
                     ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]])
        inst.append(["property", Q("Description"), Q(N.PARTS[ref][7]), ["at", f"{sx:.2f}", f"{sy:.2f}", "0"],
                     ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]])
        for num in pins:
            inst.append(["pin", Q(num), U()])
        inst = [x for x in inst if x != ["justify"]]
        inst = [[y for y in x if y != ["justify"]] if isinstance(x, list) else x for x in inst]
        inst.append(["instances", ["project", Q("focus-buddy"), ["path", Q("/" + ROOT_UUID), ["reference", Q(ref)], ["unit", "1"]]]])
        insts.append(inst)

        for num, (px, py, pa) in pins.items():
            rx, ry = rot_pt(px, py, r)
            ex, ey = sx + rx, sy - ry                     # pin end, schematic coords
            ang = (pa + r) % 360                          # direction pin -> body (lib frame)
            dx, dy = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}[int(ang)]
            net = padnets.get(num)
            if net is None or len(N.nets()[net]) < 2:
                ncs.append(["no_connect", ["at", f"{ex:.2f}", f"{ey:.2f}"], U()])
                continue
            L = 2.54
            tx, ty = ex + dx * L, ey + dy * L
            wires.append(["wire", ["pts", ["xy", f"{ex:.2f}", f"{ey:.2f}"], ["xy", f"{tx:.2f}", f"{ty:.2f}"]],
                          ["stroke", ["width", "0"], ["type", "default"]], U()])
            la = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            just = "left" if la in (0, 90) else "right"
            labels.append(["global_label", Q(net), ["shape", "passive"], ["at", f"{tx:.2f}", f"{ty:.2f}", str(la)],
                           ["fields_autoplaced", "yes"],
                           ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", just]], U(),
                           ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", f"{tx:.2f}", f"{ty:.2f}", "0"],
                            ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]]])

    texts = [["text", Q(t), ["exclude_from_sim", "no"], ["at", f"{x:.2f}", f"{y:.2f}", "0"],
              ["effects", ["font", ["size", "1.524", "1.524"], ["bold", "yes"]], ["justify", "left", "bottom"]], U()]
             for x, y, t in NOTES]
    sch = ["kicad_sch", ["version", "20250114"], ["generator", Q("focusbuddy_gen")], ["generator_version", Q("9.0")],
           ["uuid", Q(ROOT_UUID)], ["paper", Q("A4")],
           ["title_block", ["title", Q("Focus Buddy - e-ink Pomodoro desk companion")], ["date", Q("2026-11-01")],
            ["rev", Q("A")], ["company", Q("CERN-OHL-P")],
            ["comment", "1", Q("Generated from tools/netlist.py, same source as the PCB")]],
           ["lib_symbols"] + lib_syms] + insts + wires + labels + ncs + texts + [
           ["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
    path = os.path.join(out, "focus-buddy.kicad_sch")
    open(path, "w").write(dump(sch) + "\n")
    # project symbol library + library tables so the project opens cleanly anywhere
    xs = xiao_symbol()
    xs[1] = Q("XIAO_ESP32C3")
    open(os.path.join(out, "focusbuddy.kicad_sym"), "w").write(
        dump(["kicad_symbol_lib", ["version", "20241209"], ["generator", Q("focusbuddy_gen")],
              ["generator_version", Q("9.0")], xs]) + "\n")
    open(os.path.join(out, "sym-lib-table"), "w").write(
        '(sym_lib_table\n  (version 7)\n  (lib (name "focusbuddy")(type "KiCad")(uri "${KIPRJMOD}/focusbuddy.kicad_sym")(options "")(descr "Focus Buddy parts"))\n)\n')
    open(os.path.join(out, "fp-lib-table"), "w").write(
        '(fp_lib_table\n  (version 7)\n  (lib (name "focusbuddy")(type "KiCad")(uri "${KIPRJMOD}/focusbuddy.pretty")(options "")(descr "Focus Buddy footprints"))\n)\n')
    print("wrote", path, len(insts), "symbols", len(labels), "labels")


if __name__ == "__main__":
    main(sys.argv[1])
