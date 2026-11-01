# Building Focus Buddy

About 2 hours of hands-on time, all through-hole soldering. If you can solder a pin header, you can build this.

> **Status, honestly:** the PCB passes KiCad DRC, ERC and schematic-parity checks, and the firmware compiles.
> Rev A has **not been built and tested on real hardware yet**. Read the "Check before you order" list.

---

## 0. Check before you order

1. **Display window offset.** The Waveshare 2.9" glass is not centred on its PCB. When your module arrives,
   measure from the left edge of the module board to the left edge of the black active area, then do the same
   on the right. Put half the difference into `win_offset` in `hardware/cad/enclosure.scad` and re-export the
   front shell. The default `[0, 0]` assumes the glass is centred.
2. **Battery polarity** (only if you use one). JST-PH LiPo plugs are wired both ways in the wild. J2 pin 1
   (the square pad, marked `+`) must get the red wire. Check with a meter before plugging in.
3. **Buzzer type.** Either a 3 V magnetic or a passive piezo "12 mm, 7.6 mm pitch" buzzer works.
   Don't use an *active* buzzer (one with a built-in oscillator): it can't play tunes.

## 1. Get the parts

Everything is in [`hardware/BOM.csv`](../hardware/BOM.csv). In short:

| What | Qty |
|---|---|
| Seeed XIAO ESP32-C3 (comes with headers and an antenna) | 1 |
| Waveshare 2.9" e-Paper Module **V2** (B/W, 296×128) with its 8-wire cable | 1 |
| PCB (Gerber zip below) | 1 |
| 6×6 mm tactile switch, **9.5 mm tall**, through-hole | 3 |
| 12 mm buzzer, 7.6 mm pin spacing | 1 |
| 2N3904 (or S8050 / BC337) NPN, TO-92 | 1 |
| 1N4148 diode | 1 |
| Resistors 1/4 W: 1 MΩ ×2, 10 kΩ ×4, 1 kΩ ×1 | 7 |
| 100 nF ceramic capacitor | 1 |
| 1×8 male pin header (2.54 mm) | 1 |
| JST-PH 2-pin vertical socket + LiPo (optional) | 1 |
| M3×20 screws | 4 |

Other display panels: the firmware also has build targets for older Waveshare V1 panels and the WeAct 2.9"
(see `firmware/platformio.ini`). Their PCBs are about the same size, but check the window offset.

## 2. Order the PCB

Run `tools/make_all.sh` (see the README) to generate **`hardware/fab/focus-buddy-gerbers.zip`**, then upload it to
JLCPCB, PCBWay or any other fab. Every default is fine:

- 2 layers, 1.6 mm, 106 × 64 mm, any colour, HASL
- Smallest drill: 0.4 mm vias. Smallest gap: 0.25 mm. Every cheap fab can do this.
- There's a slot in the board (for the display cable); it's in the Edge.Cuts layer, so no extra settings are needed.

## 3. Print the case

`tools/make_all.sh` writes the STLs to `hardware/cad/stl/`, already in print orientation. PLA or PETG, 0.2 mm layers, 3 walls, 20 % infill,
**no supports**.

| File | Notes |
|---|---|
| `focus-buddy-front.stl` | Prints face-down, so the front comes out smooth. The USB-C hole is a short rounded bridge. |
| `focus-buddy-back.stl` | Prints outside-face-down. |
| `focus-buddy-caps.stl` | 3 button caps, flange down. A contrasting colour looks great. |
| `focus-buddy-stand.stl` | Optional 15° desk stand, prints on its side. |

To change anything (wall thickness, window size, screw type), edit the parameters at the top of
`hardware/cad/enclosure.scad`. Every hole position is generated from the PCB, so they stay in sync.

## 4. Solder

The **front** of the board (red in the renders) faces you and holds only the 3 buttons. Everything else goes on
the **back**. Solder from shortest part to tallest:

