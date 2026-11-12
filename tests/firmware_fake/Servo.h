#pragma once
class Servo {
public:
  bool attached=false;
  unsigned writes=0;
  void attach(int) { attached=true; }
  void detach() { attached=false; }
  void writeMicroseconds(int) { ++writes; }
};
