"""Focus Buddy: 60-second progress reel for the Half Life judges.

Every e-paper frame in this video comes from the firmware's own drawing code
(firmware/src/ui.cpp) compiled for the desktop (sim/fbsim). The device body,
refresh flashes and button presses are animation; the pixels are real.

  python3 video/make_reel.py            -> video/focus-buddy-progress-reel.mp4
  python3 video/make_reel.py --still 30 -> preview a single frame at t=30s
"""
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, "sim", "fbsim")
OUT = os.path.join(ROOT, "video", "focus-buddy-progress-reel.mp4")
W, H, FPS, DUR = 1920, 1080, 30, 60.0

# ------------------------------------------------------------------ palette / fonts
BG = (20, 22, 27)
BG2 = (31, 34, 41)
TOMATO = (232, 85, 61)
LEAF = (110, 180, 110)
PAPER = (228, 226, 216)
INK = (34, 34, 40)
TXT = (236, 234, 228)
MUTED = (150, 154, 164)
BODY = (214, 209, 197)
BODY_DARK = (186, 180, 166)

FD = "/usr/share/fonts/noto/"
MONO = "/usr/share/fonts/TTF/JetBrainsMono-Bold.ttf"


def font(name, size):
    return ImageFont.truetype(FD + name if not name.startswith("/") else name, size)


F_TITLE = font("NotoSans-Black.ttf", 128)
F_H1 = font("NotoSans-Bold.ttf", 64)
F_H2 = font("NotoSans-Bold.ttf", 44)
F_BODY = font("NotoSans-Medium.ttf", 36)
F_SMALL = font("NotoSans-Medium.ttf", 26)
F_TINY = font("NotoSans-Medium.ttf", 21)
F_MONO = font(MONO, 30)
F_MONO_S = font(MONO, 22)

# ------------------------------------------------------------------ firmware screens
_cache = {}
TMP = tempfile.mkdtemp()


def screen(kind="main", state=0, phase=0, nxt=1, rem=1500000, plen=1500000, prog=3, today=3,
           life=37, muted=0, batt=3950, preset="Classic 25/5", fmin=25):
    key = (kind, state, phase, nxt, rem, plen, prog, today, life, muted, batt, preset, fmin)
    if key not in _cache:
        out = os.path.join(TMP, f"s{len(_cache)}.pbm")
        subprocess.run([SIM, kind, str(state), str(phase), str(nxt), str(rem), str(plen), str(prog),
                        str(today), str(life), str(muted), str(batt), preset, str(fmin), out], check=True)
        _cache[key] = np.array(Image.open(out).convert("L")) < 128  # True = ink
    return _cache[key]


IDLE, RUNNING, PAUSED, ALARM, STATS = range(5)
FOCUS, SHORT, LONG = range(3)
M = 60000

# ------------------------------------------------------------------ demo script (absolute seconds)
# screen events: (time, frame, refresh kind)
EV = []
CAP = []      # (t0, t1, title, body)
PRESS = []    # (t, button 0..2, hold seconds)
BADGE = []    # (t0, t1, text)

t = 11.2
EV.append((t, screen(state=IDLE, rem=25 * M, prog=3, today=3), "full"))
CAP.append((11.4, 14.5, "Idle", "The buddy is ready. Press A to start a 25-minute focus block."))
PRESS.append((13.8, 0, 0.25))
EV.append((14.1, screen(state=RUNNING, rem=25 * M, prog=3, today=3), "partial"))
CAP.append((14.6, 21.0, "Focus mode", "Redraws only when the minute changes (partial refresh). The ESP32 light-sleeps in between."))
BADGE.append((14.6, 23.2, "TIME-LAPSE"))
tt = 14.6
for m in range(24, 1, -1):
    EV.append((tt, screen(state=RUNNING, rem=m * M, prog=3, today=3), "partial"))
    tt += 0.28
CAP.append((21.0, 23.4, "Last minute", "Switches to seconds, in 10-second steps."))
for s in (60, 50, 40, 30, 20, 10):
    EV.append((tt, screen(state=RUNNING, rem=s * 1000, prog=3, today=3), "partial"))
    tt += 0.36