1. **Resistors** on the back: R1 and R2 = 1 MΩ, R3 = 1 kΩ, R4–R7 = 10 kΩ. Orientation doesn't matter.
2. **D1 (1N4148)** on the back. **The band goes toward the square pad marked `K`** (silkscreen: "band → 3V3").
3. **C1 (100 nF)**: either way round.
4. **Q1** on the back. Flat face as printed on the silkscreen (E-B-C).
5. **J1, the 1×8 header**, on the back, short pins through the board.
6. **J2 (JST socket)**: only if you'll use a battery.
7. **Buzzer BZ1** on the back. **`+` goes to the square pad.**
8. **Buttons SW1–SW3** on the **front**. They only fit one way round. Push them flat before soldering.
9. **XIAO** last, on the back, on its male headers (long pins in the XIAO, short pins through the PCB),
   **USB-C pointing at the board edge**. If you'll use a battery, first solder a short red wire to the XIAO's
   `BAT+` pad (underside) and route it to the `BAT+` hole of J3.
10. **Trim** every lead on the front side flush. The display sits only a few mm in front of the board.

**Quick electrical check before powering:** with a multimeter, 3V3 to GND should **not** be a short.

## 5. Flash the firmware

```bash
pip install platformio          # once
cd firmware
pio run -t upload               # Waveshare 2.9" V2 (default)
# pio run -e weact_290 -t upload   # WeAct 2.9"
# pio run -e debug -t upload       # keeps USB serial alive, for debugging
```

If upload fails: hold the XIAO's **BOOT** button (or Button C, which is wired to the same pin), tap **RESET**,
release BOOT, then try again.

Before putting anything in the case, plug the display cable in (`VCC GND DIN CLK CS DC RST BUSY` match the
silkscreen next to J1) and power up. You should see the buddy and "25 min".

## 6. Assemble

1. Drop the 3 **button caps** into the front shell from the inside, flange-side in.
2. Put a strip of double-sided foam tape around the **display glass** edge and press the module into the
   corner brackets, **glass toward the window**, with its cable connector at the end nearest the PCB's cable
   slot (the left side when you look at the front of the device).
3. Feed the display cable **through the slot in the PCB** and plug it onto J1.
4. Lay the PCB onto the four bosses, buttons toward the front. The caps should sit on the switch plungers.
5. Stick the XIAO's **antenna** flat inside the back cover, away from the screw holes. Plug it into the XIAO.
6. (Optional) tape the **LiPo** inside the back cover and plug it into J2.
7. Put the back cover on and drive in the **4 × M3×20 screws**. They clamp cover, PCB and front together.
   Snug, not tight: it's plastic.

Click each button. If a cap doesn't click, the PCB isn't sitting flat on the bosses.

## 7. Use it

| Button | Short press | Hold 1 s |
|---|---|---|
| **A** (left) | start / pause / resume. On the "Nice work!" screen: start the next phase | – |
| **B** (middle) | skip to the next phase. Wakes the device | reset the current phase |
| **C** (right) | when idle: cycle presets (25/5, 50/10, 15/3, 90/15). When running: mute | stats screen |

- On power-up a splash screen says hi and shows what A, B and C do.
- The buddy talks in a speech bubble: the preset name when idle, encouragement while you focus
  ("Let's go!" → "Final push!"), a tip during breaks ("Stretch!", "Drink water", …), and "Charge me!" when the
  battery is below 10 %. A speaker icon shows when sound is muted.
- Long break after every 4 focus sessions (the 4 dots).
- The screen redraws once a minute, then every 10 s in the final minute.
- After 3 minutes idle (10 minutes paused) it goes to deep sleep and shows "Napping...". **A** or **B** wakes it,
  and a paused timer resumes where it left off.
- Lifetime session count is saved in flash; "today" resets when power is removed.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Display stays blank or shows noise | Wrong cable order on J1, or wrong panel version. Try `-e waveshare_290_v1` |
| Display updates but the image is mirrored or offset | Panel variant mismatch. Try the other environments |
| No sound | Buzzer reversed, Q1 reversed (check E-B-C), or muted (C while running) |
| Button does nothing | Cap not reaching the plunger: check the PCB sits on the bosses; check 10k pull-up solder joints |
| Won't flash | BOOT + RESET dance (step 5). Use a data USB-C cable |
| Battery icon missing | Normal on USB power with no battery |

## Rebuilding the design files

Everything under `hardware/` is generated from `tools/netlist.py` (parts, nets, placement):

```bash
tools/make_all.sh   # needs docker: KiCad 9 + OpenSCAD images; runs low-priority, 1 CPU
```

This places parts, routes the board with `tools/route_pcb.py` (a small built-in A* autorouter), pours ground,
generates the schematic, runs ERC/DRC/parity, and exports Gerbers, drill files, STEP, renders, BOM and STLs.
