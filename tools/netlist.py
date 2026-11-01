"""Focus Buddy rev A: single source of truth for parts, nets and placement.

Used by build_pcb.py (runs inside the kicad/kicad:9.0 docker image) and by
build_schematic.py. Coordinates are board millimetres, origin = top-left
corner of the PCB *seen from the front* (the side facing the user), y down.

Sides:
  F = front (user-facing, behind the display): only the three buttons
  B = back  (inside the case): everything else
"""

BOARD_W, BOARD_H = 106.0, 64.0
CORNER_R = 3.0
MOUNT_HOLES = [(3.5, 3.5), (102.5, 3.5), (3.5, 60.5), (102.5, 60.5)]
# slot for the display cable to pass from the front to the back
CABLE_SLOT = (8.5, 12.0, 13.0, 36.0)  # x0, y0, x1, y1
# where the e-paper module sits in front of the board (for the CAD model)
DISPLAY_MODULE = dict(cx=53.0, cy=23.0, w=89.5, h=38.0)

KLIB = "/usr/share/kicad/footprints/"

# ref: (value, footprint "Lib:Name", center x, center y, rotation deg, side, {pad: net}, description, LCSC/part hint)
PARTS = {
    "U1":  ("XIAO ESP32-C3", "focusbuddy:Seeed_XIAO_THT", 94.0, 30.0, 0, "B",
            {"1": "BTN_A", "2": "BTN_B", "3": "VBAT_SENSE", "4": "EPD_BUSY", "5": "EPD_RST",
             "6": "EPD_DC", "7": "EPD_CS", "8": "BUZ_DRV", "9": "EPD_SCK", "10": "BTN_C",
             "11": "EPD_MOSI", "12": "+3V3", "13": "GND", "14": "unconnected-(U1-5V-Pad14)"},
            "Seeed Studio XIAO ESP32-C3 (with antenna), soldered on 2x 1x7 male headers", "Seeed XIAO ESP32C3"),
    "J1":  ("EPD", "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical", 18.0, 24.0, 0, "B",
            {"1": "+3V3", "2": "GND", "3": "EPD_MOSI", "4": "EPD_SCK", "5": "EPD_CS",
             "6": "EPD_DC", "7": "EPD_RST", "8": "EPD_BUSY"},
            "1x8 2.54 mm male header, display cable (VCC GND DIN CLK CS DC RST BUSY)", "2.54mm 1x8 male header"),
    "J2":  ("BATT", "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical", 66.0, 9.0, 0, "B",
            {"1": "VBAT", "2": "GND"},
            "JST-PH 2-pin vertical, optional 3.7 V LiPo (CHECK POLARITY)", "JST B2B-PH-K-S"),
    "J3":  ("XIAO_BAT", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 78.5, 30.0, 0, "B",
            {"1": "VBAT", "2": "GND"},
            "2 solder holes: wires to the XIAO BAT+/BAT- pads (only if using a battery)", "-"),
    "BZ1": ("Buzzer", "Buzzer_Beeper:Buzzer_12x9.5RM7.6", 41.0, 15.0, 0, "B",
            {"1": "BUZ_N", "2": "+3V3"},
            "12 mm passive/magnetic buzzer 3 V, 7.6 mm pin spacing", "12x9.5mm 3V passive buzzer 7.6mm"),
    "Q1":  ("2N3904", "Package_TO_SOT_THT:TO-92_Inline_Wide", 52.0, 31.0, 0, "B",
            {"1": "GND", "2": "Q_BASE", "3": "BUZ_N"},
            "NPN transistor TO-92 (2N3904 / S8050 / BC337, EBC pinout)", "2N3904 TO-92"),
    "D1":  ("1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 41.0, 26.0, 0, "B",
            {"1": "+3V3", "2": "BUZ_N"},
            "1N4148 flyback diode (cathode band to +3V3)", "1N4148 DO-35"),
    "R1":  ("1M", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 66.0, 16.0, 0, "B",
            {"1": "VBAT", "2": "VBAT_SENSE"}, "1 MΩ 1/4 W, battery divider top", "-"),
    "R2":  ("1M", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 66.0, 21.0, 0, "B",
            {"1": "VBAT_SENSE", "2": "GND"}, "1 MΩ 1/4 W, battery divider bottom", "-"),
    "C1":  ("100n", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm", 66.0, 26.0, 0, "B",
            {"1": "VBAT_SENSE", "2": "GND"}, "100 nF ceramic, ADC filter", "-"),
    "R3":  ("1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 64.0, 36.0, 0, "B",
            {"1": "BUZ_DRV", "2": "Q_BASE"}, "1 kΩ base resistor", "-"),
    "R7":  ("10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 52.0, 38.0, 0, "B",
            {"1": "Q_BASE", "2": "GND"}, "10 kΩ base pull-down (keeps buzzer off at boot)", "-"),
    "R4":  ("10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 33.0, 46.0, 0, "B",
            {"1": "+3V3", "2": "BTN_A"}, "10 kΩ pull-up button A", "-"),
    "R5":  ("10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 53.0, 46.0, 0, "B",
            {"1": "+3V3", "2": "BTN_B"}, "10 kΩ pull-up button B", "-"),
    "R6":  ("10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", 73.0, 46.0, 0, "B",
            {"1": "+3V3", "2": "BTN_C"}, "10 kΩ pull-up button C", "-"),
    "SW1": ("A", "Button_Switch_THT:SW_PUSH_6mm_H9.5mm", 33.0, 55.0, 0, "F",
            {"1": "BTN_A", "2": "GND"}, "6x6 mm tactile switch, 9.5 mm tall", "6x6x9.5mm tactile switch THT"),
    "SW2": ("B", "Button_Switch_THT:SW_PUSH_6mm_H9.5mm", 53.0, 55.0, 0, "F",
            {"1": "BTN_B", "2": "GND"}, "6x6 mm tactile switch, 9.5 mm tall", "6x6x9.5mm tactile switch THT"),
    "SW3": ("C", "Button_Switch_THT:SW_PUSH_6mm_H9.5mm", 73.0, 55.0, 0, "F",
            {"1": "BTN_C", "2": "GND"}, "6x6 mm tactile switch, 9.5 mm tall", "6x6x9.5mm tactile switch THT"),
}

XIAO_PIN_NAMES = {
    "1": "D0/GPIO2", "2": "D1/GPIO3", "3": "D2/GPIO4", "4": "D3/GPIO5", "5": "D4/GPIO6",
    "6": "D5/GPIO7", "7": "D6/GPIO21", "8": "D7/GPIO20", "9": "D8/GPIO8", "10": "D9/GPIO9",
    "11": "D10/GPIO10", "12": "3V3", "13": "GND", "14": "5V",
}


def nets():
    """net name -> list of (ref, pad)"""
    out = {}
    for ref, p in PARTS.items():
        for pad, net in p[6].items():
            out.setdefault(net, []).append((ref, pad))
    return out


if __name__ == "__main__":
    for n, conns in sorted(nets().items()):
        print(f"{n:12s} {' '.join(f'{r}.{p}' for r, p in conns)}")
