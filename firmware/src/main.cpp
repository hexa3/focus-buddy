// Focus Buddy: an e-ink Pomodoro desk companion
// MCU: Seeed XIAO ESP32-C3, display: 2.9" 296x128 B/W e-paper (SSD1680)
//
// Buttons
//   A (left)   short: start / pause / resume.  In alarm: start the next phase now.
//   B (middle) short: skip to the next phase.  Long (1 s): reset the current phase.
//   C (right)  short: cycle presets when idle, mute/unmute otherwise.
//              Long (1 s): show stats (today / lifetime).
//
// Power: light sleep between screen updates, deep sleep after 3 min idle
// (10 min paused). A or B wakes it from deep sleep.

#include <Arduino.h>
#include <SPI.h>
#include <Preferences.h>
#include <GxEPD2_BW.h>
#include "esp_sleep.h"
#include "driver/gpio.h"
#include "pins.h"
#include "ui.h"

// ---------------------------------------------------------------- display
#if defined(FB_PANEL_290_V1)
  #define EPD_CLASS GxEPD2_290
#elif defined(FB_PANEL_290_GDEY029T94)
  #define EPD_CLASS GxEPD2_290_GDEY029T94
#else
  #define EPD_CLASS GxEPD2_290_T94_V2
#endif

GxEPD2_BW<EPD_CLASS, EPD_CLASS::HEIGHT> display(
    EPD_CLASS(PIN_EPD_CS, PIN_EPD_DC, PIN_EPD_RST, PIN_EPD_BUSY));

static const uint16_t W = UI_W, H = UI_H;  // landscape, after setRotation(1)

// ---------------------------------------------------------------- config
struct Preset { const char* name; uint16_t focus, shortBreak, longBreak; };  // minutes
static const Preset PRESETS[] = {
    {"Classic 25/5", 25, 5, 15},
    {"Deep 50/10",   50, 10, 20},
    {"Sprint 15/3",  15, 3, 10},
    {"Monk 90/15",   90, 15, 30},
};
static const uint8_t NUM_PRESETS = sizeof(PRESETS) / sizeof(PRESETS[0]);
static const uint8_t SESSIONS_PER_SET = 4;        // long break after this many focus sessions

static const uint32_t LONG_PRESS_MS      = 1000;
static const uint32_t IDLE_SLEEP_MS      = 3UL * 60 * 1000;
static const uint32_t PAUSED_SLEEP_MS    = 10UL * 60 * 1000;
static const uint32_t ALARM_TIMEOUT_MS   = 60UL * 1000;
static const uint32_t ALARM_REPEAT_MS    = 8000;
static const uint8_t  FULL_REFRESH_EVERY = 20;    // partial updates between full refreshes

// ---------------------------------------------------------------- state

// Survives deep sleep (not power loss)
RTC_DATA_ATTR uint8_t  presetIdx   = 0;
RTC_DATA_ATTR uint8_t  setProgress = 0;   // focus sessions done in the current set
RTC_DATA_ATTR uint16_t todayCount  = 0;   // since power-up
RTC_DATA_ATTR uint8_t  phase       = FOCUS;
RTC_DATA_ATTR bool     muted       = false;
RTC_DATA_ATTR bool     sleptPaused = false;  // keep a paused session across deep sleep
RTC_DATA_ATTR uint32_t sleptRemaining = 0;

Preferences prefs;
uint32_t lifetimeCount = 0;

RunState state = IDLE;
RunState stateBeforeStats = IDLE;
uint32_t endAtMs = 0;           // RUNNING: millis() when the phase ends
uint32_t remainingMs = 0;       // IDLE/PAUSED: frozen remaining time
uint32_t lastActivityMs = 0;
uint32_t alarmStartMs = 0, lastChimeMs = 0;
bool     needRedraw = true;
int32_t  shownKey = -1;         // what the big number shows; redraw when it changes
uint8_t  partialCount = 0;
bool     forceFull = false;

// ---------------------------------------------------------------- helpers
uint32_t phaseLengthMs(uint8_t p) {
  const Preset& pr = PRESETS[presetIdx];
  uint16_t m = p == FOCUS ? pr.focus : p == SHORT_BREAK ? pr.shortBreak : pr.longBreak;
  return (uint32_t)m * 60UL * 1000UL;
}

