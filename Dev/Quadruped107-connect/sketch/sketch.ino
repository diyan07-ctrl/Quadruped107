// Quadruped107 Pi 4 / Uno R3 port, 2026-11-04. GPL-3.0.
#include "motion.h"
#include <stdlib.h>
#include <string.h>

constexpr unsigned long WatchdogMs = 1500;
constexpr uint8_t OutputEnablePin = 8;  // PCA9685 OE, with external 10k pull-up to 5V
bool armed = false;
bool abortMotion = true;
bool motionActive = false;
bool driverReady = false;
unsigned long lastPing = 0;
char lineBuffer[64];
uint8_t lineLength = 0;
bool overflowed = false;

void outputsOff() {
  digitalWrite(OutputEnablePin, HIGH);
  armed = false;
  abortMotion = true;
  for (uint8_t channel = 0; channel <= LastServoChannel; ++channel)
    pwm.setPWM(channel, 0, 4096);
}

void reply(const __FlashStringHelper *kind, const char *id, const char *detail) {
  Serial.print(kind); Serial.print(' '); Serial.print(id);
  Serial.print(' '); Serial.println(detail);
}

bool runMotion(const char *name) {
  if (!strcmp(name, "initial")) moveInitial();
  else if (!strcmp(name, "stand")) moveStand();
  else if (!strcmp(name, "greeting")) moveGreeting();
  else if (!strcmp(name, "tail_wag")) moveTailWag();
  else if (!strcmp(name, "forward")) moveForwardStep();
  else if (!strcmp(name, "backward")) moveBackwardStep();
  else if (!strcmp(name, "turn_left")) moveTurnLeftStep();
  else if (!strcmp(name, "turn_right")) moveTurnRightStep();
  else return false;
  return true;
}

void handleLine(char *line) {
  char *context = nullptr;
  char *command = strtok_r(line, " ", &context);
  if (!command) return;
  if (!strcmp(command, "HELLO")) {
    outputsOff(); Serial.println(F("READY Quadruped107 1")); return;
  }
  if (!strcmp(command, "PING")) {
    lastPing = millis(); Serial.println(F("PONG")); return;
  }
  char *id = strtok_r(nullptr, " ", &context);
  if (!id || strspn(id, "0123456789") != strlen(id)) {
    Serial.println(F("ERR 0 invalid_id")); return;
  }
  if (!strcmp(command, "STOP")) {
    outputsOff(); reply(F("DONE"), id, "stopped"); return;
  }
  if (!driverReady) { reply(F("ERR"), id, "pca9685_missing"); return; }
  if (!strcmp(command, "ARM")) {
    if (motionActive) { reply(F("ERR"), id, "busy"); return; }
    abortMotion = false; armed = true; lastPing = millis();
    digitalWrite(OutputEnablePin, LOW);
    reply(F("DONE"), id, "armed"); return;
  }
  if (!armed || abortMotion) { reply(F("ERR"), id, "disarmed"); return; }
  if (motionActive) { reply(F("ERR"), id, "busy"); return; }
  if (!strcmp(command, "MOVE")) {
    char *name = strtok_r(nullptr, " ", &context);
    if (!name || strtok_r(nullptr, " ", &context)) { reply(F("ERR"), id, "invalid_motion"); return; }
    // Serial input is serviced during a gait: copy tokens before re-entering parser.
    char savedId[12]; char savedName[20];
    if (strlen(id) >= sizeof(savedId) || strlen(name) >= sizeof(savedName)) {
      reply(F("ERR"), id, "argument_too_long"); return;
    }
    strcpy(savedId, id); strcpy(savedName, name);
    reply(F("ACCEPT"), savedId, savedName);
    motionActive = true;
    bool known = runMotion(savedName);
    motionActive = false;
    reply(known && !abortMotion ? F("DONE") : F("ERR"), savedId,
          !known ? "unknown_motion" : (abortMotion ? "stopped" : savedName));
    return;
  }
  if (!strcmp(command, "SERVO")) {
    char *channelText = strtok_r(nullptr, " ", &context);
    char *pulseText = strtok_r(nullptr, " ", &context);
    if (!channelText || !pulseText || strtok_r(nullptr, " ", &context) ||
        strspn(channelText, "0123456789") != strlen(channelText) ||
        strspn(pulseText, "0123456789") != strlen(pulseText) ||
        strlen(channelText) > 1 || strlen(pulseText) > 3) {
      reply(F("ERR"), id, "invalid_servo"); return;
    }
    int channel = atoi(channelText), pulse = atoi(pulseText);
    if (channel > LastServoChannel || pulse < SafePulseMin || pulse > SafePulseMax) {
      reply(F("ERR"), id, "servo_out_of_range"); return;
    }
    writeServoPulse(channel, pulse); reply(F("DONE"), id, "servo"); return;
  }
  reply(F("ERR"), id, "unknown_command");
}

void serviceControl() {
  if (armed && millis() - lastPing > WatchdogMs) {
    outputsOff(); Serial.println(F("FAULT watchdog"));
  }
  uint8_t budget = 64;
  while (Serial.available() && budget--) {
    char character = Serial.read();
    if (character == '\r') continue;
    if (character == '\n') {
      lineBuffer[lineLength] = '\0'; lineLength = 0;
      if (overflowed) {
        overflowed = false; Serial.println(F("ERR 0 line_too_long"));
      } else handleLine(lineBuffer);
    } else if (!overflowed) {
      if (lineLength < sizeof(lineBuffer) - 1) lineBuffer[lineLength++] = character;
      else { overflowed = true; lineLength = 0; }
    }
  }
}

void cooperativeDelay(uint16_t milliseconds) {
  unsigned long start = millis();
  do {
    serviceControl();
    if (abortMotion || !armed) return;
    delay(1);
  } while (millis() - start < milliseconds);
}

void setup() {
  digitalWrite(OutputEnablePin, HIGH);
  pinMode(OutputEnablePin, OUTPUT);
  Serial.begin(115200);
  Wire.begin();
#if defined(WIRE_HAS_TIMEOUT)
  Wire.setWireTimeout(25000, true);
#endif
  driverReady = pwm.begin();
  if (driverReady) { pwm.setPWMFreq(ServoFrequencyHz); outputsOff(); }
  Serial.println(F("READY Quadruped107 1"));
  if (!driverReady) Serial.println(F("FAULT pca9685_missing"));
}

void loop() { serviceControl(); }
