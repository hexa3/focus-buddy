// Focus Buddy desktop simulator: renders the *firmware's own* ui.cpp into a
// 296x128 1-bit canvas and writes a PBM.
// usage: sim <main|stats|sleep> state phase next rem_ms len_ms setProg today lifetime muted batt_mv "preset" focusMin out.pbm
#include <Adafruit_GFX.h>
#include <stdio.h>
#include "ui.h"
int main(int argc, char **argv) {
  if (argc < 15) { fprintf(stderr, "bad args\n"); return 1; }
  UiState u;
  u.state = (RunState)atoi(argv[2]); u.phase = (Phase)atoi(argv[3]); u.nextPhase = (Phase)atoi(argv[4]);
  u.remainingMs = strtoul(argv[5], 0, 10); u.phaseLenMs = strtoul(argv[6], 0, 10);
  u.setProgress = atoi(argv[7]); u.sessionsPerSet = 4; u.todayCount = atoi(argv[8]);
  u.lifetimeCount = strtoul(argv[9], 0, 10); u.muted = atoi(argv[10]); u.batteryMv = atoi(argv[11]);
  u.presetName = argv[12]; u.presetFocusMin = atoi(argv[13]);
  GFXcanvas1 c(UI_W, UI_H);
  std::string scr = argv[1];
  if (scr == "splash") ui_drawSplash(c); else if (scr == "stats") ui_drawStats(c, u); else if (scr == "sleep") ui_drawSleep(c, u); else ui_drawMain(c, u);
  FILE *f = fopen(argv[14], "wb");
  fprintf(f, "P4\n%d %d\n", UI_W, UI_H);
  const uint8_t *b = c.getBuffer();
  for (int i = 0; i < (UI_W + 7) / 8 * UI_H; i++) fputc((uint8_t)~b[i], f);  // PBM: 1 = black
  fclose(f);
  return 0;
}