uint32_t currentRemaining() {
  if (state == RUNNING) {
    int32_t r = (int32_t)(endAtMs - millis());
    return r > 0 ? (uint32_t)r : 0;
  }
  return remainingMs;
}

// The value shown in the big digits. Minutes (rounded up) normally, then
// 10-second steps during the last minute. Used to decide when to refresh.
int32_t displayKey(uint32_t rem) {
  if (rem > 60000) return (rem + 59999) / 60000;              // minutes
  return 1000 + ((rem + 9999) / 10000) * 10;                  // 1000+seconds
}

// ms until displayKey() changes
uint32_t msUntilNextChange(uint32_t rem) {
  if (rem == 0) return 0;
  if (rem > 60000) {
    uint32_t r = rem % 60000;
    if (r == 0) r = 60000;
    if (rem - r < 60000) r = rem - 60000;   // hand over to the seconds view on time
    return r ? r : 1;
  }
  uint32_t r = rem % 10000;
  return r ? r : 10000;
}

int readBatteryMv() {
  uint32_t acc = 0;
  for (int i = 0; i < 8; i++) acc += analogReadMilliVolts(PIN_VBAT_SENSE);
  return (int)(acc / 8) * 2;  // 1:1 divider
}

// ---------------------------------------------------------------- buzzer
struct Note { uint16_t hz, ms; };
static const Note CHIME_FOCUS_DONE[] = {{1568, 120}, {0, 40}, {2093, 120}, {0, 40}, {2637, 260}, {0, 0}};
static const Note CHIME_BREAK_DONE[] = {{2093, 150}, {0, 60}, {1568, 150}, {0, 60}, {2093, 150}, {0, 0}};
static const Note CHIME_CLICK[]      = {{2400, 15}, {0, 0}};
const Note* melody = nullptr;
uint8_t  melodyPos = 0;
uint32_t noteEndMs = 0;

void play(const Note* m) {
  if (muted && m != CHIME_CLICK) return;
  melody = m; melodyPos = 0; noteEndMs = 0;
}

void serviceBuzzer() {
  if (!melody) return;
  if (millis() < noteEndMs) return;
  const Note& n = melody[melodyPos];
  if (n.ms == 0) { noTone(PIN_BUZZER); digitalWrite(PIN_BUZZER, LOW); melody = nullptr; return; }
  if (n.hz) tone(PIN_BUZZER, n.hz); else noTone(PIN_BUZZER);
  noteEndMs = millis() + n.ms;
  melodyPos++;
}

// ---------------------------------------------------------------- buttons
struct Button { uint8_t pin; bool down; uint32_t t0; bool longFired; };
Button btns[3] = {{PIN_BTN_A}, {PIN_BTN_B}, {PIN_BTN_C}};
enum BtnEvent { EV_NONE, EV_SHORT, EV_LONG };

BtnEvent pollButton(Button& b) {
  bool d = digitalRead(b.pin) == LOW;
  uint32_t now = millis();
  if (d && !b.down) {
    if (now - b.t0 < 30) return EV_NONE;  // debounce
    b.down = true; b.t0 = now; b.longFired = false;
    lastActivityMs = now;
  } else if (!d && b.down) {
    if (now - b.t0 < 30) return EV_NONE;
    b.down = false;
    lastActivityMs = now;
    if (!b.longFired) { b.t0 = now; return EV_SHORT; }
    b.t0 = now;
  } else if (d && b.down && !b.longFired && now - b.t0 >= LONG_PRESS_MS) {
    b.longFired = true;
    return EV_LONG;
  }
  return EV_NONE;
}

bool anyButtonDown() {
  for (auto& b : btns) if (b.down || digitalRead(b.pin) == LOW) return true;
  return false;
}

// ---------------------------------------------------------------- drawing (see ui.cpp)
uint8_t nextPhase();

UiState makeUi() {
  UiState u;
  u.state = state;
  u.phase = (Phase)phase;
  u.nextPhase = (Phase)nextPhase();
  u.remainingMs = currentRemaining();
  u.phaseLenMs = phaseLengthMs(phase);
  u.setProgress = setProgress;
  u.sessionsPerSet = SESSIONS_PER_SET;
  u.todayCount = todayCount;
  u.lifetimeCount = lifetimeCount;
  u.muted = muted;
  u.batteryMv = readBatteryMv();
  u.presetName = PRESETS[presetIdx].name;
  u.presetFocusMin = PRESETS[presetIdx].focus;
  return u;
}

