"""Focus Buddy progress reel, vertical 9:16 (1080x1920) for phones / Reels / Shorts.

Reuses the timeline, firmware screens and progress list from make_reel.py;
only the layout differs.

  python3 video/make_reel_vertical.py              -> video/focus-buddy-progress-reel-vertical.mp4
  python3 video/make_reel_vertical.py --still 30 x.png
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_reel as R  # noqa: E402
from make_reel import (BG, BG2, BODY_DARK, LEAF, MUTED, TOMATO, TXT, ease, fade,  # noqa: E402
                       font, text_alpha, check_icon, buddy_logo, screen_state, vgrad)

W, H, FPS, DUR = 1080, 1920, 30, 60.0
OUT = os.path.join(R.ROOT, "video", "focus-buddy-progress-reel-vertical.mp4")

F_TITLE = font("NotoSans-Black.ttf", 118)
F_H1 = font("NotoSans-Bold.ttf", 66)
F_H2 = font("NotoSans-Bold.ttf", 50)
F_BODY = font("NotoSans-Medium.ttf", 40)
F_ROWH = font("NotoSans-Bold.ttf", 36)
F_SMALL = font("NotoSans-Medium.ttf", 29)
F_TINY = font("NotoSans-Medium.ttf", 24)
F_MONO = font(R.MONO, 34)
F_MONO_S = font(R.MONO, 26)

BACKDROP = vgrad(W, H, BG2, BG)
_meas = ImageDraw.Draw(Image.new("L", (1, 1)))


def wrap(s, fnt, maxw):
    lines, cur = [], ""
    for word in s.split(" "):
        test = (cur + " " + word).strip()
        if _meas.textlength(test, font=fnt) <= maxw:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_wrap(base, x, y, s, fnt, fill, a, maxw, lh, center=False):
    """Draw wrapped text; returns the y below the last line."""
    for ln in wrap(s, fnt, maxw):
        if center:
            text_alpha(base, (x, y), ln, fnt, fill, a, "ma")
        else:
            text_alpha(base, (x, y), ln, fnt, fill, a)
        y += lh
    return y


# ------------------------------------------------------------------ device (portrait layout)
SCALE = 3
SW, SH = 296 * SCALE, 128 * SCALE
DX = (W - SW) // 2
DY = 760
BODY_BOX = (DX - 58, DY - 58, DX + SW + 58, DY + SH + 215)
BTN_Y = DY + SH + 110
BTN_X = [W // 2 - 290, W // 2, W // 2 + 290]
BTN_LABEL = ["start / pause", "skip / wake", "preset / stats"]


def make_device():
    im = BACKDROP.copy()
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle((BODY_BOX[0] + 8, BODY_BOX[1] + 28, BODY_BOX[2] + 8, BODY_BOX[3] + 38), 60, fill=150)
    im.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(36)))
    body = vgrad(BODY_BOX[2] - BODY_BOX[0], BODY_BOX[3] - BODY_BOX[1], (226, 221, 209), BODY_DARK)
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, body.width - 1, body.height - 1), 56, fill=255)
    im.paste(body, BODY_BOX[:2], mask)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(BODY_BOX, 56, outline=(240, 236, 226), width=2)
    d.rounded_rectangle((DX - 22, DY - 22, DX + SW + 22, DY + SH + 22), 16, fill=(40, 40, 44))
    d.rounded_rectangle((DX - 6, DY - 6, DX + SW + 6, DY + SH + 6), 5, fill=(205, 203, 192))
    for x, lab in zip(BTN_X, BTN_LABEL):
        d.ellipse((x - 46, BTN_Y - 46, x + 46, BTN_Y + 46), fill=(170, 164, 150))
        d.text((x, BTN_Y + 72), lab, font=F_TINY, fill=(95, 92, 84), anchor="mm")
    return im


DEVICE = make_device()
PAPER_TEX = R.np.random.default_rng(3).normal(0, 3.2, (SH, SW, 1)).astype(R.np.float32)


def render_panel(ink):
    np = R.np
    big = np.kron(ink, np.ones((SCALE, SCALE)))[:, :, None]
    rgb = np.array(R.PAPER) * (1 - big) + np.array(R.INK) * big + PAPER_TEX
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def overlay_box(im, box, r, fill, a, outline=None, width=0):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(box, r, fill=fill + (int(fill_alpha(a)),),
                                          outline=(outline + (int(255 * a),)) if outline else None, width=width)
    im.alpha_composite(lay)


def fill_alpha(a):
    return 230 * a


# ------------------------------------------------------------------ scenes
def scene_title(t):
    im = BACKDROP.convert("RGBA")
    a = fade(t, 0, 5.3, 0.6)
    lg = buddy_logo(5, TOMATO)
    lg.putalpha(Image.eval(lg.getchannel("A"), lambda v: int(v * a)))
    bob = int(10 * math.sin(t * 2.4))
    im.alpha_composite(lg, (W // 2 - lg.width // 2, 260 + bob))
    text_alpha(im, (W // 2, 1060), "FOCUS", F_TITLE, TXT, ease((t - 0.5) / 0.6) * a, "mm")
    text_alpha(im, (W // 2, 1180), "BUDDY", F_TITLE, TXT, ease((t - 0.7) / 0.6) * a, "mm")
    text_wrap(im, W // 2, 1290, "an e-ink Pomodoro companion for your desk", F_BODY, MUTED,
              ease((t - 1.0) / 0.6) * a, 860, 54, center=True)
    for i, ln in enumerate(["HALF LIFE", "PROGRESS REEL", "DISPLAY DEEP-DIVE"]):
        text_alpha(im, (W // 2, 1500 + i * 56), ln, F_MONO, TOMATO, ease((t - 1.6 - i * 0.15) / 0.5) * a, "mm")
    return im


def scene_disclaimer(t):
    im = BACKDROP.convert("RGBA")
    a = fade(t, 5.3, 10.8, 0.5)
    if a > 0:
        overlay_box(im, (60, 470, W - 60, 1380), 40, (42, 45, 54), a, TOMATO, 3)
    x, mw = 120, W - 240
    text_alpha(im, (x, 550), "DISCLAIMER", F_MONO, TOMATO, a)
    y = text_wrap(im, x, 620, "We joined Half Life halfway through.", F_H1, TXT, a, mw, 84)
    y += 40
    y = text_wrap(im, x, y, "Everything else is already planned: PCB routing, Gerbers, the 3D-printed enclosure and the build guide.",
                  F_BODY, TXT, a * ease((t - 5.9) / 0.4), mw, 56)
    y += 40
    text_wrap(im, x, y, "This reel shows only what actually exists today. No hardware has been assembled yet. "
              "Every screen you'll see is drawn by the real firmware code, compiled and run on a PC.",
              F_BODY, MUTED, a * ease((t - 6.3) / 0.4), mw, 56)
    return im


def scene_demo(t):
    im = DEVICE.copy()
    im.paste(render_panel(screen_state(t)), (DX, DY))
    im = im.convert("RGBA")
    d = ImageDraw.Draw(im)
    for i, x in enumerate(BTN_X):
        pressed, hold_p, longp = False, 0, False
        for pt, b, hold in R.PRESS:
            if b == i and pt <= t <= pt + hold:
                pressed, hold_p, longp = True, (t - pt) / hold, hold > 0.5
        off = 4 if pressed else 0
        if pressed:
            d.ellipse((x - 58, BTN_Y - 58, x + 58, BTN_Y + 58), outline=TOMATO, width=5)
            if longp:
                d.arc((x - 70, BTN_Y - 70, x + 70, BTN_Y + 70), -90, -90 + 360 * hold_p, fill=TOMATO, width=7)
        d.ellipse((x - 36, BTN_Y - 36 + off, x + 36, BTN_Y + 36 + off),
                  fill=(120, 116, 106) if pressed else (88, 86, 82))
        d.text((x, BTN_Y + off), "ABC"[i], font=F_H2, fill=(230, 226, 214), anchor="mm")

    # buzzer: sound waves rising above the device
    if 23.6 <= t <= 26.2:
        cx, cy = W // 2, BODY_BOX[1] - 10
        for k in range(3):
            ph = (t * 1.6 + k / 3) % 1
            r = 24 + ph * 72
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).arc((cx - r, cy - r, cx + r, cy + r), 210, 330, fill=TOMATO + (int(255 * (1 - ph)),), width=7)
            im.alpha_composite(lay)
        text_alpha(im, (cx + 170, cy - 50), "beep!", F_MONO, TOMATO, 1, "mm")

    for b0, b1, txt in R.BADGE:
        a = fade(t, b0, b1, 0.25)
        if a:
            bx1 = BODY_BOX[2]
            overlay_box(im, (bx1 - 290, BODY_BOX[1] - 80, bx1, BODY_BOX[1] - 24), 28, TOMATO, a)
            text_alpha(im, (bx1 - 145, BODY_BOX[1] - 52), txt, F_MONO_S, (255, 255, 255), a, "mm")

    # caption above the device, big enough for a phone
    for c0, c1, title, body in R.CAP:
        a = fade(t, c0, c1, 0.3)
        if a:
            overlay_box(im, (60, 330, W - 60, 600), 34, (14, 15, 19), a)
            text_alpha(im, (110, 370), title.upper(), F_MONO_S, TOMATO, a)
            text_wrap(im, 110, 418, body, F_BODY, TXT, a, W - 220, 54)

    da = fade(t, R.DEMO0, R.DEMO1, 0.4)
    text_alpha(im, (W // 2, 190), "DISPLAY DEEP-DIVE", F_MONO, MUTED, da, "mm")
    text_alpha(im, (W // 2, 250), "focus buddy", F_SMALL, (110, 114, 124), da, "mm")
    text_wrap(im, W // 2, 1560, "SIMULATED: pixels come from the real firmware (ui.cpp) running on a PC. "
              "Refresh flashes and the device body are animation.", F_TINY, MUTED, da, W - 160, 34, center=True)
    a = 1 - min(ease((t - R.DEMO0) / 0.45), ease((R.DEMO1 - t) / 0.45))
    if a > 0:
        im.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, int(255 * a))))
    return im


def scene_progress(t):
    im = BACKDROP.convert("RGBA")
    T0, T1 = 45.4, 56.2
    a = fade(t, T0, T1, 0.45)
    text_alpha(im, (70, 150), "WHERE WE ACTUALLY ARE", F_MONO, TOMATO, a)
    text_alpha(im, (70, 200), "Real progress,", F_H1, TXT, a)
    text_alpha(im, (70, 280), "as of today", F_H1, TXT, a)
    y = 420
    for i, (k, head, sub) in enumerate(R.PROGRESS):
        ai = a * ease((t - T0 - 0.6 - i * 0.55) / 0.4)
        hl = wrap(head, F_ROWH, W - 260)
        sl = wrap(sub, F_TINY, W - 260)
        rh = 64 + len(hl) * 46 + len(sl) * 34 + 18
        if ai > 0:
            overlay_box(im, (50, y, W - 50, y + rh), 24, (38, 41, 50), ai * 0.9)
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            check_icon(ImageDraw.Draw(lay), 108, y + 52, 24, k)
            lay.putalpha(Image.eval(lay.getchannel("A"), lambda v: int(v * ai)))
            im.alpha_composite(lay)
            tag = {"done": "DONE", "wip": "IN PROGRESS", "todo": "PLANNED"}[k]
            col = {"done": LEAF, "wip": TOMATO, "todo": MUTED}[k]
            text_alpha(im, (160, y + 20), tag, F_MONO_S, col, ai)
            yy = y + 62
            for ln in hl:
                text_alpha(im, (160, yy), ln, F_ROWH, TXT if k != "todo" else MUTED, ai)
                yy += 46
            for ln in sl:
                text_alpha(im, (160, yy + 4), ln, F_TINY, MUTED, ai)
                yy += 34
        y += rh + 18
    return im


def scene_outro(t):
    im = BACKDROP.convert("RGBA")
    a = fade(t, 56.2, 60.5, 0.5)
    lg = buddy_logo(3, TOMATO)
    lg.putalpha(Image.eval(lg.getchannel("A"), lambda v: int(v * a)))
    im.alpha_composite(lg, (W // 2 - lg.width // 2, 420))
    text_alpha(im, (W // 2, 930), "Next up", F_MONO, TOMATO, a, "mm")
    for i, ln in enumerate(["route the board", "print the case", "flash real hardware"]):
        text_alpha(im, (W // 2, 1020 + i * 80), ln, F_H2, TXT, a * ease((t - 56.5 - i * 0.25) / 0.4), "mm")
    text_wrap(im, W // 2, 1320, "Joined halfway. The rest is planned. See you at the finish line.",
              F_BODY, MUTED, a, 860, 56, center=True)
    text_alpha(im, (W // 2, 1560), "FOCUS BUDDY  ·  HALF LIFE", F_MONO, TOMATO, a, "mm")
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
        i = sys.argv.index("--still")
        frame(float(sys.argv[i + 1])).save(sys.argv[i + 2])
        return
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-threads", "2",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame(i / FPS).tobytes())
        if i % 300 == 0:
            print(f"frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
