/**
 * app.js — DevReplicator UI logic
 * Communicates with the Python CLI via a local API bridge (port 7475).
 * Falls back to a simulated demo mode if the bridge is not running.
 */

"use strict";

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  running: false,
  steps: 0,
  totalSteps: 5,
  result: null,
};

const API_BASE = "http://127.0.0.1:7475";

// ── DOM refs ─────────────────────────────────────────────────────────────────
const urlInput     = () => document.getElementById("urlInput");
const runBtn       = () => document.getElementById("runBtn");
const progressWrap = () => document.getElementById("progressWrap");
const progressFill = () => document.getElementById("progressFill");
const progressLabel= () => document.getElementById("progressLabel");
const consoleEl    = () => document.getElementById("console");
const resultPanel  = () => document.getElementById("resultPanel");
const resultGrid   = () => document.getElementById("resultGrid");
const cmdList      = () => document.getElementById("cmdList");

// ── Entry point ──────────────────────────────────────────────────────────────
async function startReplication() {
  const url = urlInput().value.trim();
  if (!url) {
    appendLog("error", "✖", "Please enter a GitHub repository URL.");
    return;
  }

  if (!/^https?:\/\/(www\.)?github\.com\/.+\/.+/.test(url)) {
    appendLog("warn", "⚠", "URL does not look like a GitHub repository — proceeding anyway.");
  }

  setRunning(true);
  clearConsole();
  setProgress(0, "Starting …");

  try {
    // Try real API bridge first
    const bridgeReachable = await checkBridge();
    if (bridgeReachable) {
      await runViaAPI(url);
    } else {
      await runSimulated(url);
    }
  } catch (err) {
    appendLog("error", "✖", `Unexpected error: ${err.message}`);
  } finally {
    setRunning(false);
  }
}

// ── API bridge mode ──────────────────────────────────────────────────────────
async function checkBridge() {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(800) });
    return r.ok;
  } catch {
    return false;
  }
}

