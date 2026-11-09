#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

constexpr uint8_t Pca9685Address = 0x40;
constexpr uint8_t ServoFrequencyHz = 50;
constexpr uint8_t FirstServoChannel = 0;
constexpr uint8_t LastServoChannel = 7;
constexpr uint16_t SafePulseMin = 50;
constexpr uint16_t SafePulseMax = 600;
constexpr uint16_t SmoothStepPulse = 5;
constexpr uint16_t SmoothStepDelayMs = 15;
constexpr uint16_t InitialArmsStepDelayMs = 22;
constexpr uint16_t MotionStageDelayMs = 500;
constexpr uint16_t GreetingWavePauseMs = 120;
constexpr uint8_t GreetingWaveCycles = 3;
constexpr uint16_t TailWagPauseMs = 120;
constexpr uint8_t TailWagCycles = 4;
constexpr uint16_t GaitStepDelayMs = 5;
constexpr uint16_t GaitFramePauseMs = 20;

constexpr uint8_t ChannelShoulderFL = 0;
constexpr uint8_t ChannelLegFL = 1;
constexpr uint8_t ChannelShoulderFR = 2;
constexpr uint8_t ChannelLegFR = 3;
constexpr uint8_t ChannelShoulderBL = 4;
constexpr uint8_t ChannelLegBL = 5;
constexpr uint8_t ChannelShoulderBR = 6;
constexpr uint8_t ChannelLegBR = 7;

struct ServoTarget {
  uint8_t channel;
  uint16_t pulse;
};

//Initial

const ServoTarget InitialShoulders[] = {
  {ChannelShoulderFL, 175},
  {ChannelShoulderFR, 440},
  {ChannelShoulderBL, 405},
  {ChannelShoulderBR, 175},
};

const ServoTarget InitialLegs[] = {
  {ChannelLegFL, 513},
  {ChannelLegFR, 90},
  {ChannelLegBL, 75},
  {ChannelLegBR, 525},
};

//Stand

const ServoTarget StandShoulders[] = {
  {ChannelShoulderFL, 278},
  {ChannelShoulderFR, 328},
  {ChannelShoulderBL, 295},
  {ChannelShoulderBR, 283},
};

const ServoTarget StandLegs[] = {
  {ChannelLegFL, 110},
  {ChannelLegFR, 500},
  {ChannelLegBL, 495},
  {ChannelLegBR, 110},
};

//Greeting

const ServoTarget GreetingSupportLegs[] = {
  {ChannelLegFL, 430},
  {ChannelLegBR, 180},
};

const ServoTarget GreetingSupportShoulders[] = {
  {ChannelShoulderFR, 380},
};

const ServoTarget GreetingShoulderForward[] = {
  {ChannelShoulderFL, 235},
};

const ServoTarget GreetingShoulderBack[] = {
  {ChannelShoulderFL, 328},
};

const ServoTarget GreetingReturnFLToStand[] = {
  {ChannelLegFL, 110},
  {ChannelShoulderFL, 278},
};

const ServoTarget GreetingReturnBRToStand[] = {
  {ChannelLegBR, 110},
  {ChannelShoulderFR, 328},
};

//Tail Wag

const ServoTarget TailWagPose[] = {
  // Hombros delanteros en posición vertical.
  {ChannelShoulderFL, 175},
  {ChannelShoulderFR, 440},

  // Piernas delanteras aproximadamente a 90 grados.
  {ChannelLegFL, 312},
  {ChannelLegFR, 295},

  // Piernas traseras en posición de pie.
  {ChannelLegBL, 495},
  {ChannelLegBR, 110},
};

const ServoTarget TailWagSideA[] = {
  {ChannelShoulderBL, 240},
  {ChannelShoulderBR, 229},
};

const ServoTarget TailWagSideB[] = {
  {ChannelShoulderBL, 350},
  {ChannelShoulderBR, 336},
};

//Forward

const ServoTarget ForwardPrepare[] = {
  {ChannelLegFL, 110},
  {ChannelLegFR, 500},
  {ChannelLegBL, 495},
  {ChannelLegBR, 110},
};

const ServoTarget ForwardLiftA[] = {
  {ChannelLegFL, 200},
  {ChannelLegBR, 200},
};

const ServoTarget ForwardPlaceA[] = {
  {ChannelShoulderFL, 226},
  {ChannelShoulderBR, 336},
};

const ServoTarget ForwardPlantA[] = {
  {ChannelLegFL, 110},
  {ChannelLegBR, 110},
};

const ServoTarget ForwardPushA[] = {
  {ChannelShoulderFL, 329},
  {ChannelShoulderBR, 229},
};

