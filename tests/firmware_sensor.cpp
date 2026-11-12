#include "Arduino.h"
#include "../firmware/uno/sensor_only/sensor_only.ino"
void send(const char *message) {
  Serial.input=message;
  while (Serial.available()) loop();
}
int main() {
  earlyReset(); setup();
  assert(wdtEnabled && modes[8]==INPUT);
  assert(Serial.output=="READY Quadruped107 1\n");
  send("ARM 1\nMOVE 2 forward\nSERVO 3 0 300\nSTOP 4\nCAPS 5\nTELEM 6 5 2\n");
  assert(Serial.output.find("DONE 4 stopped")!=std::string::npos);
  assert(Serial.output.find("caps_sensor2")!=std::string::npos);
  assert(Serial.output.find("ERR 1 sensor_only")!=std::string::npos);
  assert(Serial.output.find("ERR 2 sensor_only")!=std::string::npos);
  assert(Serial.output.find("ERR 3 sensor_only")!=std::string::npos);
  assert(Serial.output.find("DONE 6 telemetry")!=std::string::npos);
  assert(!requested);
  send("TELEM 7 -1\nTELEM 8 11\nPOLL 9 65536\n");
  assert(rate==5 && !requested);
  fakeUs=600000; loop();
  if (URM37_PROFILE) {
    assert(pins[4]==LOW);
    fakeUs=600012; loop(); assert(pins[4]==HIGH);
    fakeUs=601000; pins[2]=LOW; echoEdge();
    fakeUs=603000; pins[2]=HIGH; echoEdge();
    fakeUs=605000; loop();
    assert(range.valid && range.mm==400 && range.acquired==603000);
  } else { assert(modes[4]==INPUT && !range.valid); }
  fakeUs=640000; send("POLL 0 42\n");
  assert(Serial.output.find("TEL 2 0 640 ")!=std::string::npos);
  assert(Serial.output.find(" 42 ")!=std::string::npos);
  size_t pos=Serial.output.find("TEL 2 ");
  assert(Serial.output.find('\n',pos)-pos<=63);
  std::cout << "WIRE_RECORD=" << Serial.output.substr(pos,Serial.output.find('\n',pos)-pos) << '\n';
  if (URM37_PROFILE && TOUCH_ENABLED_MASK==31 && TOUCH_ACTIVE_LOW_MASK==0) {
    fakeUs=660000; pins[6]=HIGH; loop();
    fakeUs=680000; loop();
    assert(touches[0].pressed);
    fakeUs=840000; send("POLL 0 43\n");
    pos=Serial.output.rfind("TEL 2 ");
    std::cout << "WIRE_TOUCH_RECORD=" << Serial.output.substr(pos,Serial.output.find('\n',pos)-pos) << '\n';
    fakeUs=850000; loop();
    fakeUs=1040000; send("POLL 0 44\n");
    pos=Serial.output.rfind("TEL 2 ");
    std::cout << "WIRE_TOUCH_RECORD=" << Serial.output.substr(pos,Serial.output.find('\n',pos)-pos) << '\n';
  }
  // Drop a report rather than wait for UART space; never replay touch interval.
  Serial.capacity=0; intervalTouches=31; fakeUs=1250000;
  send("POLL 0 45\n"); assert(intervalTouches==0);
  Serial.capacity=64;
  fakeUs=1450000; send("POLL 0 46\n");
  pos=Serial.output.rfind("TEL 2 ");
  std::cout << "WIRE_INVALID_RECORD=" << Serial.output.substr(pos,Serial.output.find('\n',pos)-pos) << '\n';
  assert(!range.valid);
  send("PING\n");
  fakeUs=1650000; send("TELEM 10 5\n");
  assert(Serial.output.find("TEL 1 ")!=std::string::npos && formatVersion==1);
  fakeUs=3100000; loop();
  assert(rate==0 && watchdogFault && Serial.output.find("FAULT watchdog")!=std::string::npos);
  send("HELLO\n"); assert(intervalTouches==0 && !requested && rate==0);
  for (int i=0;i<5;++i) assert(!touches[i].initialized);
  std::string bad(80,'X'); bad+='\n'; Serial.input=bad;
  while(Serial.available()) loop();
  assert(Serial.output.find("line_too_long")!=std::string::npos);
  for (int pin=0;pin<20;++pin)
    if (pin!=4) assert(modes[pin]!=OUTPUT); // No PWM or servo output pins.
  std::cout << "sensor firmware: identity, no actuation, configured acquisition, poll, drop, watchdog, reset, overflow PASS\n";
}
