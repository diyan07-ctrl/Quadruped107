# Virtual-actuator deployment

> Historical experimental development record. ENR107 submission-phase development has concluded; further development is on hold. See [academic closure status](../PROJECT_STATUS.md) for the current scope. Pin assignments, power options and session-specific results below describe their original development context, not verified final academic wiring.

This branch deliberately inhibits physical ARM. Keep the Uno disconnected, all servos unpowered and the suspected damaged PCA9685 disconnected. No deployment command uploads firmware or switches power.

On the Pi, review [software installation](../docs/SOFTWARE.md), then run `sh deploy/install-virtual-pi.sh` from the checkout. It creates a separate environment and does not change systemd, SSH, Telegram or existing services. It requires installed OS OpenCV/NumPy; the script prints the apt command if absent. No sudo commands execute automatically.

Start the laptop simulator first, then `sh deploy/run-virtual-pi.sh LAPTOP_PRIVATE_IP`. Open the Pi's current LAN address on port 7000. An explicit browser enable and mode selection are required. Avoid public networking and port forwarding.

The inherited systemd template remains a future physical-deployment reference. Do not install it for this assignment. Foreground startup is intentional: inspect diagnostics and STOP before ending processes. See [simulation](../simulation/README.md) for Windows, CI, restart and acceptance procedures.
