#pragma once
#ifndef MOCK_PCA_PRESENT
#define MOCK_PCA_PRESENT 1
#endif
class Adafruit_PWMServoDriver {
public:
  unsigned enabledWrites=0;
  explicit Adafruit_PWMServoDriver(uint8_t) {}
  bool begin() { return MOCK_PCA_PRESENT; }
  void setPWMFreq(uint8_t) {}
  void setPWM(uint8_t,uint16_t,uint16_t off) { if (off!=4096) ++enabledWrites; }
};
