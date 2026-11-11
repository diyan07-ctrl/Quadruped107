#pragma once
#include <stdint.h>

// Pure cooperative state, shared by AVR and deterministic native tests.
// Profile 0 is unconfigured. Profile 1 is confirmed URM37 V5 PWM trigger mode.
struct RangeAcquisition {
  uint32_t started=0, edgeAt=0, acquired=0, lastStart=0;
  uint16_t mm=0;
  uint8_t phase=0, fault=1;
  bool valid=false;
  bool due(uint32_t now) const { return phase==0 && uint32_t(now-lastStart)>=200000UL; }
  void start(uint32_t now) {
    started=lastStart=now; phase=1;
  }
  void edge(bool high, uint32_t now) {
    if (phase==2 && !high) { edgeAt=now; phase=3; }
    else if (phase==3 && high) {
      uint32_t width=now-edgeAt;
      // V5 documentation: low pulse 50 us/cm; >=50000 us is invalid.
      uint32_t distance=width/5;
      valid=width<50000UL && distance>=20 && distance<=4000;
      mm=valid ? distance : 0; acquired=now; phase=0; fault=valid ? 0 : 2;
    }
  }
  bool tick(uint32_t now) {
    bool release=false;
    if (phase==1 && uint32_t(now-started)>=10) { phase=2; release=true; }
    if (phase && uint32_t(now-started)>=60000UL) {
      phase=0; valid=false; fault=2; acquired=now;
    }
    return release;
  }
};

struct TouchInput {
  uint32_t changed=0, held=0;
  bool initialized=false, raw=false, pressed=false, ready=false, stuck=false;
  void scan(bool active, uint32_t now) {
    if (!initialized) {
      initialized=true; raw=pressed=active; changed=held=now;
      // Boot while pressed must first release before becoming valid.
      ready=false; return;
    }
    if (active!=raw) { raw=active; changed=now; }
    if (uint32_t(now-changed)>=20) {
      if (pressed!=raw) { pressed=raw; held=now; }
      if (!pressed) { ready=true; stuck=false; }
    }
    if (pressed && uint32_t(now-held)>=2000) { stuck=true; ready=false; }
  }
};
