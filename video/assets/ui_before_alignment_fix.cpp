#include "ui.h"
#include <stdio.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>

static void centerText(Adafruit_GFX& g, const char* s, int16_t cx, int16_t baseline, const GFXfont* f) {
  g.setFont(f);
  int16_t x1, y1; uint16_t w, h;
  g.getTextBounds(s, 0, baseline, &x1, &y1, &w, &h);
  g.setCursor(cx - (int16_t)w / 2 - x1, baseline);
  g.print(s);
}

// Seven-segment style digit, crisp at any size.
static void drawSegDigit(Adafruit_GFX& g, int16_t x, int16_t y, int16_t w, int16_t h, int16_t t, uint8_t d) {
  static const uint8_t SEG[10] = {0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F};
  uint8_t s = SEG[d % 10];
  int16_t hh = (h - t) / 2;
  const uint16_t C = FB_BLACK;
  if (s & 0x01) g.fillRoundRect(x + t / 2, y, w - t, t, t / 3, C);                  // a
  if (s & 0x02) g.fillRoundRect(x + w - t, y + t / 2, t, hh, t / 3, C);             // b
  if (s & 0x04) g.fillRoundRect(x + w - t, y + hh + t / 2, t, hh, t / 3, C);        // c
  if (s & 0x08) g.fillRoundRect(x + t / 2, y + h - t, w - t, t, t / 3, C);          // d
  if (s & 0x10) g.fillRoundRect(x, y + hh + t / 2, t, hh, t / 3, C);                // e
  if (s & 0x20) g.fillRoundRect(x, y + t / 2, t, hh, t / 3, C);                     // f
  if (s & 0x40) g.fillRoundRect(x + t / 2, y + hh, w - t, t, t / 3, C);             // g
}

static void thickCircle(Adafruit_GFX& g, int16_t x, int16_t y, int16_t r, uint8_t t, uint16_t c) {
  for (uint8_t i = 0; i < t; i++) g.drawCircle(x, y, r - i, c);
}

static void sparkle(Adafruit_GFX& g, int16_t x, int16_t y, int16_t r) {
  g.drawFastHLine(x - r, y, 2 * r + 1, FB_BLACK);
  g.drawFastVLine(x, y - r, 2 * r + 1, FB_BLACK);
  g.fillRect(x - 1, y - 1, 3, 3, FB_BLACK);
}

const char* ui_phaseName(uint8_t p) {
  return p == FOCUS ? "FOCUS" : p == SHORT_BREAK ? "BREAK" : "LONG BREAK";
}