EV.append((23.5, screen(state=ALARM, phase=FOCUS, nxt=LONG, rem=0, prog=4, today=4, life=38), "full"))
CAP.append((24.0, 26.6, "Session done", "Buzzer chime + celebration face. Four dots filled = long break earned."))
PRESS.append((26.3, 0, 0.25))
EV.append((26.6, screen(state=RUNNING, phase=LONG, nxt=FOCUS, rem=15 * M, plen=15 * M, prog=4, today=4, life=38), "partial"))
CAP.append((26.9, 29.2, "Long break", "A starts the break. The buddy relaxes."))
BADGE.append((27.2, 29.3, "TIME-LAPSE"))
tt = 27.2
for m in range(14, 9, -1):
    EV.append((tt, screen(state=RUNNING, phase=LONG, nxt=FOCUS, rem=m * M, plen=15 * M, prog=4, today=4, life=38), "partial"))
    tt += 0.4
PRESS.append((29.4, 0, 0.25))
EV.append((29.7, screen(state=PAUSED, phase=LONG, nxt=FOCUS, rem=10 * M, plen=15 * M, prog=4, today=4, life=38), "partial"))
CAP.append((29.8, 31.0, "Paused", "Press A again to pause."))
PRESS.append((31.1, 2, 1.0))
CAP.append((31.1, 35.4, "Hold C: stats", "Today, all-time sessions and hours focused, saved in flash."))
EV.append((32.2, screen("stats", state=STATS, prog=4, today=4, life=38), "full"))
PRESS.append((35.0, 1, 0.25))
EV.append((35.3, screen(state=PAUSED, phase=LONG, nxt=FOCUS, rem=10 * M, plen=15 * M, prog=4, today=4, life=38), "full"))
BADGE.append((36.4, 38.6, "10 MIN LATER"))
EV.append((37.2, screen("sleep", prog=4, today=4, life=38), "full"))
CAP.append((36.4, 40.8, "Nobody around? It naps.", "Deep sleep, about 0.05 mA. E-ink holds the picture with zero power."))
PRESS.append((40.6, 1, 0.25))
EV.append((41.0, screen(state=PAUSED, phase=LONG, nxt=FOCUS, rem=10 * M, plen=15 * M, prog=4, today=4, life=38), "partial"))
CAP.append((41.2, 45.0, "Wakes right where you left off", "Paused time survives deep sleep (bug found and fixed while making this reel)."))

DEMO0, DEMO1 = 10.6, 45.4
REFRESH_DUR = {"full": 0.9, "partial": 0.32}

rng = np.random.default_rng(7)
NOISE = rng.random((128, 296))


def screen_state(t):
    """Return ink fraction array (128x296 float 0..1) for time t."""
    prev = np.zeros((128, 296), bool)
    cur, kind, t0 = prev, None, -99
    for et, img, k in EV:
        if et <= t:
            prev, cur, kind, t0 = cur, img, k, et
        else:
            break
    if kind is None:
        return np.zeros((128, 296))
    p = (t - t0) / REFRESH_DUR[kind]
    if p >= 1:
        ghost = max(0.0, 1 - (t - t0 - REFRESH_DUR[kind]) / 0.5) * 0.10 if kind == "partial" else 0
        return np.clip(cur.astype(float) + ghost * (prev & ~cur), 0, 1)
    if kind == "full":  # classic e-paper flash: inverse old, black, white, inverse new, new
        if p < 0.2:
            return (~prev).astype(float)
        if p < 0.4:
            return np.ones((128, 296))
        if p < 0.6:
            return np.zeros((128, 296))
        if p < 0.8:
            return (~cur).astype(float)
        return cur.astype(float)
    # partial: changed pixels switch over with a dithered sweep
    switched = NOISE < p
    out = np.where(switched, cur, prev).astype(float)
    return out


# ------------------------------------------------------------------ static layers
def vgrad(w, h, top, bot):
    a = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top) * (1 - a) + np.array(bot) * a).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, w, axis=1))


BACKDROP = vgrad(W, H, BG2, BG)

