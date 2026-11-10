"""Build-only virtual Uno variant in ignored build/. Never uploads or probes hardware."""
import argparse
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]


def generate(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    source=ROOT/"firmware/uno/sketch"
    header=(source/"motion.h").read_text(encoding="utf-8")
    stub="""class Adafruit_PWMServoDriver {
public:
  uint16_t ticks[8] = {4096,4096,4096,4096,4096,4096,4096,4096};
  explicit Adafruit_PWMServoDriver(uint8_t) {}
  bool begin() { return true; } // Explicit virtual build, never used in production.
  void setPWMFreq(uint8_t) {}
  void setPWM(uint8_t channel, uint16_t, uint16_t off) { if (channel < 8) ticks[channel] = off; }
};
"""
    header=header.replace('#include <Wire.h>','').replace('#include <Adafruit_PWMServoDriver.h>',stub)
    sketch=(source/"sketch.ino").read_text(encoding="utf-8")
    sketch=sketch.replace("Quadruped107 1","Quadruped107Virtual 1")
    sketch=sketch.replace("digitalWrite(","virtualDigitalWrite(").replace("pinMode(","virtualPinMode(")
    sketch=sketch.replace("  Wire.begin();","")
    sketch=re.sub(r"#if defined\(WIRE_HAS_TIMEOUT\).*?#endif","",sketch,flags=re.S)
    helpers="""
void virtualDigitalWrite(uint8_t, uint8_t) {}
void virtualPinMode(uint8_t, uint8_t) {}
void emitVirtualTrace() {
  static unsigned long previous = 0;
  if (millis() - previous < 50) return;
  previous = millis();
  char buffer[64];
  int length = snprintf(buffer, sizeof(buffer), "TRACE %u %u %u %u %u %u %u %u\\n",
      pwm.ticks[0], pwm.ticks[1], pwm.ticks[2], pwm.ticks[3],
      pwm.ticks[4], pwm.ticks[5], pwm.ticks[6], pwm.ticks[7]);
  if (length > 0 && length < int(sizeof(buffer)) && Serial.availableForWrite() >= length)
    Serial.write(reinterpret_cast<const uint8_t *>(buffer), length);
}
"""
    sketch=sketch.replace('#include <string.h>','#include <string.h>\n#include <stdio.h>\n'+helpers)
    sketch=sketch.replace("void serviceControl() {","void serviceControl() {\n  emitVirtualTrace();")
    if "Wire." in sketch or "digitalWrite(" in sketch or "<Adafruit_PWMServoDriver.h>" in header:
        raise ValueError("Virtual generation retained a physical driver operation")
    (output/"motion.h").write_text(header,encoding="utf-8")
    (output/"sketch.ino").write_text(sketch,encoding="utf-8")
    shutil.copyfile(source/"sketch.yaml",output/"sketch.yaml")
    return output


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"build/virtual/sketch")
    args=parser.parse_args()
    print("VIRTUAL BUILD ONLY, no upload: "+str(generate(args.output)))
