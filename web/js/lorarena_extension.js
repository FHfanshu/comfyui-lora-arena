import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { createVotingWidget } from "./voting_widget.js";
import { createLeaderboardWidget } from "./leaderboard_widget.js";

const STRINGS = (() => {
  const lang = navigator.language || "en";
  const isZh = lang.toLowerCase().startsWith("zh");
  return {
    button: isZh ? "🏆 LoRArena" : "🏆 LoRArena",
    title: isZh ? "LoRArena 配置" : "LoRArena Settings",
    close: isZh ? "关闭" : "Close",
    save: isZh ? "保存" : "Save",
    saving: isZh ? "保存中..." : "Saving...",
    loaded: isZh ? "已加载" : "Loaded",
    loadFailed: isZh ? "加载失败" : "Load failed",
    saved: isZh ? "已保存" : "Saved",
    saveFailed: isZh ? "保存失败" : "Save failed",
    loraDir: isZh ? "LoRA 目录" : "LoRA Directory",
    trainingDir: isZh ? "训练集/提示词目录" : "Training/Prompt Dir",
    basic: isZh ? "基础配置" : "Basics",
    promptPrefix: isZh ? "提示词前缀" : "Prompt Prefix",
    promptPrefixHint: isZh ? "添加到随机提示词前面" : "Prepended to random prompts",
    battleRoyale: isZh ? "大逃杀模式" : "Battle Royale",
    battleRoyaleEnabled: isZh ? "启用大逃杀" : "Enable Battle Royale",
    battleRoyaleThreshold: isZh ? "最低场次" : "Min Battles",
    battleRoyaleWinRate: isZh ? "最低胜率" : "Min Win Rate",
    battleRoyaleThresholdHint: isZh ? "达到此场次后开始淘汰" : "Start elimination after this many battles",
    battleRoyaleWinRateHint: isZh ? "低于此胜率将被淘汰 (0-1)" : "Eliminate if win rate below this (0-1)",
    hostGuest: isZh ? "模式" : "Mode",
    hostMode: isZh ? "主持人模式" : "Host Mode",
    guestMode: isZh ? "访客模式" : "Guest Mode",
    modeHint: isZh ? "访客模式只能投票和看排行" : "Guest mode: vote and view only",
    scan: isZh ? "扫描导入" : "Scan LoRAs",
    scanning: isZh ? "扫描中..." : "Scanning...",
    scanSuccess: isZh ? "导入成功" : "Import success",
    scanFailed: isZh ? "扫描失败" : "Scan failed",
    scanHint: isZh ? "扫描并导入LoRA到数据库" : "Scan and import LoRAs to database",
    eliminate: isZh ? "执行淘汰" : "Eliminate",
    eliminating: isZh ? "淘汰中..." : "Eliminating...",
    eliminateSuccess: isZh ? "淘汰完成" : "Elimination done",
    eliminateFailed: isZh ? "淘汰失败" : "Elimination failed",
    eliminateHint: isZh ? "移动低胜率LoRA到上级目录" : "Move low win-rate LoRAs to parent dir",
    refresh: isZh ? "刷新状态" : "Refresh",
    refreshing: isZh ? "刷新中..." : "Refreshing...",
    refreshSuccess: isZh ? "刷新完成" : "Refresh done",
    refreshFailed: isZh ? "刷新失败" : "Refresh failed",
    refreshHint: isZh ? "检查LoRA文件是否存在" : "Check if LoRA files exist",
  };
})();

