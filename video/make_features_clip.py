"""Before/after of the display-features update: 5 stills + a 30 s vertical clip.

BEFORE = simulator built from video/assets/ui_before_display_features.cpp,
AFTER  = simulator built from the current firmware/src/ui.cpp.
Pixels are real firmware output; only labels and the highlight box are added.

  python3 video/make_features_clip.py OLD_FBSIM
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_reel as R  # noqa: E402
from make_reel import BG, BG2, MUTED, TOMATO, TXT, ease, fade, font, text_alpha, vgrad  # noqa: E402

OLD = sys.argv[1]
NEW = os.path.join(R.ROOT, "sim", "fbsim")
OUTDIR = os.path.join(R.ROOT, "docs", "images", "display-features")
VIDEO = os.path.join(R.ROOT, "video", "display-features-30s.mp4")
os.makedirs(OUTDIR, exist_ok=True)

W, H, FPS, DUR = 1080, 1920, 30, 30.0
SC = 3
PW, PH = 296 * SC, 128 * SC
GREEN = (110, 180, 110)

F_H1 = font("NotoSans-Bold.ttf", 60)
F_BODY = font("NotoSans-Medium.ttf", 38)
F_TAG = font(R.MONO, 30)
F_TINY = font("NotoSans-Medium.ttf", 23)

P = "Classic 25/5"
# (file, title, explanation, before-args, after-args, highlight box in panel px or None)
CASES = [
    ("1-startup-splash", "Startup splash",
     "Power-up now says hi and teaches the three buttons, then goes to the timer.",
     ["main", "0", "0", "1", "1500000", "1500000", "0", "0", "0", "0", "0", P, "25"],
     ["splash", "0", "0", "0", "0", "1", "0", "0", "0", "0", "0", "x", "25"], (0, 0, 296, 128)),
    ("2-idle-shows-preset", "Idle shows the preset",
     "The buddy names the active preset, so pressing C visibly does something.",
     ["main", "0", "0", "1", "3000000", "3000000", "0", "0", "37", "0", "3950", "Deep 50/10", "50"],
     ["main", "0", "0", "1", "3000000", "3000000", "0", "0", "37", "0", "3950", "Deep 50/10", "50"], (0, 100, 110, 128)),
    ("3-focus-encouragement", "Encouragement while you focus",
     "Lines change with progress: Let's go! / In the zone / Keep going / Almost there / Final push!",
     ["main", "1", "0", "1", "700000", "1500000", "1", "1", "37", "0", "3950", P, "25"],
     ["main", "1", "0", "1", "700000", "1500000", "1", "1", "37", "0", "3950", P, "25"], (0, 100, 110, 128)),
    ("4-break-tips-and-mute-icon", "Break tips + mute icon",
     "Breaks suggest something to do. Muted is now a speaker icon, not the word 'mute'.",
     ["main", "1", "1", "0", "200000", "300000", "1", "2", "37", "1", "3950", P, "25"],
     ["main", "1", "1", "0", "200000", "300000", "1", "2", "37", "1", "3950", P, "25"], (0, 100, 236, 128)),
    ("5-low-battery", "Low-battery nudge",
     "Below 10 % the buddy asks to be charged (the sleep screen says it too).",
     ["main", "0", "0", "1", "1500000", "1500000", "1", "1", "37", "0", "3360", P, "25"],
     ["main", "0", "0", "1", "1500000", "1500000", "1", "1", "37", "0", "3360", P, "25"], (0, 100, 110, 128)),
]


def sim(binary, args, tag):
    out = os.path.join(R.TMP, f"{tag}.pbm")
    subprocess.run([binary] + args + [out], check=True)
    return np.array(Image.open(out).convert("L")) < 128


SHOTS = [(c, sim(OLD, c[3], c[0] + "_b"), sim(NEW, c[4], c[0] + "_a")) for c in CASES]
TEX = np.random.default_rng(3).normal(0, 3.0, (PH, PW, 1)).astype(np.float32)
_m = ImageDraw.Draw(Image.new("L", (1, 1)))


def wrap(s, f, mw):
    out, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if _m.textlength(t, font=f) <= mw:
            cur = t
        else:
            out.append(cur)
            cur = w
    return out + [cur]


def panel(ink, box=None, box_a=0.0):
    big = np.kron(ink.astype(float), np.ones((SC, SC)))[:, :, None]
    rgb = np.array(R.PAPER) * (1 - big) + np.array(R.INK) * big + TEX
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    if box and box_a > 0:
        x0, y0, x1, y1 = box
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle((x0 * SC + 2, y0 * SC + 2, x1 * SC - 3, y1 * SC - 3), 10,
                                              outline=TOMATO + (int(235 * box_a),), width=6)
        im.alpha_composite(lay)
    return im


def compare(case, before, after, box_a=1.0, a_txt=1.0):
    im = vgrad(W, H, BG2, BG).convert("RGBA")
    name, title, expl, _, _, box = case
    px = (W - PW) // 2
    text_alpha(im, (W // 2, 150), "DISPLAY FEATURES UPDATE", F_TAG, TOMATO, a_txt, "mm")
    text_alpha(im, (W // 2, 240), title, F_H1, TXT, a_txt, "mm")
    text_alpha(im, (px, 360), "BEFORE", F_TAG, MUTED, 1)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((px - 16, 394, px + PW + 16, 410 + PH + 16), 14, fill=(40, 40, 44))
    im.alpha_composite(panel(before), (px, 410))
    text_alpha(im, (px, 900), "AFTER", F_TAG, GREEN, 1)
    d.rounded_rectangle((px - 16, 934, px + PW + 16, 950 + PH + 16), 14, fill=(40, 40, 44))
    im.alpha_composite(panel(after, box, box_a), (px, 950))
    y = 1430
    for ln in wrap(expl, F_BODY, W - 160):
        text_alpha(im, (W // 2, y), ln, F_BODY, TXT, a_txt, "ma")
        y += 54
    text_alpha(im, (W // 2, 1760), "Red box = what changed. Pixels are real firmware output (desktop simulator).",
               F_TINY, MUTED, 1, "mm")
    return im


for case, b, a in SHOTS:
    compare(case, b, a).convert("RGB").save(os.path.join(OUTDIR, case[0] + ".png"))
print("stills ->", OUTDIR)

NOISE = np.random.default_rng(1).random((128, 296))


def title_card(t):
    im = vgrad(W, H, BG2, BG).convert("RGBA")
    a = fade(t, 0, 3.2, 0.4)
    text_alpha(im, (W // 2, 700), "The display gets a voice", F_H1, TXT, a, "mm")
    y = 800
    for ln in wrap("Speech bubble, startup splash, mute icon and a low-battery nudge.", F_BODY, 860):
        text_alpha(im, (W // 2, y), ln, F_BODY, MUTED, a, "ma")
        y += 54
    text_alpha(im, (W // 2, 1050), "FOCUS BUDDY  ·  firmware/src/ui.cpp", F_TAG, TOMATO, a, "mm")
    return im


OUTRO = ["What changed", "",
         "+ speech bubble: 12 lines + preset name",
         "+ startup splash with button guide",
         "+ speaker icon when muted",
         "+ 'Charge me!' below 10 % battery",
         "",
         "4 firmware variants build: 22.8% flash",
         "Left for later: clock, history graph,",
         "custom presets, dark mode"]


def outro(t):
    im = vgrad(W, H, BG2, BG).convert("RGBA")
    a = fade(t, 26.5, 30.6, 0.4)
    y = 560
    for i, ln in enumerate(OUTRO):
        f = F_H1 if i == 0 else F_BODY
        col = TXT if i < 6 else MUTED
        text_alpha(im, (W // 2, y), ln, f, col, a * ease((t - 26.6 - i * 0.1) / 0.4), "mm")
        y += 90 if i == 0 else 60
    return im


def frame(t):
    if t < 3.0:
        return title_card(t)
    if t >= 26.5:
        return outro(t)
    k = min(int((t - 3.0) / 4.7), 4)
    lt = t - 3.0 - k * 4.7
    case, before, after = SHOTS[k]
    p = (lt - 1.2) / 0.35
    cur = before if p <= 0 else (after if p >= 1 else np.where(NOISE < p, after, before))
    im = compare(case, before, cur, ease((lt - 1.9) / 0.4), fade(lt, 0, 4.7, 0.3))
    a = 1 - min(ease(lt / 0.25), ease((4.7 - lt) / 0.25))
    if a > 0:
        im.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, int(160 * a))))
    return im


cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
       "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-threads", "2", "-pix_fmt", "yuv420p",
       "-movflags", "+faststart", VIDEO]
ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(int(DUR * FPS)):
    ff.stdin.write(frame(i / FPS).convert("RGB").tobytes())
ff.stdin.close()
ff.wait()
print("video ->", VIDEO)