const ServoTarget ForwardLiftB[] = {
  {ChannelLegFR, 410},
  {ChannelLegBL, 410},
};

const ServoTarget ForwardPlaceB[] = {
  {ChannelShoulderFR, 384},
  {ChannelShoulderBL, 240},
};

const ServoTarget ForwardPlantB[] = {
  {ChannelLegFR, 500},
  {ChannelLegBL, 495},
};

const ServoTarget ForwardPushB[] = {
  {ChannelShoulderFR, 271},
  {ChannelShoulderBL, 350},
};

//Backward

const ServoTarget BackwardPlaceA[] = {
  {ChannelShoulderFL, 329},
  {ChannelShoulderBR, 229},
};

const ServoTarget BackwardPushA[] = {
  {ChannelShoulderFL, 226},
  {ChannelShoulderBR, 336},
};

const ServoTarget BackwardPlaceB[] = {
  {ChannelShoulderFR, 271},
  {ChannelShoulderBL, 350},
};

const ServoTarget BackwardPushB[] = {
  {ChannelShoulderFR, 384},
  {ChannelShoulderBL, 240},
};

//Left

const ServoTarget TurnLeftPlaceA[] = {
  {ChannelShoulderFL, 329},
  {ChannelShoulderBR, 336},
};

const ServoTarget TurnLeftPushA[] = {
  {ChannelShoulderFL, 226},
  {ChannelShoulderBR, 229},
};

const ServoTarget TurnLeftPlaceB[] = {
  {ChannelShoulderFR, 384},
  {ChannelShoulderBL, 350},
};

const ServoTarget TurnLeftPushB[] = {
  {ChannelShoulderFR, 271},
  {ChannelShoulderBL, 240},
};

//Right

const ServoTarget TurnRightPlaceA[] = {
  {ChannelShoulderFL, 226},
  {ChannelShoulderBR, 229},
};

const ServoTarget TurnRightPushA[] = {
  {ChannelShoulderFL, 329},
  {ChannelShoulderBR, 336},
};

const ServoTarget TurnRightPlaceB[] = {
  {ChannelShoulderFR, 271},
  {ChannelShoulderBL, 240},
};

const ServoTarget TurnRightPushB[] = {
  {ChannelShoulderFR, 384},
  {ChannelShoulderBL, 350},
};

//

extern bool armed;
extern bool abortMotion;
void cooperativeDelay(uint16_t milliseconds);

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(Pca9685Address);
uint16_t currentPulses[LastServoChannel + 1] = {300, 300, 300, 300, 300, 300, 300, 300};

uint16_t clampPulse(int pulse) {
  if (pulse < SafePulseMin) {
    return SafePulseMin;
  }
  if (pulse > SafePulseMax) {
    return SafePulseMax;
  }
  return static_cast<uint16_t>(pulse);
}

void writeServoPulse(uint8_t channel, uint16_t pulse) {
  if (!armed || abortMotion) return;
  uint16_t safePulse = clampPulse(pulse);
  pwm.setPWM(channel, 0, safePulse);
  currentPulses[channel] = safePulse;
}

uint16_t stepPulseToward(uint16_t currentPulse, uint16_t targetPulse) {
  if (currentPulse < targetPulse) {
    uint16_t nextPulse = currentPulse + SmoothStepPulse;
    return nextPulse > targetPulse ? targetPulse : nextPulse;
  }

  int nextPulse = static_cast<int>(currentPulse) - SmoothStepPulse;
  return nextPulse < targetPulse ? targetPulse : static_cast<uint16_t>(nextPulse);
}

void moveTargetsSmooth(const ServoTarget targets[], size_t targetCount, uint16_t stepDelayMs = SmoothStepDelayMs) {
  bool allAtTarget = false;

  while (!allAtTarget) {
    if (!armed || abortMotion) return;
    allAtTarget = true;

    for (size_t index = 0; index < targetCount; index++) {
      uint8_t channel = targets[index].channel;
      uint16_t safeTarget = clampPulse(targets[index].pulse);
      uint16_t currentPulse = currentPulses[channel];

      if (currentPulse != safeTarget) {
        writeServoPulse(channel, stepPulseToward(currentPulse, safeTarget));
        allAtTarget = false;
      }
    }

    if (!allAtTarget) {
      cooperativeDelay(stepDelayMs);
    }
  }
}

void moveInitial() {
  moveTargetsSmooth(InitialLegs, sizeof(InitialLegs) / sizeof(InitialLegs[0]), InitialArmsStepDelayMs);
  cooperativeDelay(MotionStageDelayMs);
  moveTargetsSmooth(InitialShoulders, sizeof(InitialShoulders) / sizeof(InitialShoulders[0]));
}

