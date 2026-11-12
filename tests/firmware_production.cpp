#include "Arduino.h"
#include "../firmware/uno/sketch/sketch.ino"
void send(const char *message) { Serial.input=message; while(Serial.available()) loop(); }
int main() {
  MCUSR=_BV(WDRF); earlyReset(); setup();
  assert(wdtEnabled && localFaultLatched && !armed && pins[8]==HIGH);
  send("HELLO\nARM 1\nMOVE 2 forward\nSERVO 3 0 300\nSTOP 4\nSTATUS 5\n");
  assert(!armed && pwm.enabledWrites==0 && pins[8]==HIGH);
  assert(Serial.output.find("DONE 4 stopped")!=std::string::npos);
  assert(Serial.output.find("ERR 1 ")!=std::string::npos);
  assert(Serial.output.find("ERR 2 ")!=std::string::npos);
  assert(Serial.output.find("ERR 3 ")!=std::string::npos);
  assert(driverReady==bool(MOCK_PCA_PRESENT));
  std::cout << "production: watchdog boot, PCA presence/absence, gated ARM, no PWM, OE commanded off, STOP status PASS\n";
}
