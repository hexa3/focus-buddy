"""Before/after of the big-number alignment fix: 5 stills + a 30 s vertical clip.

Both sides are real firmware output: BEFORE from the simulator built from the old
ui.cpp, AFTER from the current one. Only the labels and the guide line are added.

  python3 video/make_digits_clip.py OLD_FBSIM
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
OUTDIR = os.path.join(R.ROOT, "docs", "images", "display-alignment-fix")
VIDEO = os.path.join(R.ROOT, "video", "display-alignment-fix-30s.mp4")
os.makedirs(OUTDIR, exist_ok=True)

W, H, FPS, DUR = 1080, 1920, 30, 30.0
SC = 3
PW, PH = 296 * SC, 128 * SC
GUIDE_X = 112  # left edge of the label column, panel pixels

F_H1 = font("NotoSans-Bold.ttf", 60)
F_BODY = font("NotoSans-Medium.ttf", 38)
F_SMALL = font("NotoSans-Medium.ttf", 28)
F_TAG = font(R.MONO, 30)
F_TINY = font("NotoSans-Medium.ttf", 23)

CASES = [  # (file name, title, explanation, sim args)
    ("1-five-minutes", "5 min", "Single digit: no more empty slot in front of the 5.",
     ["main", "1", "0", "1", "300000", "1500000", "2", "2", "37", "0", "3950", "Classic 25/5", "25"]),
    ("2-eleven-minutes", "11 min", "A '1' is now only as wide as its bar: no hole in the middle.",
     ["main", "1", "0", "1", "660000", "1500000", "2", "2", "37", "0", "3950", "Classic 25/5", "25"]),
    ("3-nineteen-minutes", "19 min", "The number starts on the same edge as FOCUS below it.",
     ["main", "1", "0", "1", "1140000", "1500000", "2", "2", "37", "0", "3950", "Classic 25/5", "25"]),
    ("4-ten-seconds", "10 sec", "Final-minute countdown gets the same treatment.",
     ["main", "1", "0", "1", "10000", "1500000", "2", "2", "37", "0", "3950", "Classic 25/5", "25"]),
    ("5-sprint-idle", "15 min idle", "Idle screen: number, label and hint share one left edge.",
     ["main", "0", "0", "1", "900000", "900000", "0", "0", "37", "0", "3950", "Sprint 15/3", "15"]),
]


def sim(binary, args, tag):
    out = os.path.join(R.TMP, f"{tag}.pbm")
    subprocess.run([binary] + args + [out], check=True)
    return np.array(Image.open(out).convert("L")) < 128


SHOTS = [(c, sim(OLD, c[3], c[0] + "_b"), sim(NEW, c[3], c[0] + "_a")) for c in CASES]
TEX = np.random.default_rng(3).normal(0, 3.0, (PH, PW, 1)).astype(np.float32)


def panel(ink, guide_a=0.0):
    big = np.kron(ink.astype(float), np.ones((SC, SC)))[:, :, None]
    rgb = np.array(R.PAPER) * (1 - big) + np.array(R.INK) * big + TEX
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    if guide_a > 0:
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).line([(GUIDE_X * SC - 2, 6), (GUIDE_X * SC - 2, PH - 6)], fill=TOMATO + (int(220 * guide_a),), width=4)
        im.alpha_composite(lay)
    return im


def framed(base, im, x, y):
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((x - 16, y - 16, x + PW + 16, y + PH + 16), 14, fill=(40, 40, 44))
    base.alpha_composite(im, (x, y))


def compare_image(case, before, after, guide=1.0, a_title=1.0):
    im = vgrad(W, H, BG2, BG).convert("RGBA")
    name, title, expl, _ = case
    px = (W - PW) // 2
    text_alpha(im, (W // 2, 150), "DISPLAY DETAIL: NUMBER ALIGNMENT", F_TAG, TOMATO, a_title, "mm")
    text_alpha(im, (W // 2, 240), title, F_H1, TXT, a_title, "mm")
    text_alpha(im, (px, 360), "BEFORE", F_TAG, MUTED, 1)
    framed(im, panel(before, guide), px, 410)
    text_alpha(im, (px, 900), "AFTER", F_TAG, (110, 180, 110), 1)
    framed(im, panel(after, guide), px, 950)
    y = 1430
    for ln in wrap(expl, F_BODY, W - 160):
        text_alpha(im, (W // 2, y), ln, F_BODY, TXT, a_title, "ma")
        y += 54
    text_alpha(im, (W // 2, 1740), "Red line = left edge of the label column. Pixels are real firmware output (desktop simulator).",
               F_TINY, MUTED, 1, "mm")
    return im


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


# ---------------------------------------------------------------- stills
for case, b, a in SHOTS:
    compare_image(case, b, a).convert("RGB").save(os.path.join(OUTDIR, case[0] + ".png"))
print("stills ->", OUTDIR)

# ---------------------------------------------------------------- 30 s clip
# 0-3 title | 3-26.5 five cases (4.7 s each: before, e-ink partial refresh to after, guide line) | 26.5-30 outro
NOISE = np.random.default_rng(1).random((128, 296))


def title_card(t):
    im = vgrad(W, H, BG2, BG).convert("RGBA")
    a = fade(t, 0, 3.2, 0.4)
    text_alpha(im, (W // 2, 720), "One small display fix", F_H1, TXT, a, "mm")
    y = 820
    for ln in wrap("Big timer numbers now line up: no empty slot before single digits, no hole after a 1.", F_BODY, 860):
        text_alpha(im, (W // 2, y), ln, F_BODY, MUTED, a, "ma")
        y += 54
    text_alpha(im, (W // 2, 1100), "FOCUS BUDDY  ·  firmware/src/ui.cpp", F_TAG, TOMATO, a, "mm")
    return im


def outro(t):
    im = vgrad(W, H, BG2, BG).convert("RGBA")
    a = fade(t, 26.5, 30.6, 0.4)
    lines = ["What changed", "",
             "1 function in ui.cpp: +11 / -3 lines",
             "A '1' is drawn as wide as its bar",
             "Numbers left-align with the label",
             "'min' / 'sec' follow the digits",
             "",
             "Firmware still builds: 22.7% flash"]
    y = 640
    for i, ln in enumerate(lines):
        f = F_H1 if i == 0 else F_BODY
        col = TXT if i == 0 else (MUTED if i == len(lines) - 1 else TXT)
        text_alpha(im, (W // 2, y), ln, f, col, a * ease((t - 26.6 - i * 0.12) / 0.4), "mm")
        y += 90 if i == 0 else 62
    return im


def frame(t):
    if t < 3.0:
        return title_card(t)
    if t >= 26.5:
        return outro(t)
    k = min(int((t - 3.0) / 4.7), 4)
    lt = t - 3.0 - k * 4.7
    case, before, after = SHOTS[k]
    # the AFTER panel starts as BEFORE, then e-ink partial-refreshes into AFTER at 1.2 s
    p = (lt - 1.2) / 0.35
    cur = before if p <= 0 else (after if p >= 1 else np.where(NOISE < p, after, before))
    guide = ease((lt - 2.0) / 0.4)
    im = compare_image(case, before, cur, guide, fade(lt, 0, 4.7, 0.3))
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