function ensureStyles() {
  if (document.getElementById("lorarena-panel-style")) return;
  const style = document.createElement("style");
  style.id = "lorarena-panel-style";
  style.textContent = `
    .lorarena-hover-panel {
      position: fixed;
      right: 20px;
      bottom: 72px;
      width: 360px;
      max-height: 70vh;
      z-index: 10001;
      display: none;
      flex-direction: column;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(15, 17, 21, 0.98);
      backdrop-filter: blur(8px);
      box-shadow: 0 16px 40px rgba(0,0,0,0.45);
      overflow: hidden;
    }
    .lorarena-hover-panel.open {
      display: flex;
    }
    .lorarena-hover-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      background: rgba(24, 27, 32, 0.9);
      border-bottom: 1px solid rgba(255,255,255,0.06);
      font-size: 13px;
      color: #e5e7eb;
      font-weight: 600;
    }
    .lorarena-hover-close {
      border: none;
      background: transparent;
      color: #9ca3af;
      cursor: pointer;
      font-size: 14px;
      padding: 2px 6px;
      border-radius: 6px;
    }
    .lorarena-hover-close:hover {
      background: rgba(255,255,255,0.08);
      color: #f3f4f6;
    }
    .lorarena-hover-body {
      padding: 10px 12px;
      display: grid;
      gap: 10px;
      overflow-y: auto;
    }
    .lorarena-field label {
      display: block;
      font-size: 11px;
      color: #9ca3af;
      margin-bottom: 4px;
    }
    .lorarena-field input {
      width: 100%;
      padding: 6px 8px;
      border-radius: 8px;
      border: 1px solid #1f2937;
      background: #111827;
      color: #e5e7eb;
      font-size: 12px;
      outline: none;
    }
    .lorarena-field input:focus {
      border-color: #6b7280;
      box-shadow: 0 0 0 2px rgba(99,102,241,0.2);
    }
    .lorarena-toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 4px 0;
    }
    .lorarena-toggle-label {
      font-size: 12px;
      color: #e5e7eb;
    }
    .lorarena-toggle {
      position: relative;
      width: 40px;
      height: 22px;
      background: #374151;
      border-radius: 11px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .lorarena-toggle.active {
      background: #10b981;
    }
    .lorarena-toggle::after {
      content: '';
      position: absolute;
      top: 2px;
      left: 2px;
      width: 18px;
      height: 18px;
      background: #fff;
      border-radius: 50%;
      transition: transform 0.2s;
    }
    .lorarena-toggle.active::after {
      transform: translateX(18px);
    }
    .lorarena-section {
      display: grid;
      gap: 10px;
    }
    .lorarena-section-title {
      font-size: 10px;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }
    .lorarena-hover-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 12px 12px;
      border-top: 1px solid rgba(255,255,255,0.06);
      font-size: 11px;
      color: #9ca3af;
    }
    .lorarena-hover-footer a {
      color: #93c5fd;
      text-decoration: none;
    }
    .lorarena-hover-footer a:hover {
      text-decoration: underline;
    }
    .lorarena-hover-save {
      border: none;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #fff;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
    }
    .lorarena-hover-save:disabled {
      opacity: 0.6;
      cursor: default;
    }
    .lorarena-scan-btn {
      border: none;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: #fff;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
    }
    .lorarena-scan-btn:disabled {
      opacity: 0.6;
      cursor: default;
    }
    .lorarena-action-btn {
      border: none;
      background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
      color: #fff;
      padding: 6px 10px;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
    }
    .lorarena-action-btn:hover {
      background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
    }
    .lorarena-action-btn:disabled {
      opacity: 0.6;
      cursor: default;
    }
    .lorarena-action-btn.danger {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }
    .lorarena-action-btn.danger:hover {
      background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
    }
    .lorarena-actions-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .lorarena-launch-btn {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 10000;
      width: 52px;
      height: 52px;
      padding: 0;
      border-radius: 9999px;
      border: 2px solid #6366f1;
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      color: #fff;
      cursor: pointer;
      font-weight: bold;
      font-size: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
      transition: all 0.2s ease;
      user-select: none;
      touch-action: none;
      cursor: grab;
    }
    .lorarena-launch-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
    }
    .lorarena-launch-btn.dragging {
      cursor: grabbing;
      transform: none;
    }
  `;
  document.head.appendChild(style);
}

