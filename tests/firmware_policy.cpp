#include "Arduino.h"
#include "../firmware/uno/sensor_only/acquisition.h"
#include <QuadrupedSafety.h>
int main() {
  RangeAcquisition range;
  assert(!range.valid && range.fault);
  range.start(200000); assert(!range.tick(200009)); assert(range.tick(200010));
  range.edge(false,201000); range.edge(true,206000);
  assert(range.valid && range.mm==1000 && range.acquired==206000);
  range.start(400000); range.tick(400010); range.tick(460000);
  assert(!range.valid && range.fault==2);
  range.start(600000); range.tick(600010); range.edge(false,601000); range.edge(true,651000);
  assert(!range.valid); // Explicit module invalid width.
  range.start(800000); range.tick(800010); range.edge(false,801000); range.edge(true,801050);
  assert(!range.valid); // Below configured 20 mm.
  range.start(0xfffffff0); assert(range.tick(0xfffffffa));
  range.edge(false,0xfffffffb); range.edge(true,4995);
  assert(range.valid && range.mm==1000); // uint32 microsecond wrap.
  TouchInput touch;
  touch.scan(true,0); touch.scan(true,25); assert(!touch.ready && touch.pressed);
  touch.scan(false,30); touch.scan(false,49); assert(touch.pressed);
  touch.scan(false,50); assert(!touch.pressed && touch.ready);
  touch.scan(true,60); touch.scan(false,65); touch.scan(true,70); touch.scan(true,90);
  assert(touch.pressed && !touch.stuck);
  touch.scan(true,2090); assert(touch.stuck && !touch.ready);
  touch.scan(false,2100); touch.scan(false,2120); assert(!touch.stuck && touch.ready);
  assert(!productionQualified());
  JointQualification unknown={}; uint16_t target;
  assert(!unknown.target(0,target));
  // Synthetic fixture only; never exported to firmware profiles.
  JointQualification qualified={1400,1500,1600,100,-1,true};
  assert(qualified.target(20,target) && target==1480);
  assert(!qualified.target(101,target));
  CalibrationSession session;
  assert(!session.enable(0,unknown,true,0));
  assert(!session.enable(0,qualified,false,0));
  assert(!session.enable(8,qualified,true,0));
  assert(session.enable(0,qualified,true,0));
  assert(!session.enable(1,qualified,true,0));
  assert(!session.move(26,qualified,100));
  assert(!session.move(10,qualified,10));
  assert(session.move(10,qualified,100) && session.current==1490);
  session.stop(); assert(!session.enabled);
  assert(session.enable(1,qualified,true,200));
  assert(!session.tick(701) && session.latched);
  assert(!session.enable(1,qualified,true,702));
  CalibrationSession deadline;
  assert(deadline.enable(0,qualified,true,0));
  deadline.renewed=4900; assert(!deadline.tick(5000));
  std::cout << "driver/policy: timeout, invalid, recovery, wrap, debounce, stuck, uncalibrated, direction, limits, rate, lease, STOP PASS\n";
}