void moveStand() {
  moveTargetsSmooth(StandShoulders, sizeof(StandShoulders) / sizeof(StandShoulders[0]));
  cooperativeDelay(MotionStageDelayMs);
  moveTargetsSmooth(StandLegs, sizeof(StandLegs) / sizeof(StandLegs[0]));
}

void moveGreeting() {
  moveStand();
  cooperativeDelay(MotionStageDelayMs);
  moveTargetsSmooth(GreetingSupportShoulders, sizeof(GreetingSupportShoulders) / sizeof(GreetingSupportShoulders[0]));
  cooperativeDelay(MotionStageDelayMs);
  moveTargetsSmooth(GreetingSupportLegs, sizeof(GreetingSupportLegs) / sizeof(GreetingSupportLegs[0]));
  cooperativeDelay(MotionStageDelayMs);

  for (uint8_t cycle = 0; cycle < GreetingWaveCycles; cycle++) {
    moveTargetsSmooth(GreetingShoulderForward, sizeof(GreetingShoulderForward) / sizeof(GreetingShoulderForward[0]));
    cooperativeDelay(GreetingWavePauseMs);
    moveTargetsSmooth(GreetingShoulderBack, sizeof(GreetingShoulderBack) / sizeof(GreetingShoulderBack[0]));
    cooperativeDelay(GreetingWavePauseMs);
  }

  moveTargetsSmooth(GreetingReturnFLToStand, sizeof(GreetingReturnFLToStand) / sizeof(GreetingReturnFLToStand[0]));
  cooperativeDelay(MotionStageDelayMs);
  moveTargetsSmooth(GreetingReturnBRToStand, sizeof(GreetingReturnBRToStand) / sizeof(GreetingReturnBRToStand[0]));
}

void moveTailWag() {
  // Comienza desde una posición estable.
  moveStand();
  cooperativeDelay(MotionStageDelayMs);

  // Coloca la parte delantera y las piernas traseras.
  moveTargetsSmooth(
    TailWagPose,
    sizeof(TailWagPose) / sizeof(TailWagPose[0])
  );
  cooperativeDelay(MotionStageDelayMs);

  // Mueve los hombros traseros de lado a lado.
  for (uint8_t cycle = 0; cycle < TailWagCycles; cycle++) {
    moveTargetsSmooth(
      TailWagSideA,
      sizeof(TailWagSideA) / sizeof(TailWagSideA[0])
    );
    cooperativeDelay(TailWagPauseMs);

    moveTargetsSmooth(
      TailWagSideB,
      sizeof(TailWagSideB) / sizeof(TailWagSideB[0])
    );
    cooperativeDelay(TailWagPauseMs);
  }

  // Regresa a la posición de pie.
  moveStand();
}

void moveGaitStep(
  const ServoTarget placeA[],
  const ServoTarget pushA[],
  const ServoTarget placeB[],
  const ServoTarget pushB[]
) {
  moveTargetsSmooth(ForwardPrepare, sizeof(ForwardPrepare) / sizeof(ForwardPrepare[0]), GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);

  moveTargetsSmooth(ForwardLiftA, sizeof(ForwardLiftA) / sizeof(ForwardLiftA[0]), GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
  moveTargetsSmooth(placeA, 2, GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
  moveTargetsSmooth(ForwardPlantA, sizeof(ForwardPlantA) / sizeof(ForwardPlantA[0]), GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
  moveTargetsSmooth(pushA, 2, GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);

  moveTargetsSmooth(ForwardLiftB, sizeof(ForwardLiftB) / sizeof(ForwardLiftB[0]), GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
  moveTargetsSmooth(placeB, 2, GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
  moveTargetsSmooth(ForwardPlantB, sizeof(ForwardPlantB) / sizeof(ForwardPlantB[0]), GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
  moveTargetsSmooth(pushB, 2, GaitStepDelayMs);
  cooperativeDelay(GaitFramePauseMs);
}

void moveForwardStep() {
  moveGaitStep(ForwardPlaceA, ForwardPushA, ForwardPlaceB, ForwardPushB);
}

void moveBackwardStep() {
  moveGaitStep(BackwardPlaceA, BackwardPushA, BackwardPlaceB, BackwardPushB);
}

void moveTurnLeftStep() {
  moveGaitStep(TurnLeftPlaceA, TurnLeftPushA, TurnLeftPlaceB, TurnLeftPushB);
}

void moveTurnRightStep() {
  moveGaitStep(TurnRightPlaceA, TurnRightPushA, TurnRightPlaceB, TurnRightPushB);
}