function createHoverPanel() {
  ensureStyles();
  let panel = document.getElementById("lorarena-hover-panel");
  if (panel) return panel;

  panel = document.createElement("div");
  panel.id = "lorarena-hover-panel";
  panel.className = "lorarena-hover-panel";
  panel.innerHTML = `
    <div class="lorarena-hover-header">
      <span>${STRINGS.title}</span>
      <button class="lorarena-hover-close" type="button" title="${STRINGS.close}">✕</button>
    </div>
    <div class="lorarena-hover-body">
      <div class="lorarena-section">
        <div class="lorarena-section-title">${STRINGS.basic}</div>
        <div class="lorarena-field">
          <label>${STRINGS.loraDir}</label>
          <input type="text" data-field="lora_directory" placeholder="styles/748cm" />
        </div>
        <div class="lorarena-field">
          <label>${STRINGS.trainingDir}</label>
          <input type="text" data-field="training_data_directory" placeholder="E:\\Dataset\\748cm" />
        </div>
        <div class="lorarena-field">
          <label>${STRINGS.promptPrefix}</label>
          <input type="text" data-field="prompt_prefix" placeholder="1girl, " />
          <small style="color:#6b7280;font-size:10px;">${STRINGS.promptPrefixHint}</small>
        </div>
      </div>
      <div class="lorarena-section">
        <div class="lorarena-section-title">${STRINGS.battleRoyale}</div>
        <div class="lorarena-toggle-row">
          <span class="lorarena-toggle-label">${STRINGS.battleRoyaleEnabled}</span>
          <div class="lorarena-toggle" data-field="battle_royale_enabled" data-type="boolean"></div>
        </div>
        <div class="lorarena-field">
          <label>${STRINGS.battleRoyaleThreshold}</label>
          <input type="number" data-field="battle_royale_threshold" placeholder="10" min="1" />
          <small style="color:#6b7280;font-size:10px;">${STRINGS.battleRoyaleThresholdHint}</small>
        </div>
        <div class="lorarena-field">
          <label>${STRINGS.battleRoyaleWinRate}</label>
          <input type="number" data-field="battle_royale_win_rate" placeholder="0.3" min="0" max="1" step="0.05" />
          <small style="color:#6b7280;font-size:10px;">${STRINGS.battleRoyaleWinRateHint}</small>
        </div>
        <div class="lorarena-actions-row" style="margin-top:8px;">
          <button class="lorarena-action-btn danger lorarena-eliminate-btn" type="button" title="${STRINGS.eliminateHint}">${STRINGS.eliminate}</button>
          <button class="lorarena-action-btn lorarena-refresh-btn" type="button" title="${STRINGS.refreshHint}">${STRINGS.refresh}</button>
        </div>
      </div>
      <div class="lorarena-section">
        <div class="lorarena-section-title">${STRINGS.hostGuest}</div>
        <div class="lorarena-field">
          <select data-field="mode" style="width:100%;padding:6px 8px;border-radius:8px;border:1px solid #1f2937;background:#111827;color:#e5e7eb;font-size:12px;">
            <option value="host">${STRINGS.hostMode}</option>
            <option value="guest">${STRINGS.guestMode}</option>
          </select>
          <small style="color:#6b7280;font-size:10px;">${STRINGS.modeHint}</small>
        </div>
      </div>
    </div>
    <div class="lorarena-hover-footer">
      <span class="lorarena-hover-status" data-status>${STRINGS.loaded}</span>
      <div style="display:flex;gap:8px;">
        <button class="lorarena-scan-btn" type="button" title="${STRINGS.scanHint}">${STRINGS.scan}</button>
        <button class="lorarena-hover-save" type="button">${STRINGS.save}</button>
      </div>
    </div>
  `;

  document.body.appendChild(panel);
  return panel;
}

async function loadHoverConfig(panel) {
  const status = panel.querySelector("[data-status]");
  if (status) status.textContent = STRINGS.loaded;

  try {
    const configRes = await fetch("/lorarena/api/config");

    if (!configRes.ok) throw new Error("config");
    const config = await configRes.json();

    const fields = panel.querySelectorAll("[data-field]");
    fields.forEach((field) => {
      const key = field.getAttribute("data-field");
      const type = field.getAttribute("data-type");
      if (!key) return;
      if (config[key] !== undefined && config[key] !== null) {
        if (type === "boolean") {
          // Toggle switch
          if (config[key]) {
            field.classList.add("active");
          } else {
            field.classList.remove("active");
          }
        } else {
          field.value = config[key];
        }
      }
    });

    // Add click handlers for toggles
    panel.querySelectorAll(".lorarena-toggle").forEach((toggle) => {
      toggle.onclick = () => toggle.classList.toggle("active");
    });

    // Guest mode: disable editing of most fields
    const isGuest = config.mode === "guest";
    if (isGuest) {
      // Disable all inputs except the mode selector itself
      fields.forEach((field) => {
        const key = field.getAttribute("data-field");
        if (key !== "mode") {
          field.disabled = true;
          field.style.opacity = "0.5";
          field.style.pointerEvents = "none";
        }
      });
      // Disable save and scan buttons
      const saveBtn = panel.querySelector(".lorarena-hover-save");
      const scanBtn = panel.querySelector(".lorarena-scan-btn");
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.style.opacity = "0.5";
      }
      if (scanBtn) {
        scanBtn.disabled = true;
        scanBtn.style.opacity = "0.5";
      }
      if (status) status.textContent = STRINGS.guestMode;
    }

  } catch (error) {
    if (status) status.textContent = STRINGS.loadFailed;
    console.error("[LoRArena] Failed to load hover config:", error);
  }
}

