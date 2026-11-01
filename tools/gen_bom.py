"""Write hardware/BOM.csv: everything needed to build one Focus Buddy.

PCB parts come from tools/netlist.py (grouped by value so it reads like a
shopping list); everything else (display, mechanical, printed parts,
consumables, tools, software) is listed below.
"""
import csv
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist as N  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = ["Category", "Item", "Qty", "Refs", "Specification / notes", "Required", "Footprint", "Search term"]

# Shopping-friendly text for grouped PCB parts, keyed by (value, footprint)
GROUP_TEXT = {
    "10k": ("Resistor 10 kΩ", "1/4 W axial, 5 % or better. R4-R6 button pull-ups, R7 transistor base pull-down"),
    "1M": ("Resistor 1 MΩ", "1/4 W axial. Battery-voltage divider (fit even without a battery: keeps the ADC from floating)"),
    "1k": ("Resistor 1 kΩ", "1/4 W axial. Transistor base resistor"),
}
OPTIONAL_REFS = {"J2": "Optional (battery)", "J3": "Optional (battery)"}

ITEM = {"U1": "Seeed Studio XIAO ESP32-C3", "J1": "Pin header 1x8 male, 2.54 mm",
        "J2": "JST-PH 2-pin socket, vertical (B2B-PH-K)", "BZ1": "Buzzer 12 mm, 3 V, 7.6 mm pin spacing",
        "Q1": "NPN transistor 2N3904, TO-92", "D1": "Diode 1N4148", "C1": "Capacitor 100 nF ceramic",
        "SW": "Tactile switch 6x6 mm, 9.5 mm tall, through-hole"}


def natural(ref):
    i = len(ref.rstrip("0123456789"))
    return ref[:i], int(ref[i:] or 0)


rows = []
groups = OrderedDict()
for ref, p in N.PARTS.items():
    val, fp = p[0], p[1]
    key = (val if ref[0] in "RC" else p[7], fp)  # resistors by value; others by description
    groups.setdefault(key, []).append(ref)

for (val, fp), refs in groups.items():
    p = N.PARTS[refs[0]]
    desc, search = p[7], p[8]
    item, spec = GROUP_TEXT.get(val, (None, None)) if refs[0].startswith("R") else (None, None)
    if item is None:
        item, spec = ITEM.get(refs[0], ITEM.get(refs[0].rstrip("0123456789"), desc)), desc
    refs = sorted(refs, key=natural)
    qty = len(refs)
    if refs == ["J3"]:
        item, qty, spec = "No part: 2 solder holes", 0, "Short wire from the XIAO BAT+ pad lands here (see Consumables)"
    rows.append(["PCB electronics", item, qty, " ".join(refs), spec,
                 OPTIONAL_REFS.get(refs[0], "Yes"), fp.split(":")[1], "" if search == "-" else search])

rows += [
    ["Off-board electronics", "2.9\" e-paper module, Waveshare V2", 1, "DISP1",
     "296x128 black/white, SSD1680 driver, with its 8-wire cable (PH2.0 to female jumpers). "
     "Firmware also supports Waveshare V1 and WeAct 2.9\" (pick the matching build target)",
     "Yes", "-", "Waveshare 2.9inch e-Paper Module"],
    ["Off-board electronics", "Male pin header 1x7, 2.54 mm", 2, "-",
     "Mounts the XIAO on the PCB. Often included with the XIAO; buy if yours didn't come with them",
     "Yes", "-", "2.54mm 1x7 male header"],
    ["Off-board electronics", "Wi-Fi/BLE antenna (U.FL FPC)", 1, "-",
     "Included with the XIAO ESP32C3. Not needed for the timer, but keep it plugged in if you ever use radio",
     "Included", "-", ""],
    ["Off-board electronics", "LiPo battery 3.7 V", 1, "BT1",
     "400-1000 mAh, JST-PH 2.0 plug, max 40 x 30 x 6 mm to fit inside the back cover. "
     "CHECK POLARITY: red wire must go to J2 pin 1 (+, square pad)",
     "Optional", "-", "3.7V lipo JST PH 2.0 500mAh"],
    ["PCB", "Printed circuit board", 1, "-",
     "106 x 64 mm, 2 layers, 1.6 mm FR-4, HASL, any colour. Generate the Gerber zip with tools/make_all.sh "
     "(hardware/fab/focus-buddy-gerbers.zip). Fabs usually sell a minimum of 5",
     "Yes", "-", "JLCPCB / PCBWay / OSH Park"],
    ["Mechanical", "Screw M3 x 20 mm", 4, "-",
     "Pan or socket head. Self-taps into the 2.5 mm printed holes; clamps back cover, PCB and front shell together",
     "Yes", "-", "M3x20 screw"],
    ["Mechanical", "Heat-set insert M3 (instead of self-tapping)", 4, "-",
     "Only if you prefer metal threads: set pilot_d = 4.0 in enclosure.scad and re-export the front shell",
     "Optional", "-", "M3 heat set insert 4mm"],
    ["Mechanical", "Double-sided foam tape", "~10 cm", "-",
     "About 5 mm wide, 1 mm thick. Holds the display glass against the window",
     "Yes", "-", "double sided foam tape 1mm"],
    ["Mechanical", "Kapton or electrical tape", "a few cm", "-",
     "Holds the LiPo and antenna inside the back cover and insulates the battery",
     "Optional", "-", ""],
]

