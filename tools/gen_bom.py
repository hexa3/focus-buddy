"""Write hardware/BOM.csv: PCB parts (from netlist.py) + everything off the board."""
import csv
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist as N  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

groups = OrderedDict()
for ref, p in N.PARTS.items():
    val, fp, desc, pn = p[0], p[1], p[7], p[8]
    key = (desc, fp.split(":")[1], pn)
    groups.setdefault(key, []).append(ref)

rows = []
for (desc, fp, pn), refs in groups.items():
    rows.append([",".join(refs), len(refs), desc, fp, pn if pn != "-" else ""])

OFFBOARD = [
    ("DISP1", 1, "Waveshare 2.9inch e-Paper Module (V2, 296x128, B/W, SSD1680) incl. 8-wire cable", "-", "Waveshare 2.9inch e-Paper Module"),
    ("-", 2, "1x7 male pin header 2.54 mm (usually included with the XIAO)", "-", ""),
    ("-", 1, "PCB 106 x 64 mm, 2 layer, 1.6 mm, HASL (order the Gerber zip)", "-", "JLCPCB / PCBWay"),
    ("-", 4, "M3 x 20 mm screw (pan or socket head, self-tapping into PLA, or machine screw with heat-set inserts)", "-", ""),
    ("-", 1, "3D-printed front shell (stl/focus-buddy-front.stl)", "-", ""),
    ("-", 1, "3D-printed back cover (stl/focus-buddy-back.stl)", "-", ""),
    ("-", 3, "3D-printed button caps (stl/focus-buddy-caps.stl)", "-", ""),
    ("-", 1, "3D-printed stand (stl/focus-buddy-stand.stl), optional", "-", ""),
    ("-", 1, "Double-sided foam tape, ~70 x 5 mm (holds the display glass to the window)", "-", ""),
    ("BT1", 1, "OPTIONAL 3.7 V LiPo, 400-1000 mAh, JST-PH 2.0 plug, max 40 x 30 x 6 mm. CHECK POLARITY", "-", ""),
    ("-", 1, "USB-C cable (data capable, for flashing)", "-", ""),
]
for r in OFFBOARD:
    rows.append(list(r))

out = os.path.join(ROOT, "hardware/BOM.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Refs", "Qty", "Description", "Footprint", "Part no. / search term"])
    w.writerows(rows)
print(open(out).read())
