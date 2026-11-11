// COMPILE/MOCK ONLY during software readiness. No deployment automation.
#include <Servo.h>
#include <avr/wdt.h>
#include <stdlib.h>
#include <string.h>
#include <QuadrupedSafety.h>

#ifndef DIRECT_COMMISSIONING_REVIEWED
#define DIRECT_COMMISSIONING_REVIEWED 0
#endif
// Fill from individually reviewed microsecond measurements, never motion.h.
const JointQualification DirectJoints[8]={};
Servo signalOutput;
CalibrationSession session;
char input[64];
uint8_t used=0;
bool overflow=false;
void earlyReset() __attribute__((naked, section(".init3")));
void earlyReset() { MCUSR=0; wdt_disable(); }
void disableSignal(bool fault=false) {
  signalOutput.detach(); pinMode(12,INPUT); session.stop(fault);
}
void command(char *line) {
  char *context=nullptr, *verb=strtok_r(line," ",&context);
  if (!verb) return;
  if (!strcmp(verb,"STOP") || !strcmp(verb,"HELLO")) {
    disableSignal(); Serial.println(F("DONE 0 signal_disabled")); return;
  }
  if (!strcmp(verb,"PING")) {
    if (session.enabled) session.renewed=millis();
    Serial.println(F("PONG")); return;
  }
  char *argument=strtok_r(nullptr," ",&context);
  if (!strcmp(verb,"ENABLE") && argument && strlen(argument)==1 && argument[0]>='0' && argument[0]<='7') {
    char *review=strtok_r(nullptr," ",&context);
    uint8_t channel=argument[0]-'0';
    if (review && !strcmp(review,"POWER_SUPPORT_REVIEWED") && !strtok_r(nullptr," ",&context) &&
        DIRECT_COMMISSIONING_REVIEWED && session.enable(channel,DirectJoints[channel],true,millis())) {
      signalOutput.writeMicroseconds(session.current);
      signalOutput.attach(12); Serial.println(F("DONE 0 enabled_one")); return;
    }
  } else if (!strcmp(verb,"STEP") && argument && strlen(argument)<=3 &&
             strspn(argument,"-0123456789")==strlen(argument) &&
             argument[0]!='\0' && !strtok_r(nullptr," ",&context)) {
    char *end=nullptr;
    long offset=strtol(argument,&end,10);
    if (*end==0 && session.enabled && offset>=-25 && offset<=25 &&
        session.move(offset,DirectJoints[session.channel],millis())) {
      signalOutput.writeMicroseconds(session.current); Serial.println(F("DONE 0 step")); return;
    }
  }
  disableSignal(true); Serial.println(F("ERR 0 commissioning_inhibited"));
}
void setup() {
  pinMode(12,INPUT); Serial.begin(115200); disableSignal();
  Serial.println(F("READY Quadruped107Calibration 1")); wdt_enable(WDTO_1S);
}
void loop() {
  wdt_reset();
  if (!session.tick(millis())) disableSignal();
  uint8_t budget=32;
  while (Serial.available() && budget--) {
    char c=Serial.read();
    if (c=='\r') continue;
    if (c=='\n') {
      input[used]=0; used=0;
      if (overflow) { overflow=false; disableSignal(true); Serial.println(F("ERR 0 overflow")); }
      else command(input);
    } else if (!overflow) {
      if (used<63) input[used++]=c; else { used=0; overflow=true; disableSignal(true); }
    }
  }
}