void drawMainScreen()  { ui_drawMain(display, makeUi()); }
void drawStatsScreen() { ui_drawStats(display, makeUi()); }
void drawSleepScreen() { ui_drawSleep(display, makeUi()); }
void drawSplashScreen() { ui_drawSplash(display); }

void refresh(void (*painter)(), bool full) {
  if (full || partialCount >= FULL_REFRESH_EVERY) {
    display.setFullWindow();
    partialCount = 0;
  } else {
    display.setPartialWindow(0, 0, W, H);
    partialCount++;
  }
  display.firstPage();
  do { painter(); } while (display.nextPage());
  display.powerOff();  // panel holds the image with zero power
}

// ---------------------------------------------------------------- timer logic
uint8_t nextPhase() {
  if (phase == FOCUS) return (setProgress % SESSIONS_PER_SET == 0) ? LONG_BREAK : SHORT_BREAK;
  return FOCUS;
}

void loadPhase(uint8_t p) {
  if (phase == LONG_BREAK && p == FOCUS) setProgress = 0;  // start a fresh set
  phase = p;
  remainingMs = phaseLengthMs(p);
  state = IDLE;
  needRedraw = true;
}

void startRunning() {
  endAtMs = millis() + remainingMs;
  state = RUNNING;
  needRedraw = true;
}

void completePhase() {
  if (phase == FOCUS) {
    setProgress++;
    todayCount++;
    lifetimeCount++;
    prefs.putUInt("lifetime", lifetimeCount);
    play(CHIME_FOCUS_DONE);
  } else {
    play(CHIME_BREAK_DONE);
  }
  state = ALARM;
  alarmStartMs = lastChimeMs = millis();
  remainingMs = 0;
  forceFull = true;
  needRedraw = true;
}

void handleButtons() {
  BtnEvent a = pollButton(btns[0]);
  BtnEvent b = pollButton(btns[1]);
  BtnEvent c = pollButton(btns[2]);
  if (a == EV_NONE && b == EV_NONE && c == EV_NONE) return;
  play(CHIME_CLICK);

  if (state == STATS) {  // any button leaves the stats screen
    state = stateBeforeStats;
    forceFull = true; needRedraw = true;
    return;
  }

  if (state == ALARM) {
    melody = nullptr; noTone(PIN_BUZZER);
    uint8_t n = nextPhase();
    loadPhase(n);
    if (a == EV_SHORT) startRunning();
    return;
  }

  if (a == EV_SHORT) {
    if (state == RUNNING) { remainingMs = currentRemaining(); state = PAUSED; }
    else startRunning();
    needRedraw = true;
  }
  if (b == EV_SHORT) {           // skip
    if (phase == FOCUS) setProgress++;  // count skip toward the set, not the stats
    if (setProgress > SESSIONS_PER_SET) setProgress = SESSIONS_PER_SET;
    loadPhase(nextPhase());
  }
  if (b == EV_LONG) {            // reset current phase
    loadPhase(phase);
    forceFull = true;
  }
  if (c == EV_SHORT) {
    if (state == IDLE) {
      presetIdx = (presetIdx + 1) % NUM_PRESETS;
      prefs.putUChar("preset", presetIdx);
      loadPhase(phase);
    } else {
      muted = !muted;
      needRedraw = true;
    }
  }
  if (c == EV_LONG) {
    stateBeforeStats = state;
    state = STATS;
    forceFull = true; needRedraw = true;
  }
}

// ---------------------------------------------------------------- power
void goDeepSleep() {
  sleptPaused = state == PAUSED;
  sleptRemaining = remainingMs;
  refresh(drawSleepScreen, true);
  display.hibernate();
  noTone(PIN_BUZZER);
  pinMode(PIN_BUZZER, OUTPUT); digitalWrite(PIN_BUZZER, LOW);
  gpio_hold_en((gpio_num_t)PIN_BUZZER);
  gpio_deep_sleep_hold_en();
  esp_deep_sleep_enable_gpio_wakeup((1ULL << PIN_BTN_A) | (1ULL << PIN_BTN_B), ESP_GPIO_WAKEUP_GPIO_LOW);
  esp_deep_sleep_start();
}

