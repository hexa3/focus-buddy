#pragma once
// Focus Buddy rev A, Seeed XIAO ESP32-C3 pin map.
// Must match hardware/pcb (netlist in tools/netlist.py).

// Buttons: active LOW, 10k external pull-ups on the PCB.
// A and B are on GPIO2/3 so they can wake the chip from deep sleep (only GPIO0-5 can).
#define PIN_BTN_A      2   // D0  left   : start / pause / resume
#define PIN_BTN_B      3   // D1  middle : skip phase (hold = reset)
#define PIN_BTN_C      9   // D9  right  : preset (idle) / mute (running). This is also BOOT.

#define PIN_VBAT_SENSE 4   // D2  1M/1M divider from battery +
#define PIN_BUZZER    20   // D7  drives an NPN, buzzer between 3V3 and the collector

// E-paper (SPI, write only)
#define PIN_EPD_BUSY   5   // D3
#define PIN_EPD_RST    6   // D4
#define PIN_EPD_DC     7   // D5
#define PIN_EPD_CS    21   // D6
#define PIN_EPD_SCK    8   // D8
#define PIN_EPD_MOSI  10   // D10
