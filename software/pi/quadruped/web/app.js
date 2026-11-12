const state = {
  mjpegMode: false,
  cameraTimer: null,
  stateTimer: null,
  commandId: 0,
  latestAcceptedGeneration: 0,
  appMode: "manual",
  desiredMotion: "stand",
  currentMotion: "none",
  busy: false,
  enabled: false,
  heartbeatPending: false,
  visionRevision: null,
  historySequence: -1,
  activeInputs: new Map(),
  activeMovementMode: null,
};

const elements = {
  connectionStatus: document.querySelector("#connectionStatus"),
  appMode: document.querySelector("#appMode"),
  currentMotion: document.querySelector("#currentMotion"),
  desiredMotion: document.querySelector("#desiredMotion"),
  currentMotionReadout: document.querySelector("#currentMotionReadout"),
  lastResult: document.querySelector("#lastResult"),
  cameraStatus: document.querySelector("#cameraStatus"),
  cameraReadout: document.querySelector("#cameraReadout"),
  cameraStage: document.querySelector("#cameraStage"),
  cameraBackdrop: document.querySelector("#cameraBackdrop"),
  cameraImage: document.querySelector("#cameraImage"),
  cameraFallback: document.querySelector("#cameraFallback"),
  toggleStreamButton: document.querySelector("#toggleStreamButton"),
  focusModeButton: document.querySelector("#focusModeButton"),
  focusButtonLabel: document.querySelector("#focusButtonLabel"),
  exitFocusButton: document.querySelector("#exitFocusButton"),
  hudConnection: document.querySelector("#hudConnection"),
  hudMode: document.querySelector("#hudMode"),
  hudMotion: document.querySelector("#hudMotion"),
  visionStatus: document.querySelector("#visionStatus"),
  appModeButtons: document.querySelectorAll("[data-app-mode]"),
  driveButtons: document.querySelectorAll("[data-drive-mode]"),
  poseButtons: document.querySelectorAll("[data-pose-mode]"),
  armButton: document.querySelector("#armButton"),
  stopButton: document.querySelector("#stopButton"),
};

const movementKeyToMode = {
  w: "forward",
  s: "backward",
  a: "turn_left",
  d: "turn_right",
};

const poseKeyToMode = {
  ArrowUp: "stand",
  ArrowDown: "initial",
  ArrowRight: "greeting",
  ArrowLeft: "tail_wag",
};

const reservedKeyBindings = {
  PageDown: "opencv",
  F4: "hand_gesture",
  " ": "manual",
};

const modeLabels = { hand_gesture: "hand gesture" };
let cameraAspectRatio = 4 / 3;

function sizeCameraFrame() {
  const stage = elements.cameraStage;
  const frame = stage?.querySelector(".camera-frame");
  if (!stage || !frame) return;
  const availableWidth = stage.clientWidth;
  const availableHeight = stage.clientHeight;
  if (!availableWidth || !availableHeight) return;

  let width = availableWidth;
  let height = width / cameraAspectRatio;
  if (height > availableHeight) {
    height = availableHeight;
    width = height * cameraAspectRatio;
  }
  const sideGap = Math.max(0, (availableWidth - width) / 2);
  frame.style.width = `${Math.max(1, Math.round(width))}px`;
  frame.style.height = `${Math.max(1, Math.round(height))}px`;
  stage.style.setProperty("--camera-aspect", String(cameraAspectRatio));
  document.body.style.setProperty("--camera-side-gap", `${sideGap}px`);
  document.body.style.setProperty("--side-control-key", `${Math.max(48, Math.min(110, (sideGap - 32) / 3))}px`);
  document.body.style.setProperty("--pose-rail-width", `${Math.max(150, Math.min(320, sideGap - 32))}px`);
  document.body.classList.toggle(
    "focus-side-rails",
    document.body.classList.contains("focus-mode") && availableWidth >= 1000 && sideGap >= 190,
  );
}

