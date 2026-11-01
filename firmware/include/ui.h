#pragma once
// Screen drawing for Focus Buddy. Pure Adafruit_GFX, so the exact same code
// draws on the e-paper (GxEPD2) and in the desktop simulator (GFXcanvas1).
#include <Adafruit_GFX.h>

#define FB_BLACK 0x0000
#define FB_WHITE 0xFFFF

enum Phase : uint8_t { FOCUS, SHORT_BREAK, LONG_BREAK };
enum RunState : uint8_t { IDLE, RUNNING, PAUSED, ALARM, STATS };
enum Mood : uint8_t { M_IDLE, M_FOCUS, M_BREAK, M_PAUSED, M_DONE, M_SLEEP };

struct UiState {
  RunState state;
  Phase phase;
  Phase nextPhase;
  uint32_t remainingMs;
  uint32_t phaseLenMs;
  uint8_t setProgress;
  uint8_t sessionsPerSet;
  uint16_t todayCount;
  uint32_t lifetimeCount;
  bool muted;
  int batteryMv;           // <3000 = no battery icon
  const char* presetName;
  uint16_t presetFocusMin;
};

static const uint16_t UI_W = 296, UI_H = 128;

void ui_drawMain(Adafruit_GFX& g, const UiState& s);
void ui_drawStats(Adafruit_GFX& g, const UiState& s);
void ui_drawSleep(Adafruit_GFX& g, const UiState& s);
void ui_drawSplash(Adafruit_GFX& g);
const char* ui_bubbleText(const UiState& s);
void ui_drawBuddy(Adafruit_GFX& g, int16_t cx, int16_t cy, Mood mood);
const char* ui_phaseName(uint8_t p);
