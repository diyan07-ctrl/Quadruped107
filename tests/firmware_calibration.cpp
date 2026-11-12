#include "Arduino.h"
#include "../firmware/uno/direct_calibration/direct_calibration.ino"
void send(const char *message) { Serial.input=message; while(Serial.available()) loop(); }
int main() {
  earlyReset(); setup();
  assert(wdtEnabled && !signalOutput.attached && modes[12]==INPUT);
  send("ENABLE 0 POWER_SUPPORT_REVIEWED\nSTEP 1\nPING\nSTOP\nHELLO\n");
  assert(!session.enabled && !signalOutput.attached && signalOutput.writes==0);
  assert(Serial.output.find("commissioning_inhibited")!=std::string::npos);
  assert(Serial.output.find("signal_disabled")!=std::string::npos);
  std::cout << "direct calibration: boot disabled, unknown endpoints, no signal, STOP, reset PASS\n";
}
