#pragma once
// Set only after identifying the actual module and verifying PWM trigger mode.
#ifndef URM37_PROFILE
#define URM37_PROFILE 0
#endif
#if URM37_PROFILE != 0 && URM37_PROFILE != 1
#error Unsupported URM37 revision/interface profile
#endif
// Bits select physically verified, connected digital touch boards (2-5 for use).
#ifndef TOUCH_ENABLED_MASK
#define TOUCH_ENABLED_MASK 0
#endif
#ifndef TOUCH_ACTIVE_LOW_MASK
#define TOUCH_ACTIVE_LOW_MASK 0
#endif
static_assert(TOUCH_ENABLED_MASK==0 || TOUCH_ENABLED_MASK==3 || TOUCH_ENABLED_MASK==7 ||
              TOUCH_ENABLED_MASK==15 || TOUCH_ENABLED_MASK==31, "Select 2-5 contiguous touches");
static_assert((TOUCH_ACTIVE_LOW_MASK & ~TOUCH_ENABLED_MASK)==0, "Polarity for absent touch");