function updateCameraAspect() {
  const width = elements.cameraImage.naturalWidth;
  const height = elements.cameraImage.naturalHeight;
  if (width > 0 && height > 0) cameraAspectRatio = width / height;
  sizeCameraFrame();
}

function apiUrl(path) {
  return new URL(path, window.location.origin);
}

async function fetchJson(path, options = {}, behavior = {}) {
  const response = await fetch(apiUrl(path), {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let body = null;
  try {
    body = await response.json();
  } catch (_error) {
    body = null;
  }

  if (!response.ok || (body?.ok === false && !behavior.allowUnavailable)) {
    const detail = body?.error ? `: ${body.error}` : "";
    const error = new Error(`HTTP ${response.status}${detail}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function setConnectionStatus(text, className) {
  elements.connectionStatus.innerHTML = `<i></i>${text}`;
  elements.connectionStatus.className = `status-pill ${className}`;
  elements.hudConnection.innerHTML = `<i></i>${text}`;
}

function setCameraStatus(text) {
  const value = text || "Camera status unknown";
  elements.cameraStatus.textContent = value;
  elements.cameraReadout.textContent = value;
}

function renderMotion() {
  const appModeLabel = modeLabels[state.appMode] || state.appMode;
  elements.appMode.textContent = `Mode: ${appModeLabel}`;
  elements.currentMotion.textContent = `Motion: ${state.currentMotion}`;
  elements.desiredMotion.textContent = state.desiredMotion;
  elements.currentMotionReadout.textContent = state.currentMotion;
  elements.hudMode.textContent = `Mode: ${appModeLabel}`;
  elements.hudMotion.textContent = `Motion: ${state.desiredMotion}`;

  elements.appModeButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.appMode === state.appMode);
  });
  elements.driveButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.driveMode === state.activeMovementMode);
  });
  elements.poseButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.poseMode === state.desiredMotion);
  });
}

function setResult(text) {
  elements.lastResult.textContent = text || "Ready";
}

function applyMotionState(motionState) {
  if (!motionState) return;
  state.appMode = motionState.appMode || state.appMode;
  state.desiredMotion = motionState.desiredMotion || state.desiredMotion;
  state.currentMotion = motionState.currentMotion || state.currentMotion;
  state.busy = Boolean(motionState.busy);
  state.latestAcceptedGeneration = motionState.generation || state.latestAcceptedGeneration;
  setResult(motionState.lastResult);
  renderMotion();
}

function formatBlueBallStatus(blueBall) {
  if (!blueBall) return "Idle";
  if (!blueBall.detected) return `${blueBall.action || "search"} → ${blueBall.motion || "hold"}`;
  const offset = Number(blueBall.offset || 0).toFixed(2);
  return `Detected · offset ${offset} → ${blueBall.motion}`;
}

function formatHandStatus(hand, fallback = "Reserved") {
  if (!hand) return fallback;
  if (!hand.detected) return `${hand.gesture || "none"} → ${hand.motion || "hold"}`;
  return `${hand.gesture} → ${hand.motion}`;
}

function updateVisionStatus(vision = {}) {
  if (state.appMode === "opencv") {
    elements.visionStatus.textContent = `${vision.targetColor === "yellow" ? "Yellow" : "Blue"}: ${formatBlueBallStatus(vision.blueBall)}`;
    return;
  }
  if (state.appMode === "hand_gesture") {
    elements.visionStatus.textContent = formatHandStatus(vision.hand, vision.handGesture || vision.mediapipe);
    return;
  }
  elements.visionStatus.textContent = "Reserved";
}

async function loadState() {
  try {
    const data = await fetchJson("/api/state");
    setCameraStatus(data.camera?.status);
    renderDiagnostics(data);
    renderDecisions(data);
    applyMotionState(data.motion);
    updateVisionStatus(data.vision);
    const targetButton = document.querySelector('[data-app-mode="opencv"]');
    if (targetButton) targetButton.textContent = `${data.vision?.targetColor === "yellow" ? "Yellow tennis-ball" : "Blue target"} tracking`;
    state.enabled = Boolean(data.motion?.enabled && data.link?.armed);
    if (!state.enabled) releaseAllMovement("disabled", false);
    elements.armButton.disabled = !data.simulation || !data.link?.connected || state.enabled;
    elements.armButton.textContent = data.simulation ? "Enable virtual actuators" : "Physical actuation inhibited";
    [...elements.driveButtons, ...elements.poseButtons, ...elements.appModeButtons].forEach((button) => {
      const mode = button.dataset.appMode;
      if (mode) button.hidden = !data.controlModes?.includes(mode) || (mode === "hand_gesture" && !data.features?.handGesture);
      button.disabled = !state.enabled || (mode && !data.controlModes?.includes(mode));
    });
    setConnectionStatus(data.simulation ? "Simulation" : (state.enabled ? "Enabled" : (data.link?.connected ? "Disabled" : "Uno disconnected")),
      state.enabled ? "status-success" : "status-warning");
  } catch (error) {
    setResult(`Connection failed: ${error.message}`);
    setConnectionStatus("Disconnected", "status-danger");
  }
}

async function setMode(mode, source = "ui") {
  if (!state.enabled) { setResult("Enable servos first"); return; }
  const commandId = ++state.commandId;
  setConnectionStatus("Sending", "status-warning");
  setResult(`set_mode("${mode}") from ${source}`);
  try {
    const data = await fetchJson("/api/mode", { method: "POST", body: JSON.stringify({ mode }) });
    if (commandId !== state.commandId && data.generation < state.latestAcceptedGeneration) return;
    applyMotionState(data.state);
    setConnectionStatus("Connected", "status-success");
  } catch (error) {
    setResult(error.message);
    setConnectionStatus(error.status ? "Request Error" : "Bridge Error", "status-danger");
  }
}

async function refreshCameraFrame() {
  if (state.mjpegMode) return;
  try {
    const data = await fetchJson("/api/camera-frame", {}, { allowUnavailable: true });
    if (!data) throw new Error("Camera endpoint returned an invalid response");
    setCameraStatus(data.status);
    if (!data.ok || !data.available) {
      elements.cameraFallback.classList.remove("hidden");
      return;
    }
    elements.cameraImage.src = `data:${data.mimeType};base64,${data.data}`;
    elements.cameraBackdrop.style.backgroundImage = `url("${elements.cameraImage.src}")`;
    elements.cameraFallback.classList.add("hidden");
  } catch (error) {
    setCameraStatus(`Refresh failed: ${error.message}`);
    elements.cameraFallback.classList.remove("hidden");
  }
}

function startCameraRefresh() {
  if (state.cameraTimer) window.clearInterval(state.cameraTimer);
  state.cameraTimer = window.setInterval(refreshCameraFrame, 250);
  refreshCameraFrame();
}

function startStateRefresh() {
  if (state.stateTimer) window.clearInterval(state.stateTimer);
  state.stateTimer = window.setInterval(loadState, 750);
}

function toggleStreamMode() {
  state.mjpegMode = !state.mjpegMode;
  if (state.mjpegMode) {
    elements.cameraImage.src = "/video-feed";
    elements.cameraFallback.classList.add("hidden");
    setCameraStatus("MJPEG stream");
    elements.toggleStreamButton.textContent = "Snapshots";
    return;
  }
  elements.toggleStreamButton.textContent = "MJPEG";
  startCameraRefresh();
}

function fullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement || null;
}

function requestAppFullscreen() {
  if (fullscreenElement()) return;
  const root = document.documentElement;
  try {
    const request = root.requestFullscreen
      ? root.requestFullscreen({ navigationUI: "hide" })
      : root.webkitRequestFullscreen?.();
    request?.catch?.(() => {});
  } catch (_error) {
    // Focus view still works when fullscreen is unavailable or blocked.
  }
}

function exitAppFullscreen() {
  if (!fullscreenElement()) return;
  try {
    const exit = document.exitFullscreen ? document.exitFullscreen() : document.webkitExitFullscreen?.();
    exit?.catch?.(() => {});
  } catch (_error) {
    // The browser may already be leaving fullscreen via Escape.
  }
}

function setFocusMode(enabled, manageFullscreen = true) {
  document.body.classList.toggle("focus-mode", enabled);
  elements.focusButtonLabel.textContent = enabled ? "Exit Fullscreen" : "Fullscreen";
  elements.focusModeButton.setAttribute("aria-label", enabled ? "Exit fullscreen" : "Enter fullscreen");
  window.requestAnimationFrame(sizeCameraFrame);
  if (!manageFullscreen) return;
  if (enabled) requestAppFullscreen();
  else exitAppFullscreen();
}

function toggleFocusMode() {
  setFocusMode(!document.body.classList.contains("focus-mode"));
}

function shouldIgnoreKeyboardEvent(event) {
  const tagName = event.target?.tagName?.toLowerCase();
  return tagName === "input" || tagName === "select" || tagName === "textarea";
}

function chooseActiveMovementMode() {
  const active = [...state.activeInputs.values()];
  if (!active.length) return null;
  active.sort((left, right) => right.time - left.time);
  return active[0].mode;
}

function updateMovementMode(source) {
  const nextMode = chooseActiveMovementMode();
  if (nextMode === state.activeMovementMode) return;
  state.activeMovementMode = nextMode;
  renderMotion();
  setMode(nextMode || "stand", source);
}

function activateMovement(token, mode, source) {
  if (!state.enabled) return;
  const previous = state.activeInputs.get(token);
  if (previous?.mode === mode) return;
  state.activeInputs.set(token, { mode, time: performance.now() });
  updateMovementMode(source);
}

function releaseMovement(token, source) {
  if (!state.activeInputs.delete(token)) return;
  updateMovementMode(source);
}

function releaseAllMovement(source = "safety-release", sendStand = true) {
  const wasMoving = state.activeInputs.size > 0 || state.activeMovementMode !== null;
  state.activeInputs.clear();
  state.activeMovementMode = null;
  renderMotion();
  if (wasMoving && sendStand) setMode("stand", source);
}

async function switchAppMode(mode, source) {
  const wasMoving = state.activeInputs.size > 0 || state.activeMovementMode !== null;
  releaseAllMovement("mode-change", false);
  if (wasMoving) await setMode("stand", "mode-change");
  await setMode(mode, source);
}

elements.appModeButtons.forEach((button) => {
  button.addEventListener("click", () => switchAppMode(button.dataset.appMode, "button"));
});

elements.poseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    releaseAllMovement("pose-button", false);
    setMode(button.dataset.poseMode, "button");
  });
});

elements.driveButtons.forEach((button) => {
  button.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.preventDefault();
    button.setPointerCapture?.(event.pointerId);
    activateMovement(`pointer:${event.pointerId}`, button.dataset.driveMode, "touch");
  });

  button.addEventListener("pointermove", (event) => {
    const token = `pointer:${event.pointerId}`;
    if (!state.activeInputs.has(token)) return;
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest?.("[data-drive-mode]");
    if (target) activateMovement(token, target.dataset.driveMode, "touch-slide");
  });

  const endPointer = (event) => {
    event.preventDefault();
    releaseMovement(`pointer:${event.pointerId}`, "touch-release");
  };
  button.addEventListener("pointerup", endPointer);
  button.addEventListener("pointercancel", endPointer);
  button.addEventListener("lostpointercapture", (event) => releaseMovement(`pointer:${event.pointerId}`, "capture-lost"));
  button.addEventListener("contextmenu", (event) => event.preventDefault());
});

window.addEventListener("keydown", (event) => {
  if (shouldIgnoreKeyboardEvent(event)) return;
  if (event.key.toLowerCase() === "x" && !event.repeat) { stopRobot(); return; }
  const poseMode = poseKeyToMode[event.key];
  if (poseMode && !event.repeat) {
    event.preventDefault();
    releaseAllMovement("keyboard-pose", false);
    setMode(poseMode, "keyboard");
    return;
  }
  if (event.key === "Escape" && !event.repeat) {
    event.preventDefault();
    toggleFocusMode();
    return;
  }
  const reservedMode = reservedKeyBindings[event.key] || reservedKeyBindings[event.key.toLowerCase()];
  if (reservedMode && !event.repeat) {
    event.preventDefault();
    switchAppMode(reservedMode, "keyboard");
    return;
  }
  const key = event.key.toLowerCase();
  if (movementKeyToMode[key]) {
    event.preventDefault();
    activateMovement(`key:${key}`, movementKeyToMode[key], "keyboard");
  }
});

window.addEventListener("keyup", (event) => {
  if (shouldIgnoreKeyboardEvent(event)) return;
  const key = event.key.toLowerCase();
  if (!movementKeyToMode[key]) return;
  event.preventDefault();
  releaseMovement(`key:${key}`, "keyboard");
});

window.addEventListener("blur", stopRobot);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopRobot();
});
window.addEventListener("pagehide", () => {
  navigator.sendBeacon("/api/stop", new Blob(["{}"], { type: "application/json" }));
});
document.addEventListener("fullscreenchange", () => {
  if (!fullscreenElement() && document.body.classList.contains("focus-mode")) {
    setFocusMode(false, false);
  }
});
document.addEventListener("webkitfullscreenchange", () => {
  if (!fullscreenElement() && document.body.classList.contains("focus-mode")) {
    setFocusMode(false, false);
  }
});

elements.toggleStreamButton.addEventListener("click", toggleStreamMode);
elements.focusModeButton.addEventListener("click", toggleFocusMode);
elements.exitFocusButton.addEventListener("click", () => setFocusMode(false));
elements.cameraImage.addEventListener("load", updateCameraAspect);
window.addEventListener("resize", sizeCameraFrame);
if ("ResizeObserver" in window) {
  new ResizeObserver(sizeCameraFrame).observe(elements.cameraStage);
}

async function stopRobot() {
  state.enabled = false;
  releaseAllMovement("stop", false);
  try { await fetchJson("/api/stop", { method: "POST", body: "{}" }); }
  catch (error) { setResult(`Stop request failed: ${error.message}`); }
  await loadState();
}

elements.armButton.addEventListener("click", async () => {
  releaseAllMovement("arm", false);
  try { await fetchJson("/api/arm", { method: "POST", body: "{}" }); }
  catch (error) { setResult(error.message); }
  await loadState();
});
elements.stopButton.addEventListener("click", stopRobot);
window.setInterval(async () => {
  if (document.hidden || state.heartbeatPending) return;
  state.heartbeatPending = true;
  try {
    await fetchJson("/api/heartbeat", { method: "POST",
      body: JSON.stringify({ motion: state.activeMovementMode }) });
  } catch (_error) { /* The server lease expires if contact is lost. */ }
  finally { state.heartbeatPending = false; }
}, 250);

loadState();
startStateRefresh();
startCameraRefresh();
window.requestAnimationFrame(sizeCameraFrame);

function renderDiagnostics(data) {
  const show = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
  const camera = data.camera || {};
  const vision = data.vision || {};
  const system = data.system || {};
  const link = data.link || {};
  const target = vision.blueBall || {};
  const physicalLink = data.sensorLink || {};
  const telemetry = physicalLink.telemetry || {};
  const range = data.sensors?.observations?.urm37;
  show('sensorSourceReadout', 'Sensor source: ' + (data.sensorSource || 'none') + ' / ' +
    (data.sensors?.virtual === false ? 'physical monitoring only' : 'virtual or unavailable'));
  show('physicalSensorReadout', (physicalLink.firmwareCapability || physicalLink.firmwareIdentity || 'no negotiated sensor firmware') + ' / ' +
    (physicalLink.connected ? 'USB connected' : 'USB unavailable') + ' / ' + (physicalLink.telemetryRate || 0) + ' Hz / URM37 ' +
    (range?.valid ? range.measurement.toFixed(3) + ' m' : 'INVALID / STALE') + ' / age ' +
    (range ? Math.round(range.age * 1000) + ' ms' : 'unknown') + ' / faults ' + (telemetry.faults ?? 'unknown') +
    ' / last valid acquisition ' + (telemetry.lastValidAcquisitionMonotonic ?? 'none') + ' / serial ' + (physicalLink.error || 'no reported error'));
  show('touchSensorReadout', 'Configured touches: ' + (data.sensors?.configuredTouchCount ?? 'unknown') +
    ' / profile ' + (data.sensors?.touchProfile || 'unknown') + ' / mapping ' + JSON.stringify(data.sensors?.touchMapping || []) +
    ' / states ' + JSON.stringify(data.sensors?.touches || {}) + ' / events ' + JSON.stringify(data.sensors?.events || []) +
    ' / virtual gesture ' + JSON.stringify(data.autonomy?.touchGesture || null));
  show('oledReadout', 'OLED: ' + (data.oled?.enabled ? (data.oled.connected ? data.oled.screen : 'disconnected') : 'disabled') +
    (data.oled?.error ? ' / ' + data.oled.error : ''));
  show('sensorInhibits', 'Physical actuation DISABLED / ' + (data.sensors?.safetyInhibits || []).join(' / '));
  show("backendDiagnostics", `${camera.backend || "unknown"} / ${camera.actualFps || 0} FPS${camera.lastError ? " / " + camera.lastError : ""}`);
  show("visionDiagnostics", `${vision.processingFps || 0} FPS / ${camera.frameAge == null ? "no frame" : Math.round(camera.frameAge * 1000) + " ms"}`);
  show("resourceDiagnostics", `${system.processCpuPercent ?? "?"}% / ${system.rssBytes == null ? "RAM unavailable" : (system.rssBytes / 1048576).toFixed(1) + " MiB"}`);
  show("behaviorDiagnostics", `${vision.behavior || "IDLE"} / ${target.detected ? "x error " + Number(target.offset).toFixed(2) + " / area " + target.area : "no target"}`);
  show("actuatorDiagnostics", `${link.kind || (data.simulation ? "unit stub" : "serial monitor")} / ${data.bridge ? (data.bridge.connected ? "simulator connected" : "simulator unavailable") : "local only"}`);
  show("safetyDiagnostics", data.motion?.enabled ? "VIRTUAL ENABLED — physical outputs prohibited" : (data.motion?.fault || "STOPPED"));
  const section = document.getElementById("virtualAutonomy");
  const touchMode = document.querySelector('[data-app-mode="interaction"]');
  if (touchMode) touchMode.textContent = data.sensorSource === 'physical_uno' ? 'Touch gestures (virtual placeholders)' : 'Interactions';
  if (section) section.hidden = !data.features?.virtualSensors;
  if (data.sensors && data.autonomy) {
    const sensors = data.sensors;
    const nav = data.autonomy;
    const observations = Object.values(sensors.observations || {});
    const oldest = observations.length ? Math.max(...observations.map(value => value.age)) : null;
    show("navState", (data.motion?.appMode || "idle") + " / " + nav.state);
    show("navRange", (sensors.front_m == null ? "Unknown" : sensors.front_m.toFixed(3) + " m") + " / " + nav.obstacle);
    show("navHealth", (sensors.fault || "OK") + " / " + (oldest == null ? "missing" : Math.round(oldest * 1000) + " ms maximum age"));
    show("navTouch", Object.entries(sensors.touches || {}).map(([key, value]) => key + ": " + (value.stuck ? "STUCK" : !value.valid ? "INVALID" : value.pressed ? "pressed" : "released")).join(" / "));
    show("navDecision", nav.reason + " / " + (nav.lastRequestedMotion || "none"));
    show("navOverride", (data.motion?.fault || sensors.fault || "none") + " / " + (data.bridge?.connected ? "simulator connected" : "no simulator"));
  }
  show("traceDiagnostics", link.targets ? link.targets.join(" / ") + " | active mask " + link.activeMask : "No protocol trace (legacy unit stub or inhibited serial monitor)");
}


function renderDecisions(data) {
  const config = data.visionConfig;
  const select = document.getElementById("targetColorSelect");
  const search = document.getElementById("targetSearch");
  if (select && search) {
    select.disabled = search.disabled = !data.simulation || !config;
    if (config) {
      state.visionRevision = config.revision;
      select.value = config.settings.target_color;
      search.checked = config.settings.search_enabled;
    }
  }
  const synthetic = document.getElementById("syntheticTargetControls");
  if (synthetic) synthetic.hidden = !data.simulation || data.camera?.backend !== "synthetic";
  const actions = document.getElementById("interactionActions");
  if (actions) {
    actions.hidden = !data.features?.virtualSensors;
    actions.querySelectorAll("button").forEach(button => {button.disabled = !data.motion?.enabled || data.motion?.appMode !== "interaction" || data.motion?.busy;});
  }
  const target = data.vision?.blueBall || {};
  const age = data.vision?.observationAge;
  const summary = document.getElementById("targetDetection");
  if (summary) summary.textContent = (data.vision?.targetColor || "unknown") + ": " +
    (data.vision?.targetFresh && target.detected ? "candidate detected; error " + Number(target.offset).toFixed(3) +
      "; " + (target.lockState || "unknown lock") : "no fresh locked target") +
    "; age " + (age == null ? "unavailable" : Math.round(age * 1000) + " ms");
  const request = data.motion?.lastRequest;
  const outcome = document.getElementById("motionOutcome");
  if (outcome) outcome.textContent = "Request: " + (request ? request.motion + " / " + request.status + " / " + request.reason : "none") +
    "; virtual Uno active: " + (data.link?.activeMotion || "none") + "; STOP/fault: " + (data.motion?.fault || "none");
  const history = data.decisionHistory || [];
  const sequence = history.length ? history[history.length - 1].seq : 0;
  const list = document.getElementById("decisionHistory");
  if (list && sequence !== state.historySequence) {
    state.historySequence = sequence;
    list.replaceChildren(...history.slice(-32).map(entry => {
      const row = document.createElement("li");
      row.textContent = entry.time + " — " + entry.kind + ": " + entry.status +
        (entry.motion ? " / " + entry.motion : "") + (entry.reason ? " / " + entry.reason : "") +
        (entry.requestId == null ? "" : " / request " + entry.requestId);
      return row;
    }));
  }
}
async function changeTargetSettings() {
  releaseAllMovement("target-change", false);
  try {
    await fetchJson("/api/vision", {method:"POST",body:JSON.stringify({
      revision:state.visionRevision,
      target_color:document.getElementById("targetColorSelect").value,
      search_enabled:document.getElementById("targetSearch").checked
    })});
    setResult("Target settings applied; explicitly enable virtual actuators again.");
  } catch (error) {setResult(error.message);}
  await loadState();
}
document.getElementById("targetColorSelect")?.addEventListener("change", changeTargetSettings);
document.getElementById("targetSearch")?.addEventListener("change", changeTargetSettings);

document.querySelectorAll("[data-interaction]").forEach(button => {
  button.addEventListener("click", async () => {
    try {
      await fetchJson("/api/interaction",{method:"POST",body:JSON.stringify({name:button.dataset.interaction})});
      setResult("Interaction intent queued; execution is shown in command history.");
    } catch (error) {setResult(error.message);}
    await loadState();
  });
});

document.querySelectorAll("[data-synthetic-target]").forEach(button => {
  button.addEventListener("click",async()=>{
    try {
      await fetchJson("/api/simulation/target",{method:"POST",body:JSON.stringify({
        visible:button.dataset.syntheticTarget!=="hide",
        x:button.dataset.syntheticTarget==="hide"?0:Number(button.dataset.syntheticTarget),
        color:document.getElementById("targetColorSelect").value
      })});
    } catch(error) {setResult(error.message);}
    await loadState();
  });
});
