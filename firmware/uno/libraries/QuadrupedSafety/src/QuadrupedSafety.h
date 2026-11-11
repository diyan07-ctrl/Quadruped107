#pragma once
#include <stdint.h>

// Values are deliberately unknown. Historical gait ticks are not mechanical limits.
struct JointQualification {
  uint16_t minimum, neutral, maximum, unitsPerSecond;
  int8_t direction;
  bool qualified;
  bool valid() const {
    return qualified && minimum>0 && minimum<neutral && neutral<maximum &&
           unitsPerSecond>0 && (direction==1 || direction==-1);
  }
  bool target(int16_t offset, uint16_t &result) const {
    if (!valid()) return false;
    int32_t value=int32_t(neutral)+int32_t(direction)*offset;
    if (value<minimum || value>maximum) return false;
    result=value; return true;
  }
  bool step(uint16_t previous, uint16_t next, uint32_t elapsedMs) const {
    if (!valid() || previous<minimum || previous>maximum || next<minimum || next>maximum || elapsedMs>300)
      return false;
    uint16_t change=previous>next ? previous-next : next-previous;
    return uint32_t(change)*1000UL<=uint32_t(unitsPerSecond)*elapsedMs;
  }
};
// Production units are PCA ticks; separate direct-servo units are microseconds.
const JointQualification ProductionJoints[8]={};
inline bool productionQualified() {
  for (uint8_t i=0;i<8;++i) if (!ProductionJoints[i].valid()) return false;
  return true;
}

struct CalibrationSession {
  bool enabled=false, latched=false;
  uint8_t channel=255;
  uint16_t current=0;
  uint32_t began=0, renewed=0, moved=0;
  void stop(bool fault=false) { enabled=false; channel=255; latched|=fault; }
  bool enable(uint8_t selected, const JointQualification &joint, bool prerequisites, uint32_t now) {
    if (enabled || latched || selected>=8 || !prerequisites || !joint.valid()) return false;
    channel=selected; current=joint.neutral; began=renewed=moved=now; enabled=true; return true;
  }
  bool tick(uint32_t now) {
    if (enabled && (uint32_t(now-began)>=5000 || uint32_t(now-renewed)>500)) stop(true);
    return enabled;
  }
  bool move(int16_t offset, const JointQualification &joint, uint32_t now) {
    if (!tick(now) || offset < -25 || offset > 25) return false;
    uint16_t target;
    if (!joint.target(offset,target) || !joint.step(current,target,now-moved)) return false;
    uint16_t change=current>target ? current-target : target-current;
    if (change>10) return false;
    current=target; moved=now; return true;
  }
};
