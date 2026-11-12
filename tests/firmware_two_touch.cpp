#include "Arduino.h"
#include "../firmware/uno/sensor_only/sensor_only.ino"
static_assert(TOUCH_ENABLED_MASK==3,"Exactly D6/D7 required");
void send(const char *text) {
  Serial.input=text;
  while (Serial.available()) loop();
}
void contact(int index,bool active) {
  pins[touchPins[index]]=active != bool(TOUCH_ACTIVE_LOW_MASK & (1<<index));
}
void advance(uint32_t duration) {
  const uint32_t until=fakeUs+duration;
  while (fakeUs<until) {
    fakeUs+=1000;
    loop();
    if (range.phase==1) { fakeUs+=12; loop(); }
    if (range.phase==2 && captureEnabled) {
      pins[2]=LOW; echoEdge(); fakeUs+=4000; pins[2]=HIGH; echoEdge(); loop();
    }
    lastPing=millis(); // Mock host heartbeat; never hardware access.
  }
}
void emit(uint16_t pollToken) {
  std::string text="POLL 0 "+std::to_string(pollToken)+"\n";
  send(text.c_str());
  advance(210000);
  const size_t pos=Serial.output.rfind("TEL 2 ");
  assert(pos!=std::string::npos);
  std::cout << "WIRE_TWO=" << Serial.output.substr(pos,Serial.output.find('\n',pos)-pos) << '\n';
}
int main() {
  contact(0,false); contact(1,false);
  earlyReset(); setup();
  send("CAPS 1\nARM 2\nMOVE 3 forward\nSERVO 4 0 300\nSTOP 5\n");
  assert(Serial.output.find("caps_sensor2_t2")!=std::string::npos);
  for (int id=2;id<=4;++id) assert(Serial.output.find("ERR "+std::to_string(id)+" sensor_only")!=std::string::npos);
  assert(Serial.output.find("DONE 5 stopped")!=std::string::npos);
  advance(600000); assert(touches[0].ready && touches[1].ready && range.valid);
  send("TELEM 6 5 2\n"); emit(1);
  // Bounce before a stable back press must not qualify.
  contact(0,true); advance(5000); contact(0,false); advance(10000);
  assert(!touches[0].pressed);
  contact(0,true); advance(35000); assert(touches[0].pressed && !touches[1].pressed);
  emit(2); emit(3); // Two Pi samples establish the same qualified activation.
  contact(0,false); advance(35000); emit(4); emit(5);
  contact(1,true); advance(35000); assert(!touches[0].pressed && touches[1].pressed);
  emit(6); emit(7);
  contact(1,false); advance(35000); emit(8); emit(9);
  contact(0,true); contact(1,true); advance(35000); emit(10); emit(11);
  assert(touches[0].pressed && touches[1].pressed);
  contact(1,false); advance(2100000); emit(12);
  assert(touches[0].stuck && !touches[0].ready);
  send("HELLO\n"); advance(35000);
  assert(!touches[0].ready); // Boot/session-held input is invalid until release.
  contact(0,false); advance(35000); assert(touches[0].ready);
  send("STOP 99\n"); assert(Serial.output.find("DONE 99 stopped")!=std::string::npos);
  for (int pin=0;pin<20;++pin) if (pin!=4) assert(modes[pin]!=OUTPUT);
  std::cout << "two-touch real sketch: polarity, debounce, independent D6/D7, held, stuck, HELLO, STOP, no PWM PASS\n";
}