void lightSleepFor(uint32_t ms) {
#if FB_LIGHT_SLEEP
  if (ms < 30) { delay(ms); return; }
  esp_sleep_enable_timer_wakeup((uint64_t)ms * 1000ULL);
  for (auto& b : btns) gpio_wakeup_enable((gpio_num_t)b.pin, GPIO_INTR_LOW_LEVEL);
  esp_sleep_enable_gpio_wakeup();
  esp_light_sleep_start();
  for (auto& b : btns) gpio_wakeup_disable((gpio_num_t)b.pin);
  esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);
#else
  delay(ms < 20 ? ms : 20);
#endif
}

// ---------------------------------------------------------------- main
void setup() {
  gpio_hold_dis((gpio_num_t)PIN_BUZZER);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  for (auto& b : btns) pinMode(b.pin, INPUT_PULLUP);
  analogSetPinAttenuation(PIN_VBAT_SENSE, ADC_11db);

  Serial.begin(115200);
  prefs.begin("focusbuddy", false);
  lifetimeCount = prefs.getUInt("lifetime", 0);

  bool fromDeepSleep = esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_GPIO;
  if (!fromDeepSleep) {
    presetIdx = prefs.getUChar("preset", 0) % NUM_PRESETS;
    setProgress = 0; todayCount = 0; phase = FOCUS;
  }

  SPI.begin(PIN_EPD_SCK, -1, PIN_EPD_MOSI, -1);
  display.init(0, !fromDeepSleep, 2, false);
  display.setRotation(1);

  // Cold boot: say hi and show the buttons for a moment.
  if (!fromDeepSleep) {
    refresh(drawSplashScreen, true);
    delay(2500);
  }

  // Swallow the press that woke us so it doesn't also start a session.
  if (fromDeepSleep) {
    uint32_t t = millis();
    while (anyButtonDown() && millis() - t < 3000) delay(10);
    for (auto& b : btns) { b.down = false; b.t0 = millis(); }
  }

  loadPhase(phase);
  if (fromDeepSleep && sleptPaused) { state = PAUSED; remainingMs = sleptRemaining; }
  sleptPaused = false;
  forceFull = !fromDeepSleep;
  lastActivityMs = millis();
}

void loop() {
  handleButtons();
  serviceBuzzer();

  uint32_t now = millis();
  if (state == RUNNING && currentRemaining() == 0) completePhase();

  if (state == ALARM) {
    if (!melody && !muted && now - lastChimeMs > ALARM_REPEAT_MS) {
      play(phase == FOCUS ? CHIME_FOCUS_DONE : CHIME_BREAK_DONE);
      lastChimeMs = now;
    }
    if (now - alarmStartMs > ALARM_TIMEOUT_MS) {  // nobody around: load the next phase, wait
      loadPhase(nextPhase());
      lastActivityMs = now;
    }
  }

  if (state == RUNNING) {
    int32_t k = displayKey(currentRemaining());
    if (k != shownKey) needRedraw = true;
  }

  if (needRedraw && !melody) {
    shownKey = displayKey(currentRemaining());
    refresh(state == STATS ? drawStatsScreen : drawMainScreen, forceFull);
    needRedraw = false;
    forceFull = false;
  }

  // ------- sleep decisions
  if (melody || anyButtonDown() || needRedraw) { delay(5); return; }
  if (now - lastActivityMs < 1500) { delay(10); return; }   // stay responsive right after a press

  if (state == IDLE || state == PAUSED || state == STATS) {
    uint32_t limit = state == PAUSED ? PAUSED_SLEEP_MS : IDLE_SLEEP_MS;
    uint32_t idleFor = now - lastActivityMs;
    if (idleFor >= limit) goDeepSleep();
    lightSleepFor(min<uint32_t>(limit - idleFor, 60000));
  } else if (state == RUNNING) {
    lightSleepFor(msUntilNextChange(currentRemaining()) + 5);
  } else {  // ALARM
    lightSleepFor(min<uint32_t>(ALARM_REPEAT_MS - min<uint32_t>(now - lastChimeMs, ALARM_REPEAT_MS), 1000));
  }
}
