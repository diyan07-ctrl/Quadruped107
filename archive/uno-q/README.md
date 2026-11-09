# Historical UNO Q applications

These supplied Arduino App Lab / Arduino Bridge applications are archived for provenance, calibration workflow reference, and recovery of earlier behavior. They are excluded from Pi dependencies, CI execution and deployment. Do not run them against the active Uno R3 firmware or flash their sketches to Uno R3.

- [Control station](control-station/README.md): deprecated Bridge-based control and vision implementation, with differing historical calibration values.
- [Servo calibrator](servo-calibrator/README.md): Bridge-based calibration UI and JSON export workflow.

They retain original source and dependency metadata; those dependencies and incomplete board profiles are not maintained. No generated calibration_values.json was present in the tracked repository. The preserved [spreadsheets](../../hardware/calibration/) and active [Pi calibration API](../../software/pi/README.md) are separate references. Historical pulse limits are not physically verified safe endpoints.

Original READMEs describe their historical environment; their instructions are not current setup instructions. Missing placeholder screenshots were removed from the archived calibrator README during Phase 0 link cleanup.
