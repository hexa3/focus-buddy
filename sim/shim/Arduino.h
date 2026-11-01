// Minimal host-side Arduino shim, just enough for Adafruit_GFX + ui.cpp
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <string>
#include <algorithm>
#define PROGMEM
#define pgm_read_byte(a) (*(const uint8_t *)(a))
#define pgm_read_word(a) (*(const uint16_t *)(a))
#define pgm_read_dword(a) (*(const uint32_t *)(a))
using std::min; using std::max;
typedef bool boolean;
#define radians(d) ((d) * M_PI / 180.0)
#define degrees(r) ((r) * 180.0 / M_PI)
class __FlashStringHelper;
class String {
  std::string s;
 public:
  String(const char *c = "") : s(c) {}
  const char *c_str() const { return s.c_str(); }
  unsigned length() const { return s.size(); }
};
#include "Print.h"
