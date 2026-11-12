// Non-actuating Uno: no Wire, PCA9685, Servo, gait data or actuator command path.
#include <avr/wdt.h>
#include <util/atomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
#include "acquisition.h"

uint8_t resetCause __attribute__((section(".noinit")));
void earlyReset() __attribute__((naked, section(".init3")));
void earlyReset() { resetCause=MCUSR; MCUSR=0; wdt_disable(); }
RangeAcquisition range;
TouchInput touches[5];
const uint8_t touchPins[5]={6,7,9,10,11};
volatile uint32_t lowAt=0, pulseWidth=0, pulseAt=0;
volatile bool capturing=false, captureEnabled=false, pulseReady=false;
char input[64];
uint8_t used=0, rate=0, intervalTouches=0, formatVersion=1;
bool overflow=false;
uint16_t sequence=0, token=0;
uint32_t lastReport=0, lastScan=0, lastPing=0, firstTouchAt=0;
bool requested=false, watchdogFault=false, warmed=false;

void echoEdge() {
  if (!captureEnabled) return;
  uint32_t now=micros();
  if (!digitalRead(2)) { lowAt=now; capturing=true; }
  else if (capturing) { pulseWidth=now-lowAt; pulseAt=now; pulseReady=true; captureEnabled=false; capturing=false; }
}
void sessionReset() {
  rate=0; requested=false; intervalTouches=0;
  for (uint8_t i=0;i<5;++i) touches[i]=TouchInput();
  lastPing=millis();
}
void reply(const __FlashStringHelper *kind, const char *id, const __FlashStringHelper *detail) {
  Serial.print(kind); Serial.print(' '); Serial.print(id); Serial.print(' '); Serial.println(detail);
}
bool decimal(const char *s, uint8_t length) {
  return s && *s && strlen(s)<=length && strspn(s,"0123456789")==strlen(s);
}
void command(char *line) {
  char *context=nullptr, *verb=strtok_r(line," ",&context);
  if (!verb) return;
  if (!strcmp(verb,"HELLO")) { sessionReset(); Serial.println(F("READY Quadruped107 1")); return; }
  if (!strcmp(verb,"PING")) { lastPing=millis(); Serial.println(F("PONG")); return; }
  char *id=strtok_r(nullptr," ",&context);
  if (!decimal(id,11)) { Serial.println(F("ERR 0 invalid_id")); return; }
  char *argument=strtok_r(nullptr," ",&context);
  char *version=strtok_r(nullptr," ",&context);
  bool extra=strtok_r(nullptr," ",&context)!=nullptr;
  if (!strcmp(verb,"STOP")) { reply(F("DONE"),id,F("stopped")); return; }
  if (!strcmp(verb,"CAPS") && !argument && !version) {
#if TOUCH_ENABLED_MASK == 31
    reply(F("DONE"),id,F("caps_sensor2_t5"));
#elif TOUCH_ENABLED_MASK == 15
    reply(F("DONE"),id,F("caps_sensor2_t4"));
#elif TOUCH_ENABLED_MASK == 7
    reply(F("DONE"),id,F("caps_sensor2_t3"));
#elif TOUCH_ENABLED_MASK == 3
    reply(F("DONE"),id,F("caps_sensor2_t2"));
#else
    reply(F("DONE"),id,F("caps_sensor2_t0"));
#endif
    return;
  }
  if (!strcmp(verb,"TELEM") && decimal(argument,2) && !extra && atoi(argument)<=10 &&
      (!version || !strcmp(version,"1") || !strcmp(version,"2"))) {
    rate=atoi(argument); requested=false; intervalTouches=0;
    formatVersion=version ? atoi(version) : 1;
    reply(F("DONE"),id,F("telemetry")); return;
  }
  if (!strcmp(verb,"POLL") && decimal(argument,5) && !version && !extra && atol(argument)<=65535L && rate && formatVersion==2) {
    token=atol(argument); requested=true; return;
  }
  reply(F("ERR"),id,F("sensor_only")); // ARM/MOVE/SERVO can never reach a signal generator.
}
uint16_t ageMs(uint32_t now, uint32_t acquired) {
  uint32_t age=(now-acquired)/1000UL;
  return age>999 ? 999 : age;
}
void report(uint32_t now) {
  uint32_t ms=millis();
  if (!rate || (formatVersion==2 && !requested) || uint32_t(ms-lastReport)<1000UL/rate) return;
  lastReport=ms; requested=false;
  uint8_t mask=intervalTouches, faults=(URM37_PROFILE==0 ? 1 : range.fault);
  bool touchValid=TOUCH_ENABLED_MASK!=0;
  for (uint8_t i=0;i<5;++i) if (TOUCH_ENABLED_MASK & (1<<i)) {
    touchValid &= touches[i].ready && !touches[i].stuck;
    if (touches[i].stuck) faults|=4;
  }
  if (watchdogFault) faults|=8;
  uint16_t age=ageMs(now,range.acquired);
  bool rangeValid=URM37_PROFILE && range.valid && age<=300;
  uint8_t flags=16 | (rangeValid ? 1 : 0) | (touchValid ? 2 : 0) | ((resetCause&_BV(WDRF)) ? 64 : 0);
  char output[64];
  uint32_t touchAge=mask ? ms-firstTouchAt : ms-lastScan;
  int count;
  if (formatVersion==1) count=snprintf(output,sizeof(output),"TEL 1 %u %lu %d %u %u %u -1 -1\n",
    sequence++,static_cast<unsigned long>(ms),rangeValid ? int(range.mm) : -1,URM37_PROFILE ? 1 : 0,flags,mask);
  else count=snprintf(output,sizeof(output),"TEL 2 %u %lu %d %u %u %u %u %u %u %u\n",
    sequence++,static_cast<unsigned long>(ms),rangeValid ? int(range.mm) : -1,URM37_PROFILE ? 1 : 0,flags,mask,
    age,uint16_t(touchAge>999 ? 999 : touchAge),token,faults);
  intervalTouches=0; // Also clear on a dropped report; stale taps never replay.
  if (count>0 && count<int(sizeof(output)) && Serial.availableForWrite()>=count) Serial.write((uint8_t*)output,count);
}
void setup() {
  // D8 stays input: this target does not connect to or operate the servo driver.
  Serial.begin(115200); sessionReset();
  if (URM37_PROFILE) {
    digitalWrite(4,HIGH); pinMode(4,OUTPUT); pinMode(2,INPUT);
    attachInterrupt(digitalPinToInterrupt(2),echoEdge,CHANGE);
  }
  for (uint8_t i=0;i<5;++i) if (TOUCH_ENABLED_MASK & (1<<i)) pinMode(touchPins[i],INPUT);
  Serial.println(F("READY Quadruped107 1"));
  wdt_enable(WDTO_1S);
}
void loop() {
  wdt_reset();
  uint8_t budget=32;
  while (Serial.available() && budget--) {
    char c=Serial.read();
    if (c=='\r') continue;
    if (c=='\n') {
      input[used]=0; used=0;
      if (overflow) { overflow=false; Serial.println(F("ERR 0 line_too_long")); }
      else command(input);
    } else if (!overflow) {
      if (used<63) input[used++]=c; else { overflow=true; used=0; }
    }
  }
  uint32_t now=micros(), ms=millis();
  if (ms>=500) warmed=true;
  if (URM37_PROFILE && warmed) {
    if (range.due(now)) {
      range.start(now);
      ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { captureEnabled=false; capturing=false; pulseReady=false; }
      digitalWrite(4,LOW);
    }
    if (range.tick(now)) {
      ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { captureEnabled=true; }
      digitalWrite(4,HIGH);
    }
    uint32_t width=0, acquired=0;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { if (pulseReady) { width=pulseWidth; acquired=pulseAt; pulseReady=false; } }
    if (width) { range.edge(false,acquired-width); range.edge(true,acquired); }
    if (!range.phase) { ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { captureEnabled=false; } }
  }
  if (uint32_t(ms-lastScan)>=10) {
    lastScan=ms;
    for (uint8_t i=0;i<5;++i) if (TOUCH_ENABLED_MASK & (1<<i)) {
      bool active=digitalRead(touchPins[i])!=0;
      if (TOUCH_ACTIVE_LOW_MASK & (1<<i)) active=!active;
      touches[i].scan(active,ms);
      if (touches[i].pressed) {
        if (!intervalTouches) firstTouchAt=ms;
        intervalTouches|=1<<i;
      }
    }
  }
  if (rate && uint32_t(ms-lastPing)>1500) {
    sessionReset(); watchdogFault=true; Serial.println(F("FAULT watchdog"));
  }
  report(now);
}
