# Development standards

Use Python 3.11+, Arduino C++, and plain browser JavaScript. Follow the [software setup](docs/SOFTWARE.md). Work on a descriptive branch; keep commits focused and include relevant validation evidence in the PR. Do not force-push shared history or commit generated files, credentials, downloaded models, or local environment configuration.

Keep one owner per hardware interface and route motion through the scheduler. Preserve the documented protocol unless a compatibility change is justified and tested. Use monotonic timestamps for freshness. Avoid blocking sensor/vision work in safety paths and avoid unbounded queues. Make faults visible and reconnect disarmed.

Keep existing code style when making small changes. New Python uses clear names, four-space indentation and explicit imports; firmware avoids dynamic allocation in control paths. New safety behavior needs failure-path tests, not only happy-path assertions. Check asset paths from both checkout and installed package. Preserve source and third-party notices.

Before a commit run the checks in [VALIDATION](docs/VALIDATION.md), including git diff --check. If local tools are unavailable, record exactly which checks did not run and require CI evidence before declaring validation passed. Hardware changes require proposed/verified labels, measured evidence and updated safety notes. No remote CI or simulation result substitutes for hardware qualification.

Keep detailed technical facts in docs rather than repeating them across READMEs. Separate implemented features from future requirements. Changes to pulse tables must include joint-specific calibration context; do not replace functioning components for style alone.