SCALE = 4
SW, SH = 296 * SCALE, 128 * SCALE
DX, DY = (W - SW) // 2, 120          # screen top-left
BODY_BOX = (DX - 92, DY - 60, DX + SW + 92, DY + SH + 205)
BTN_Y = DY + SH + 106
BTN_X = [W // 2 - 300, W // 2, W // 2 + 300]
BTN_LABEL = ["A  start / pause", "B  skip / wake", "C  preset / stats"]


def make_device():
    im = BACKDROP.copy()
    # shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle((BODY_BOX[0] + 10, BODY_BOX[1] + 30, BODY_BOX[2] + 10, BODY_BOX[3] + 40), 70, fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(40))
    im.paste((0, 0, 0), (0, 0), sh)
    # body with soft vertical gradient
    body = vgrad(BODY_BOX[2] - BODY_BOX[0], BODY_BOX[3] - BODY_BOX[1], (226, 221, 209), BODY_DARK)
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, body.width - 1, body.height - 1), 64, fill=255)
    im.paste(body, BODY_BOX[:2], mask)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(BODY_BOX, 64, outline=(240, 236, 226), width=2)
    # bezel around the panel
    d.rounded_rectangle((DX - 26, DY - 26, DX + SW + 26, DY + SH + 26), 18, fill=(40, 40, 44))
    d.rounded_rectangle((DX - 8, DY - 8, DX + SW + 8, DY + SH + 8), 6, fill=(205, 203, 192))
    # button wells + labels
    for x, lab in zip(BTN_X, BTN_LABEL):
        d.ellipse((x - 44, BTN_Y - 44, x + 44, BTN_Y + 44), fill=(170, 164, 150))
        d.text((x, BTN_Y + 66), lab, font=F_TINY, fill=(95, 92, 84), anchor="mm")
    return im


DEVICE = make_device()
PAPER_TEX = (np.random.default_rng(3).normal(0, 3.2, (SH, SW, 1))).astype(np.float32)


def render_panel(ink):
    big = np.kron(ink, np.ones((SCALE, SCALE)))[:, :, None]
    rgb = np.array(PAPER) * (1 - big) + np.array(INK) * big + PAPER_TEX
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ drawing helpers
def ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


def fade(t, t0, t1, f=0.35):
    if t < t0 or t > t1:
        return 0.0
    return min(ease((t - t0) / f), ease((t1 - t) / f))


def text_alpha(base, xy, s, fnt, fill, a, anchor="la"):
    if a <= 0:
        return
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, s, font=fnt, fill=fill + (int(255 * a),), anchor=anchor)
    base.alpha_composite(layer)


def check_icon(d, cx, cy, r, kind):
    if kind == "done":
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LEAF)
        d.line([(cx - r * .45, cy + r * .02), (cx - r * .1, cy + r * .38), (cx + r * .5, cy - r * .35)], fill=BG, width=6, joint="curve")
    elif kind == "wip":
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=TOMATO, width=5)
        d.pieslice((cx - r, cy - r, cx + r, cy + r), -90, 90, fill=TOMATO)
    else:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=MUTED, width=4)


BUDDY = screen(state=IDLE, rem=25 * M)[:, :106]  # the firmware's own buddy art


def buddy_logo(size, color):
    m = Image.fromarray((BUDDY * 255).astype(np.uint8)).resize((106 * size, 128 * size), Image.NEAREST)
    lay = Image.new("RGBA", m.size, color + (0,))
    lay.putalpha(m)
    return lay


LOGO = buddy_logo(4, TOMATO)