for name, qty, note in [
    ("Front shell", 1, "focus-buddy-front.stl. Prints face-down, no supports. 34.3 cm³ solid"),
    ("Back cover", 1, "focus-buddy-back.stl. Outside face down, no supports. 17.7 cm³ solid"),
    ("Button cap", 3, "focus-buddy-caps.stl (all 3 on one plate). Flange down. 1.0 cm³ solid in total"),
    ("Desk stand (15°)", 1, "focus-buddy-stand.stl. Prints on its side. 32.8 cm³ solid"),
]:
    rows.append(["Printed parts", name, qty, "-", note + ". STLs come from tools/make_all.sh",
                 "Optional" if "stand" in note else "Yes", "-", ""])

rows += [
    ["Consumables", "PLA or PETG filament", "~110 g", "-",
     "All parts together are 85.7 cm³, which is 106 g of PLA even printed 100 % solid. "
     "3 walls / 20 % infill uses less. A contrasting colour for the caps looks great",
     "Yes", "-", ""],
    ["Consumables", "Solder wire", "~1 m", "-", "0.6-0.8 mm, rosin core (63/37 leaded or SAC305 lead-free). About 80 joints",
     "Yes", "-", ""],
    ["Consumables", "Hook-up wire", "~5 cm", "-",
     "Thin (26-30 AWG), red. XIAO BAT+ pad to the J3 BAT+ hole. Only with a battery",
     "Optional", "-", ""],
    ["Consumables", "Flux pen", 1, "-", "Makes the XIAO header joints easier", "Optional", "-", ""],
    ["Tools", "Soldering iron", 1, "-", "Temperature-controlled, fine conical or chisel tip", "Yes", "-", ""],
    ["Tools", "Flush cutters", 1, "-",
     "Trim every lead on the front of the PCB flush: the display sits a few mm in front of it", "Yes", "-", ""],
    ["Tools", "Multimeter", 1, "-",
     "Check 3V3 is not shorted to GND before power-up; check LiPo polarity", "Yes", "-", ""],
    ["Tools", "3D printer (or a print service)", 1, "-",
     "Bed at least 115 x 75 mm (the front shell is 112.8 x 70.8 x 28 mm)", "Yes", "-", ""],
    ["Tools", "Screwdriver for M3", 1, "-", "Phillips or hex, matching your screws", "Yes", "-", ""],
    ["Tools", "Soldering iron insert tip", 1, "-", "Only for heat-set inserts", "Optional", "-", ""],
    ["Tools", "Tweezers / helping hands", 1, "-", "Nice to have for the XIAO headers", "Optional", "-", ""],
    ["Tools", "USB-C data cable + computer", 1, "-",
     "Must be a data cable, not charge-only. Powers the device and flashes the firmware", "Yes", "-", ""],
    ["Software", "PlatformIO", 1, "-", "pip install platformio, then `pio run -t upload` in firmware/", "Yes", "-", ""],
    ["Software", "Docker", 1, "-",
     "Runs tools/make_all.sh (KiCad 9 + OpenSCAD images) to generate Gerbers and STLs", "Yes", "-", ""],
    ["Software", "KiCad 9 / OpenSCAD", 1, "-", "Only to view or edit the design files", "Optional", "-", ""],
]

out = os.path.join(ROOT, "hardware/BOM.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    w.writerows(rows)
print(f"wrote {out}: {len(rows)} lines")
for r in rows:
    print(" | ".join(str(x) for x in r[:4]), "|", r[5])