async function saveHoverConfig(panel) {
  const status = panel.querySelector("[data-status]");
  const saveBtn = panel.querySelector(".lorarena-hover-save");
  if (saveBtn) saveBtn.disabled = true;
  if (status) status.textContent = STRINGS.saving;

  const payload = {};
  const fields = panel.querySelectorAll("[data-field]");
  fields.forEach((field) => {
    const key = field.getAttribute("data-field");
    const type = field.getAttribute("data-type");
    if (!key) return;

    // Handle boolean toggles
    if (type === "boolean") {
      payload[key] = field.classList.contains("active");
      return;
    }

    let value = field.value;
    if (value === "") return;

    if (["battle_royale_threshold", "auto_queue_target", "auto_queue_max"].includes(key)) {
      const parsed = parseInt(value, 10);
      if (!Number.isNaN(parsed)) payload[key] = parsed;
      return;
    }

    if (["lora_strength", "battle_royale_win_rate"].includes(key)) {
      const parsed = parseFloat(value);
      if (!Number.isNaN(parsed)) payload[key] = parsed;
      return;
    }

    payload[key] = value;
  });

  try {
    const response = await fetch("/lorarena/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("save");
    if (status) status.textContent = STRINGS.saved;
  } catch (error) {
    if (status) status.textContent = STRINGS.saveFailed;
    console.error("[LoRArena] Failed to save hover config:", error);
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

function addLauncherButton() {
  if (document.getElementById("lorarena-launch-button")) return;

  ensureStyles();

  const panel = createHoverPanel();
  const closeBtn = panel.querySelector(".lorarena-hover-close");
  const saveBtn = panel.querySelector(".lorarena-hover-save");
  const scanBtn = panel.querySelector(".lorarena-scan-btn");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => panel.classList.remove("open"));
  }
  if (saveBtn) {
    saveBtn.addEventListener("click", () => saveHoverConfig(panel));
  }
  if (scanBtn) {
    scanBtn.addEventListener("click", async () => {
      const status = panel.querySelector("[data-status]");
      scanBtn.disabled = true;
      scanBtn.textContent = STRINGS.scanning;
      if (status) status.textContent = STRINGS.scanning;

      try {
        // First save config to ensure lora_directory is up to date
        await saveHoverConfig(panel);

        // Get the lora_directory from the input field
        const loraDirInput = panel.querySelector('[data-field="lora_directory"]');
        const loraDirectory = loraDirInput ? loraDirInput.value.trim() : "";

        const response = await fetch("/lorarena/api/checkpoints/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ directory: loraDirectory || null }),
        });
        const result = await response.json();
        if (response.ok) {
          const msg = `${STRINGS.scanSuccess}: ${result.imported}/${result.scanned}`;
          if (status) status.textContent = msg;
          scanBtn.textContent = STRINGS.scan;
        } else {
          throw new Error(result.detail || "Scan failed");
        }
      } catch (error) {
        console.error("[LoRArena] Scan failed:", error);
        const status = panel.querySelector("[data-status]");
        if (status) status.textContent = STRINGS.scanFailed;
        scanBtn.textContent = STRINGS.scan;
      } finally {
        scanBtn.disabled = false;
      }
    });
  }

  // Eliminate button
  const eliminateBtn = panel.querySelector(".lorarena-eliminate-btn");
  if (eliminateBtn) {
    eliminateBtn.addEventListener("click", async () => {
      const status = panel.querySelector("[data-status]");
      eliminateBtn.disabled = true;
      eliminateBtn.textContent = STRINGS.eliminating;
      if (status) status.textContent = STRINGS.eliminating;

      try {
        // First save config
        await saveHoverConfig(panel);

        const response = await fetch("/lorarena/api/checkpoints/eliminate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const result = await response.json();
        if (response.ok && result.success) {
          const msg = `${STRINGS.eliminateSuccess}: ${result.eliminated} (${result.moved} moved)`;
          if (status) status.textContent = msg;
        } else {
          const errorMsg = result.errors?.join(", ") || "Unknown error";
          if (status) status.textContent = errorMsg;
        }
      } catch (error) {
        console.error("[LoRArena] Eliminate failed:", error);
        if (status) status.textContent = STRINGS.eliminateFailed;
      } finally {
        eliminateBtn.disabled = false;
        eliminateBtn.textContent = STRINGS.eliminate;
      }
    });
  }

  // Refresh button
  const refreshBtn = panel.querySelector(".lorarena-refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      const status = panel.querySelector("[data-status]");
      refreshBtn.disabled = true;
      refreshBtn.textContent = STRINGS.refreshing;
      if (status) status.textContent = STRINGS.refreshing;

      try {
        const response = await fetch("/lorarena/api/checkpoints/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const result = await response.json();
        if (response.ok) {
          const msg = `${STRINGS.refreshSuccess}: ${result.deactivated} deactivated`;
          if (status) status.textContent = msg;
        } else {
          throw new Error("Refresh failed");
        }
      } catch (error) {
        console.error("[LoRArena] Refresh failed:", error);
        if (status) status.textContent = STRINGS.refreshFailed;
      } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = STRINGS.refresh;
      }
    });
  }

  const button = document.createElement("button");
  button.id = "lorarena-launch-button";
  button.className = "lorarena-launch-btn";
  button.textContent = "🏆";
  button.title = "LoRArena";

  let isDragging = false;
  let dragMoved = false;
  let dragStartX = 0;
  let dragStartY = 0;
  const DRAG_THRESHOLD = 3;
  const BUTTON_SIZE = 52;

  const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

  const loadButtonPosition = () => {
    try {
      const raw = localStorage.getItem("lorarena-launch-pos");
      if (!raw) return;
      const pos = JSON.parse(raw);
      if (typeof pos.left === "number" && typeof pos.top === "number") {
        button.style.left = `${pos.left}px`;
        button.style.top = `${pos.top}px`;
        button.style.right = "auto";
        button.style.bottom = "auto";
      }
    } catch (err) {
      // ignore
    }
  };

  const saveButtonPosition = () => {
    const rect = button.getBoundingClientRect();
    try {
      localStorage.setItem(
        "lorarena-launch-pos",
        JSON.stringify({ left: rect.left, top: rect.top })
      );
    } catch (err) {
      // ignore
    }
  };

  const positionPanel = () => {
    if (!panel.classList.contains("open")) return;
    const btnRect = button.getBoundingClientRect();
    panel.style.right = "auto";
    panel.style.bottom = "auto";
    panel.style.left = "0px";
    panel.style.top = "0px";
    const panelRect = panel.getBoundingClientRect();
    let left = btnRect.left + btnRect.width / 2 - panelRect.width / 2;
    let top = btnRect.top - panelRect.height - 12;
    if (top < 10) {
      top = btnRect.bottom + 12;
    }
    left = clamp(left, 10, window.innerWidth - panelRect.width - 10);
    top = clamp(top, 10, window.innerHeight - panelRect.height - 10);
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
  };

  const openPanel = () => {
    panel.classList.add("open");
    loadHoverConfig(panel);
    requestAnimationFrame(() => positionPanel());
  };
  const closePanel = () => panel.classList.remove("open");

  // Drag handlers on document level for smooth dragging
  const onMouseMove = (e) => {
    if (!isDragging) return;

    const dx = Math.abs(e.clientX - dragStartX);
    const dy = Math.abs(e.clientY - dragStartY);

    if (!dragMoved && (dx >= DRAG_THRESHOLD || dy >= DRAG_THRESHOLD)) {
      dragMoved = true;
      button.classList.add("dragging");
    }

    if (dragMoved) {
      // Center the button on the cursor
      let left = e.clientX - BUTTON_SIZE / 2;
      let top = e.clientY - BUTTON_SIZE / 2;
      left = clamp(left, 0, window.innerWidth - BUTTON_SIZE);
      top = clamp(top, 0, window.innerHeight - BUTTON_SIZE);
      button.style.left = `${left}px`;
      button.style.top = `${top}px`;
      button.style.right = "auto";
      button.style.bottom = "auto";
      positionPanel();
    }
  };

  const onMouseUp = () => {
    if (!isDragging) return;
    isDragging = false;
    button.classList.remove("dragging");
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    if (dragMoved) {
      saveButtonPosition();
    }
  };

  // Click button to toggle panel
  button.addEventListener("click", (e) => {
    // If we just finished dragging, ignore this click
    if (dragMoved) {
      e.preventDefault();
      e.stopPropagation();
      dragMoved = false;
      return;
    }
    if (panel.classList.contains("open")) {
      closePanel();
    } else {
      openPanel();
    }
  });

  button.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    isDragging = true;
    dragMoved = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });

  loadButtonPosition();

  // Always add as fixed button in bottom-right corner
  document.body.appendChild(button);
  console.log("[LoRArena] Launch button added to page");
}

app.registerExtension({
  name: "lorarena",
  async setup() {
    console.log("[LoRArena] Extension setup starting...");
    try {
      createVotingWidget(app, api);
      createLeaderboardWidget(app, api);
      addLauncherButton();
      console.log("[LoRArena] Extension loaded successfully!");
    } catch (error) {
      console.error("[LoRArena] Extension setup failed:", error);
    }
  },
});