async function runViaAPI(url) {
  const response = await fetch(`${API_BASE}/replicate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const lines = decoder.decode(value).split("\n").filter(Boolean);
    for (const line of lines) {
      try {
        const event = JSON.parse(line);
        handleAPIEvent(event);
      } catch {
        // raw line
        appendLog("info", "›", line);
      }
    }
  }
}

function handleAPIEvent(event) {
  const { type, message, step, result } = event;
  switch (type) {
    case "info":    appendLog("info",    "›", message); break;
    case "success": appendLog("success", "✔", message); break;
    case "warn":    appendLog("warn",    "⚠", message); break;
    case "error":   appendLog("error",   "✖", message); break;
    case "step":
      setProgress((step / state.totalSteps) * 100, message);
      appendLog("step", `[${step}/${state.totalSteps}]`, message);
      break;
    case "done":
      setProgress(100, "Complete");
      showResults(result);
      break;
  }
}

// ── Simulated demo mode ──────────────────────────────────────────────────────
async function runSimulated(url) {
  appendLog("warn", "⚠", "API bridge not running — demo simulation mode.");
  appendLog("dim",  "·", "To run for real: python replicator.py (CLI mode)");
  await sleep(400);

  const repoName = url.split("/").pop().replace(".git", "") || "repo";
  const imageTag = `devreplicator-${url.split("github.com/").pop().replace(/\//g, "-").toLowerCase()}`;
  const containerName = `devreplicator-${repoName.toLowerCase()}`;

  const steps = [
    [1, "Cloning repository …",         () => [
      { t: "info",    m: `git clone --depth=1 ${url}` },
      { t: "success", m: `Repository cloned to /tmp/devreplicator_${repoName}` },
    ]],
    [2, "Detecting project type …",     () => [
      { t: "info",    m: "Scanning for requirements.txt / pyproject.toml / package.json …" },
      { t: "info",    m: "Detected: requirements.txt → Python (pip) project" },
      { t: "info",    m: "Entry point detected: app.py" },
    ]],
    [3, "Generating Dockerfile …",      () => [
      { t: "info",    m: "Writing Dockerfile.devreplicator …" },
      { t: "info",    m: "Base image: python:3.11-slim" },
      { t: "success", m: "Dockerfile written" },
    ]],
    [4, "Building Docker image …",      () => [
      { t: "info",    m: `docker build -f Dockerfile.devreplicator -t ${imageTag} .` },
      { t: "info",    m: "Step 1/5 : FROM python:3.11-slim" },
      { t: "info",    m: "Step 2/5 : RUN apt-get update …" },
      { t: "info",    m: "Step 3/5 : COPY requirements.txt ." },
      { t: "info",    m: "Step 4/5 : RUN pip install …" },
      { t: "info",    m: "Step 5/5 : CMD [\"python\", \"app.py\"]" },
      { t: "success", m: `Image built: ${imageTag}` },
    ]],
    [5, "Starting container …",         () => [
      { t: "info",    m: `docker run -d --name ${containerName} ${imageTag}` },
      { t: "success", m: `Container running: ${containerName}` },
    ]],
  ];

  for (const [stepNum, label, logsFn] of steps) {
    setProgress((stepNum - 1) / state.totalSteps * 100, label);
    appendLog("step", `[${stepNum}/${state.totalSteps}]`, label);
    await sleep(320);
    for (const { t, m } of logsFn()) {
      await sleep(180);
      const icon = t === "info" ? "›" : t === "success" ? "✔" : t === "warn" ? "⚠" : "✖";
      appendLog(t, icon, m);
    }
  }

  setProgress(100, "Complete");
  appendLog("success", "✔", "DevReplicator finished successfully.");

  showResults({
    imageTag,
    containerName,
    projectType: "python",
    depFile: "requirements.txt",
    entryPoint: "app.py",
    repoPath: `/tmp/devreplicator_${repoName}`,
  });
}

// ── UI helpers ───────────────────────────────────────────────────────────────
function appendLog(type, icon, message) {
  const el = consoleEl();
  const ts  = new Date().toLocaleTimeString("en-GB", { hour12: false });

  const line = document.createElement("div");
  line.className = `log-line ${type}`;
  line.innerHTML = `
    <span class="log-ts">${ts}</span>
    <span class="log-icon">${icon}</span>
    <span class="log-msg">${escHtml(message)}</span>
  `;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function clearConsole() {
  consoleEl().innerHTML = "";
}

function setProgress(pct, label) {
  progressWrap().classList.add("visible");
  progressFill().style.width = `${Math.min(pct, 100)}%`;
  progressLabel().textContent = label;
}

function setRunning(on) {
  state.running = on;
  runBtn().disabled = on;
  runBtn().textContent = on ? "⏳ Running …" : "▶ Replicate";
}

function resetUI() {
  urlInput().value = "";
  clearConsole();
  appendLog("dim", "·", "Awaiting repository URL …");
  progressWrap().classList.remove("visible");
  progressFill().style.width = "0%";
  resultPanel().classList.remove("visible");
  setRunning(false);
}

function showResults(r) {
  if (!r) return;

  resultGrid().innerHTML = `
    ${resultItem("Image Tag",      r.imageTag,      true)}
    ${resultItem("Container",      r.containerName, false)}
    ${resultItem("Project Type",   r.projectType,   false)}
    ${resultItem("Dep File",       r.depFile || "—", false)}
    ${resultItem("Entry Point",    r.entryPoint || "—", false)}
    ${resultItem("Source Path",    r.repoPath,      false)}
  `;

  const cmds = [
    `docker logs -f ${r.containerName}`,
    `docker exec -it ${r.containerName} bash`,
    `docker stop ${r.containerName}`,
    `docker rm -f ${r.containerName}`,
    `docker images ${r.imageTag}`,
  ];

  cmdList().innerHTML = cmds
    .map(cmd => `
      <div class="cmd-item">
        <span class="cmd-code">${escHtml(cmd)}</span>
        <button class="btn-copy" onclick="copyCmd(this, '${escAttr(cmd)}')">copy</button>
      </div>
    `)
    .join("");

  resultPanel().classList.add("visible");
}

function resultItem(label, value, accent) {
  return `
    <div class="result-item">
      <div class="result-label">${label}</div>
      <div class="result-value${accent ? " accent" : ""}">${escHtml(value || "—")}</div>
    </div>
  `;
}

function copyCmd(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "copied";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = "copy";
      btn.classList.remove("copied");
    }, 1800);
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escAttr(str) {
  return String(str).replace(/'/g, "\\'");
}

function sleep(ms) {
  return new Promise(res => setTimeout(res, ms));
}

// ── Keyboard shortcut ─────────────────────────────────────────────────────────
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && document.activeElement === urlInput() && !state.running) {
    startReplication();
  }
});