# ------------------------------------------------------------------ scenes
def scene_title(t):
    im = BACKDROP.convert("RGBA")
    a = fade(t, 0, 5.3, 0.6)
    lg = LOGO.copy()
    lg.putalpha(Image.eval(lg.getchannel("A"), lambda v: int(v * a)))
    bob = int(8 * math.sin(t * 2.4))
    im.alpha_composite(lg, (W // 2 - lg.width // 2, 110 + bob))
    text_alpha(im, (W // 2, 700), "FOCUS BUDDY", F_TITLE, TXT, ease((t - 0.5) / 0.6) * a, "mm")
    text_alpha(im, (W // 2, 800), "an e-ink Pomodoro companion for your desk", F_BODY, MUTED, ease((t - 1.0) / 0.6) * a, "mm")
    text_alpha(im, (W // 2, 905), "HALF LIFE  ·  PROGRESS REEL  ·  DISPLAY DEEP-DIVE", F_MONO, TOMATO, ease((t - 1.6) / 0.6) * a, "mm")
    return im


def scene_disclaimer(t):
    im = BACKDROP.convert("RGBA")
    a = fade(t, 5.3, 10.8, 0.5)
    d = ImageDraw.Draw(im)
    box = (260, 220, W - 260, 860)
    if a > 0:
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle(box, 36, fill=(42, 45, 54, int(235 * a)), outline=TOMATO + (int(255 * a),), width=3)
        im.alpha_composite(lay)
    text_alpha(im, (340, 300), "DISCLAIMER", F_MONO, TOMATO, a)
    text_alpha(im, (340, 360), "We joined Half Life halfway through.", F_H1, TXT, a)
    lines = [
        "Everything else is already planned: PCB routing, Gerbers,",
        "the 3D-printed enclosure and the build guide.",
        "",
        "This reel shows only what actually exists today. No hardware",
        "has been assembled yet. Every screen you'll see is drawn by the",
        "real firmware code, compiled and run on a PC.",
    ]
    for i, ln in enumerate(lines):
        text_alpha(im, (340, 480 + i * 50), ln, F_BODY, TXT if i < 2 else MUTED, a * ease((t - 5.8 - i * 0.12) / 0.4))
    return im


def scene_demo(t):
    im = DEVICE.copy()
    ink = screen_state(t)
    im.paste(render_panel(ink), (DX, DY))
    im = im.convert("RGBA")
    d = ImageDraw.Draw(im)
    # buttons
    for i, x in enumerate(BTN_X):
        pressed, hold_p = False, 0
        for pt, b, hold in PRESS:
            if b == i and pt <= t <= pt + hold:
                pressed, hold_p = True, (t - pt) / hold
        off = 4 if pressed else 0
        col = (120, 116, 106) if pressed else (88, 86, 82)
        if pressed:
            d.ellipse((x - 56, BTN_Y - 56, x + 56, BTN_Y + 56), outline=TOMATO, width=5)
            if hold_p and any(b == i and h > 0.5 and pt <= t <= pt + h for pt, b, h in PRESS):
                d.arc((x - 66, BTN_Y - 66, x + 66, BTN_Y + 66), -90, -90 + 360 * hold_p, fill=TOMATO, width=6)
        d.ellipse((x - 34, BTN_Y - 34 + off, x + 34, BTN_Y + 34 + off), fill=col)
        d.text((x, BTN_Y + off), "ABC"[i], font=F_H2, fill=(230, 226, 214), anchor="mm")
    # buzzer waves while the alarm screen is fresh
    if 23.6 <= t <= 26.2:
        cx, cy = BODY_BOX[2] + 40, DY + SH // 2
        for k in range(3):
            ph = ((t * 1.6 + k / 3) % 1)
            r = 30 + ph * 120
            al = int(255 * (1 - ph))
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).arc((cx - r, cy - r, cx + r, cy + r), -50, 50, fill=TOMATO + (al,), width=7)
            im.alpha_composite(lay)
        text_alpha(im, (cx + 70, cy - 150), "beep!", F_MONO, TOMATO, 1, "mm")
    # badges
    for b0, b1, txt in BADGE:
        a = fade(t, b0, b1, 0.25)
        if a:
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).rounded_rectangle((DX + SW - 270, DY - 92, DX + SW, DY - 44), 24, fill=TOMATO + (int(240 * a),))
            im.alpha_composite(lay)
            text_alpha(im, (DX + SW - 135, DY - 68), txt, F_MONO_S, (255, 255, 255), a, "mm")
    # caption
    for c0, c1, title, body in CAP:
        a = fade(t, c0, c1, 0.3)
        if a:
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).rounded_rectangle((180, 912, W - 180, 1018), 26, fill=(14, 15, 19, int(225 * a)))
            im.alpha_composite(lay)
            text_alpha(im, (220, 940), title.upper(), F_MONO_S, TOMATO, a)
            text_alpha(im, (220, 970), body, F_SMALL, TXT, a)
    # persistent honesty footer
    text_alpha(im, (W // 2, 1052), "SIMULATED: pixels come from the real firmware (ui.cpp) running on a PC. Refresh flashes and the device body are animation.",
               F_TINY, MUTED, fade(t, DEMO0, DEMO1, 0.4), "mm")
    text_alpha(im, (40, 40), "DISPLAY DEEP-DIVE", F_MONO_S, MUTED, fade(t, DEMO0, DEMO1, 0.4))
    # fade from/to black
    a = 1 - min(ease((t - DEMO0) / 0.45), ease((DEMO1 - t) / 0.45))
    if a > 0:
        im.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, int(255 * a))))
    return im


PROGRESS = [
    ("done", "Firmware: timer state machine, 7 screens, light + deep sleep",
             "PlatformIO, ESP32-C3. Compiles clean: 22.7% flash, 6.1% RAM, 4 panel variants"),
    ("done", "Display simulator: real ui.cpp rendered on desktop",
             "Same Adafruit-GFX code path as the device. It rendered every frame of this video"),
    ("done", "Circuit + netlist: 18 through-hole parts, 17 nets",
             "XIAO ESP32-C3, 2.9\" e-paper, 3 buttons, buzzer driver, LiPo sense"),
    ("done", "PCB: 106 x 64 mm outline, cable slot, every part placed",
             "KiCad 9, scripted in Python. Custom XIAO footprint"),
    ("wip", "PCB autorouting + DRC + Gerbers",
            "Freerouting is downloaded; this is the next step"),
    ("todo", "Enclosure (OpenSCAD), schematic PDF, build guide, real hardware test",
             "Planned and specced, not started"),
]


def scene_progress(t):
    im = BACKDROP.convert("RGBA")
    T0, T1 = 45.4, 56.2
    a = fade(t, T0, T1, 0.45)
    text_alpha(im, (160, 90), "WHERE WE ACTUALLY ARE", F_MONO, TOMATO, a)
    text_alpha(im, (160, 135), "Real progress, as of today", F_H1, TXT, a)
    for i, (k, head, sub) in enumerate(PROGRESS):
        ai = a * ease((t - T0 - 0.6 - i * 0.55) / 0.4)
        if ai <= 0:
            continue
        y = 280 + i * 118
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle((150, y - 14, W - 150, y + 96), 20, fill=(38, 41, 50, int(200 * ai)))
        check_icon(ld, 210, y + 41, 24, k)
        lay.putalpha(Image.eval(lay.getchannel("A"), lambda v: int(v * ai)) if ai < 1 else lay.getchannel("A"))
        im.alpha_composite(lay)
        text_alpha(im, (260, y + 2), head, F_BODY, TXT if k != "todo" else MUTED, ai)
        text_alpha(im, (260, y + 50), sub, F_SMALL, MUTED, ai)
        tag = {"done": "DONE", "wip": "IN PROGRESS", "todo": "PLANNED"}[k]
        col = {"done": LEAF, "wip": TOMATO, "todo": MUTED}[k]
        text_alpha(im, (W - 190, y + 41), tag, F_MONO_S, col, ai, "rm")
    return im


def scene_outro(t):
    im = BACKDROP.convert("RGBA")
    a = fade(t, 56.2, 60.5, 0.5)
    lg = buddy_logo(2, TOMATO)
    lg.putalpha(Image.eval(lg.getchannel("A"), lambda v: int(v * a)))
    im.alpha_composite(lg, (W // 2 - lg.width // 2, 200))
    text_alpha(im, (W // 2, 560), "Next up: route the board, print the case, flash real hardware", F_H2, TXT, a, "mm")
    text_alpha(im, (W // 2, 650), "Joined halfway. The rest is planned. See you at the finish line.", F_BODY, MUTED, a, "mm")
    text_alpha(im, (W // 2, 760), "FOCUS BUDDY  ·  HALF LIFE", F_MONO, TOMATO, a, "mm")
    return im


def frame(t):
    if t < 5.3:
        im = scene_title(t)
    elif t < 10.8:
        im = scene_disclaimer(t)
    elif t < 45.4:
        im = scene_demo(t)
    elif t < 56.2:
        im = scene_progress(t)
    else:
        im = scene_outro(t)
    return im.convert("RGB")


def main():
    if "--still" in sys.argv:
        ts = float(sys.argv[sys.argv.index("--still") + 1])
        p = sys.argv[sys.argv.index("--still") + 2] if len(sys.argv) > sys.argv.index("--still") + 2 else "/dev/stdout"
        frame(ts).save(p)
        return
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-threads", "2",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