// The buddy: a little tomato with a face.
void ui_drawBuddy(Adafruit_GFX& g, int16_t cx, int16_t cy, Mood mood) {
  const uint16_t K = FB_BLACK, Wt = FB_WHITE;
  const int16_t r = 40;
  thickCircle(g, cx, cy, r, 3, K);
  // leaves + stem
  g.fillTriangle(cx - 2, cy - r + 1, cx - 18, cy - r - 4, cx - 6, cy - r + 8, K);
  g.fillTriangle(cx + 2, cy - r + 1, cx + 18, cy - r - 4, cx + 6, cy - r + 8, K);
  g.fillTriangle(cx - 4, cy - r + 2, cx + 4, cy - r + 2, cx, cy - r - 10, K);
  g.fillRect(cx - 1, cy - r - 14, 3, 6, K);

  const int16_t ex = 14, ey = cy - 6;
  switch (mood) {
    case M_FOCUS:  // determined: flat brows, focused pupils
      g.fillRect(cx - ex - 9, ey - 12, 16, 3, K);
      g.fillRect(cx + ex - 7, ey - 12, 16, 3, K);
      g.fillCircle(cx - ex, ey, 5, K);
      g.fillCircle(cx + ex, ey, 5, K);
      g.fillRect(cx - 7, cy + 16, 14, 3, K);
      break;
    case M_BREAK:  // happy ^ ^
      for (int s = -1; s <= 1; s += 2) {
        int16_t x = cx + s * ex;
        g.drawLine(x - 7, ey + 3, x, ey - 4, K); g.drawLine(x - 7, ey + 4, x, ey - 3, K);
        g.drawLine(x, ey - 4, x + 7, ey + 3, K); g.drawLine(x, ey - 3, x + 7, ey + 4, K);
      }
      g.fillCircle(cx, cy + 12, 10, K);
      g.fillRect(cx - 11, cy + 1, 23, 11, Wt);
      break;
    case M_PAUSED:  // o_o
      thickCircle(g, cx - ex, ey, 6, 2, K);
      thickCircle(g, cx + ex, ey, 6, 2, K);
      g.fillRect(cx - 5, cy + 16, 10, 3, K);
      break;
    case M_DONE:  // starry eyes, big grin
      for (int s = -1; s <= 1; s += 2) {
        int16_t x = cx + s * ex;
        g.fillTriangle(x, ey - 8, x - 7, ey + 5, x + 7, ey + 5, K);
        g.fillTriangle(x, ey + 9, x - 7, ey - 3, x + 7, ey - 3, K);
      }
      g.fillCircle(cx, cy + 10, 13, K);
      g.fillRect(cx - 14, cy - 4, 29, 14, Wt);
      sparkle(g, cx + r + 2, cy - r + 6, 5);
      sparkle(g, cx - r + 2, cy - r + 4, 4);
      sparkle(g, cx + r + 4, cy + r - 14, 3);
      break;
    case M_SLEEP:  // closed eyes + zzz
      g.fillRect(cx - ex - 7, ey, 14, 3, K);
      g.fillRect(cx + ex - 7, ey, 14, 3, K);
      thickCircle(g, cx, cy + 16, 4, 2, K);
      g.setFont(&FreeSansBold9pt7b);
      g.setCursor(cx + r - 2, cy - r + 4);  g.print("z");
      g.setCursor(cx + r + 8, cy - r - 8);  g.print("Z");
      break;
    case M_IDLE:
    default:  // friendly
      g.fillCircle(cx - ex, ey, 6, K);
      g.fillCircle(cx + ex, ey, 6, K);
      g.fillCircle(cx - ex + 2, ey - 2, 2, Wt);
      g.fillCircle(cx + ex + 2, ey - 2, 2, Wt);
      g.fillCircle(cx, cy + 10, 9, K);
      g.fillCircle(cx, cy + 6, 9, Wt);
      break;
  }
  if (mood != M_SLEEP) {  // cheeks
    for (int16_t i = -3; i <= 3; i += 2) {
      g.drawPixel(cx - ex - 10 + i, cy + 8, K);
      g.drawPixel(cx + ex + 10 + i, cy + 8, K);
    }
  }
}

static void drawBattery(Adafruit_GFX& g, int16_t x, int16_t y, int mv) {
  if (mv < 3000 || mv > 4500) return;  // no battery fitted (or USB only)
  int pct = (mv - 3300) * 100 / (4150 - 3300);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  g.drawRect(x, y, 22, 11, FB_BLACK);
  g.fillRect(x + 22, y + 3, 2, 5, FB_BLACK);
  g.fillRect(x + 2, y + 2, (18 * pct) / 100, 7, FB_BLACK);
}

static void drawSetDots(Adafruit_GFX& g, int16_t x, int16_t y, const UiState& s) {
  for (uint8_t i = 0; i < s.sessionsPerSet; i++) {
    int16_t cx = x + i * 14;
    if (i < s.setProgress) g.fillCircle(cx, y, 5, FB_BLACK);
    else g.drawCircle(cx, y, 5, FB_BLACK);
  }
}

static Mood moodFor(const UiState& s) {
  switch (s.state) {
    case RUNNING: return s.phase == FOCUS ? M_FOCUS : M_BREAK;
    case PAUSED:  return M_PAUSED;
    case ALARM:   return M_DONE;
    default:      return M_IDLE;
  }
}

