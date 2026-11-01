#!/bin/sh
# Builds the desktop simulator. Run `pio run` in firmware/ once first so the Adafruit GFX library is downloaded.
cd "$(dirname "$0")/.."
G="firmware/.pio/libdeps/waveshare_290_v2/Adafruit GFX Library"
g++ -O2 -std=c++17 -DARDUINO=100 -Isim/shim -I"$G" -Ifirmware/include sim/sim.cpp firmware/src/ui.cpp "$G/Adafruit_GFX.cpp" -o sim/fbsim