void ui_drawMain(Adafruit_GFX& g, const UiState& s) {
  g.fillScreen(FB_WHITE);
  g.setTextColor(FB_BLACK);
  ui_drawBuddy(g, 52, 62, moodFor(s));

  const int16_t X0 = 112;
  uint32_t rem = s.remainingMs;
  char buf[32];

  if (s.state == ALARM) {
    centerText(g, s.phase == FOCUS ? "Nice work!" : "Break over!", X0 + 90, 40, &FreeSansBold12pt7b);
    snprintf(buf, sizeof(buf), "A: start %s",
             s.nextPhase == FOCUS ? "focus" : s.nextPhase == SHORT_BREAK ? "break" : "long break");
    centerText(g, buf, X0 + 90, 66, &FreeSans9pt7b);
    centerText(g, "B: later", X0 + 90, 86, &FreeSans9pt7b);
  } else {
    bool secs = rem <= 60000 && s.state != IDLE;
    uint32_t v = secs ? (rem + 999) / 1000 : (rem + 59999) / 60000;
    if (v > 99) v = 99;
    const int16_t dw = 38, dh = 66, dt = 9, gap = 8, dy = 6;
    if (v >= 10) drawSegDigit(g, X0, dy, dw, dh, dt, v / 10);
    drawSegDigit(g, X0 + dw + gap, dy, dw, dh, dt, v % 10);
    g.setFont(&FreeSansBold12pt7b);
    g.setCursor(X0 + 2 * dw + gap + 8, dy + dh);
    g.print(secs ? "sec" : "min");

    // phase label; never wider than the panel (GFX would wrap it onto a new line)
    g.setFont(&FreeSansBold9pt7b);
    g.setTextWrap(false);
    g.setCursor(X0, 94);
    g.print(ui_phaseName(s.phase));
    int16_t lx = g.getCursorX() + 8;
    if (s.state == PAUSED) {               // pause icon instead of text
      g.fillRect(lx, 81, 4, 13, FB_BLACK);
      g.fillRect(lx + 7, 81, 4, 13, FB_BLACK);
    } else if (s.state == IDLE) {
      int16_t x1, y1; uint16_t tw, th;
      g.setFont(&FreeSans9pt7b);
      g.getTextBounds("press A", 0, 94, &x1, &y1, &tw, &th);
      if (lx + (int16_t)tw <= UI_W - 4) { g.setCursor(lx, 94); g.print("press A"); }
    }

    uint32_t len = s.phaseLenMs;
    uint32_t done = len > rem ? len - rem : 0;
    int16_t bw = UI_W - X0 - 6;
    g.drawRoundRect(X0, 100, bw, 10, 4, FB_BLACK);
    int16_t fw = (int32_t)(bw - 4) * (int64_t)done / (len ? len : 1);
    if (fw > 0) g.fillRoundRect(X0 + 2, 102, fw, 6, 2, FB_BLACK);
  }

  drawSetDots(g, X0 + 5, 120, s);
  g.setFont(&FreeSans9pt7b);
  snprintf(buf, sizeof(buf), "x%u", s.todayCount);
  g.setCursor(X0 + 62, 125);
  g.print(buf);
  if (s.muted) { g.setCursor(X0 + 100, 125); g.print("mute"); }
  drawBattery(g, UI_W - 28, 115, s.batteryMv);
}

void ui_drawStats(Adafruit_GFX& g, const UiState& s) {
  g.fillScreen(FB_WHITE);
  g.setTextColor(FB_BLACK);
  ui_drawBuddy(g, 52, 62, M_DONE);
  char buf[40];
  centerText(g, "Your focus", 204, 26, &FreeSansBold12pt7b);
  snprintf(buf, sizeof(buf), "Today: %u sessions", s.todayCount);
  centerText(g, buf, 204, 54, &FreeSans9pt7b);
  snprintf(buf, sizeof(buf), "All time: %lu", (unsigned long)s.lifetimeCount);
  centerText(g, buf, 204, 76, &FreeSans9pt7b);
  uint32_t mins = s.lifetimeCount * s.presetFocusMin;
  snprintf(buf, sizeof(buf), "~%lu h %lu m focused", (unsigned long)(mins / 60), (unsigned long)(mins % 60));
  centerText(g, buf, 204, 98, &FreeSans9pt7b);
  centerText(g, s.presetName, 204, 122, &FreeSansBold9pt7b);
}

void ui_drawSleep(Adafruit_GFX& g, const UiState& s) {
  g.fillScreen(FB_WHITE);
  g.setTextColor(FB_BLACK);
  ui_drawBuddy(g, 52, 64, M_SLEEP);
  centerText(g, "Napping...", 204, 46, &FreeSansBold12pt7b);
  centerText(g, "press A or B to wake", 204, 76, &FreeSans9pt7b);
  char buf[32];
  snprintf(buf, sizeof(buf), "%u done today", s.todayCount);
  centerText(g, buf, 204, 104, &FreeSans9pt7b);
}
