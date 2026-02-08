import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { createVotingWidget } from "./voting_widget.js";
import { createLeaderboardWidget } from "./leaderboard_widget.js";

const STRINGS = (() => {
  const lang = navigator.language || "en";
  const isZh = lang.toLowerCase().startsWith("zh");
  return {
    // Menu items
    openSettings: isZh ? "打开设置" : "Open Settings",
    scanLoras: isZh ? "扫描LoRA" : "Scan LoRAs",
    eliminate: isZh ? "执行淘汰" : "Eliminate",
    refreshStatus: isZh ? "刷新状态" : "Refresh Status",
    resetElo: isZh ? "重置ELO" : "Reset ELO",
    // Settings panel
    title: isZh ? "LoRArena 设置" : "LoRArena Settings",
    close: isZh ? "关闭" : "Close",
    save: isZh ? "保存" : "Save",
    saving: isZh ? "保存中..." : "Saving...",
    saved: isZh ? "已保存" : "Saved",
    saveFailed: isZh ? "保存失败" : "Save failed",
    loraDir: isZh ? "LoRA 目录" : "LoRA Directory",
    trainingDir: isZh ? "训练集目录" : "Training Dir",
    battleRoyale: isZh ? "大逃杀模式" : "Battle Royale",
    battleRoyaleEnabled: isZh ? "启用大逃杀" : "Enable",
    battleRoyaleThreshold: isZh ? "最低场次" : "Min Battles",
    battleRoyaleWinRate: isZh ? "最低胜率" : "Min Win Rate",
    mode: isZh ? "模式" : "Mode",
    hostMode: isZh ? "主持人" : "Host",
    guestMode: isZh ? "访客" : "Guest",
    openMenu: isZh ? "打开菜单" : "Open menu",
    // Status messages
    scanning: isZh ? "扫描中..." : "Scanning...",
    scanSuccess: isZh ? "扫描完成" : "Scan complete",
    scanFailed: isZh ? "扫描失败" : "Scan failed",
    eliminating: isZh ? "淘汰中..." : "Eliminating...",
    eliminateSuccess: isZh ? "淘汰完成" : "Elimination done",
    eliminateFailed: isZh ? "淘汰失败" : "Elimination failed",
    refreshing: isZh ? "刷新中..." : "Refreshing...",
    refreshSuccess: isZh ? "刷新完成" : "Refresh done",
    refreshFailed: isZh ? "刷新失败" : "Refresh failed",
    resetting: isZh ? "重置中..." : "Resetting...",
    resetSuccess: isZh ? "重置完成" : "Reset done",
    resetFailed: isZh ? "重置失败" : "Reset failed",
    // Confirm dialogs
    confirmEliminate: isZh
      ? "确定要执行淘汰吗？低胜率的LoRA将被移动到上级目录。"
      : "Are you sure you want to eliminate? Low win-rate LoRAs will be moved to parent directory.",
    confirmReset: isZh
      ? "确定要重置所有LoRA的ELO评分吗？此操作不可撤销。"
      : "Are you sure you want to reset all ELO ratings? This action cannot be undone.",
  };
})();

function ensureStyles() {
  if (document.getElementById("lorarena-style")) return;
  const style = document.createElement("style");
  style.id = "lorarena-style";
  style.textContent = `
    /* Floating button */
    .lorarena-ball {
      position: fixed;
      z-index: 120;
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: #6366f1;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      user-select: none;
      font-size: 22px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      transition: box-shadow 0.2s;
    }
    .lorarena-ball:hover {
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
    }

    /* Menu container */
    .lorarena-menu {
      position: fixed;
      z-index: 100;
      display: none;
      flex-direction: column;
      background: rgba(20, 20, 30, 0.95);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      padding: 8px 0;
      min-width: 140px;
      backdrop-filter: blur(8px);
    }
    .lorarena-menu.open {
      display: flex;
    }
    .lorarena-menu-item {
      padding: 10px 16px;
      color: #e5e7eb;
      font-size: 13px;
      cursor: pointer;
      transition: background 0.15s;
      white-space: nowrap;
    }
    .lorarena-menu-item:hover {
      background: rgba(99, 102, 241, 0.3);
    }
    .lorarena-menu-item.danger {
      color: #f87171;
    }
    .lorarena-menu-item.danger:hover {
      background: rgba(239, 68, 68, 0.3);
    }

    /* Settings panel */
    .lorarena-settings {
      position: fixed;
      z-index: 110;
      display: none;
      flex-direction: column;
      width: 320px;
      max-height: 80vh;
      background: rgba(15, 17, 21, 0.98);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
      overflow: hidden;
      backdrop-filter: blur(8px);
    }
    .lorarena-settings.open {
      display: flex;
    }
    .lorarena-settings-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: rgba(30, 30, 40, 0.9);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 14px;
      font-weight: 600;
      color: #e5e7eb;
    }
    .lorarena-settings-close {
      border: none;
      background: transparent;
      color: #9ca3af;
      cursor: pointer;
      font-size: 16px;
      padding: 4px 8px;
      border-radius: 6px;
    }
    .lorarena-settings-close:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }
    .lorarena-settings-body {
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .lorarena-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .lorarena-field label {
      font-size: 11px;
      color: #9ca3af;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .lorarena-field input,
    .lorarena-field select {
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid #374151;
      background: #1f2937;
      color: #e5e7eb;
      font-size: 13px;
      outline: none;
    }
    .lorarena-field input:focus,
    .lorarena-field select:focus {
      border-color: #6366f1;
      box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
    }
    .lorarena-toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .lorarena-toggle-label {
      font-size: 13px;
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
    .lorarena-settings-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    .lorarena-status {
      font-size: 11px;
      color: #9ca3af;
    }
    .lorarena-save-btn {
      border: none;
      background: #10b981;
      color: #fff;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .lorarena-save-btn:disabled {
      opacity: 0.6;
      cursor: default;
    }
    .lorarena-section-title {
      font-size: 10px;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-top: 8px;
    }

    /* Respect user's motion preferences */
    @media (prefers-reduced-motion: reduce) {
      .lorarena-ball,
      .lorarena-menu-item,
      .lorarena-toggle,
      .lorarena-toggle::after,
      .lorarena-settings-close,
      .lorarena-save-btn {
        transition: none !important;
      }
    }
  `;
  document.head.appendChild(style);
}

// Create settings panel
function createSettingsPanel() {
  let panel = document.getElementById("lorarena-settings");
  if (panel) return panel;

  panel = document.createElement("div");
  panel.id = "lorarena-settings";
  panel.className = "lorarena-settings";
  panel.innerHTML = `
    <div class="lorarena-settings-header">
      <span>${STRINGS.title}</span>
      <button class="lorarena-settings-close" type="button" aria-label="${STRINGS.close}">✕</button>
    </div>
    <div class="lorarena-settings-body">
      <div class="lorarena-field">
        <label>${STRINGS.loraDir}</label>
        <input type="text" data-field="lora_directory" placeholder="styles/my-loras" />
      </div>
      <div class="lorarena-field">
        <label>${STRINGS.trainingDir}</label>
        <input type="text" data-field="training_data_directory" placeholder="E:\\Dataset\\my-data" />
      </div>
      <div class="lorarena-section-title">${STRINGS.battleRoyale}</div>
      <div class="lorarena-toggle-row">
        <span class="lorarena-toggle-label">${STRINGS.battleRoyaleEnabled}</span>
        <div class="lorarena-toggle" data-field="battle_royale_enabled" data-type="boolean"></div>
      </div>
      <div class="lorarena-field">
        <label>${STRINGS.battleRoyaleThreshold}</label>
        <input type="number" data-field="battle_royale_threshold" placeholder="10" min="1" />
      </div>
      <div class="lorarena-field">
        <label>${STRINGS.battleRoyaleWinRate}</label>
        <input type="number" data-field="battle_royale_win_rate" placeholder="0.3" min="0" max="1" step="0.05" />
      </div>
      <div class="lorarena-section-title">${STRINGS.mode}</div>
      <div class="lorarena-field">
        <select data-field="mode">
          <option value="host">${STRINGS.hostMode}</option>
          <option value="guest">${STRINGS.guestMode}</option>
        </select>
      </div>
    </div>
    <div class="lorarena-settings-footer">
      <span class="lorarena-status"></span>
      <button class="lorarena-save-btn" type="button">${STRINGS.save}</button>
    </div>
  `;

  // Close button
  panel.querySelector(".lorarena-settings-close").addEventListener("click", () => {
    panel.classList.remove("open");
  });

  // Save button
  panel.querySelector(".lorarena-save-btn").addEventListener("click", () => saveSettings(panel));

  // Toggle click handlers
  panel.querySelectorAll(".lorarena-toggle").forEach((toggle) => {
    toggle.addEventListener("click", () => toggle.classList.toggle("active"));
  });

  document.body.appendChild(panel);
  return panel;
}

async function loadSettings(panel) {
  try {
    const res = await fetch("/lorarena/api/config");
    if (!res.ok) throw new Error("Failed to load config");
    const config = await res.json();

    panel.querySelectorAll("[data-field]").forEach((field) => {
      const key = field.getAttribute("data-field");
      const type = field.getAttribute("data-type");
      if (config[key] === undefined) return;

      if (type === "boolean") {
        field.classList.toggle("active", !!config[key]);
      } else {
        field.value = config[key];
      }
    });
  } catch (err) {
    console.error("[LoRArena] Failed to load settings:", err);
  }
}

async function saveSettings(panel) {
  const saveBtn = panel.querySelector(".lorarena-save-btn");
  const status = panel.querySelector(".lorarena-status");
  saveBtn.disabled = true;
  status.textContent = STRINGS.saving;

  const payload = {};
  panel.querySelectorAll("[data-field]").forEach((field) => {
    const key = field.getAttribute("data-field");
    const type = field.getAttribute("data-type");

    if (type === "boolean") {
      payload[key] = field.classList.contains("active");
    } else if (field.value !== "") {
      if (["battle_royale_threshold"].includes(key)) {
        payload[key] = parseInt(field.value, 10);
      } else if (["battle_royale_win_rate"].includes(key)) {
        payload[key] = parseFloat(field.value);
      } else {
        payload[key] = field.value;
      }
    }
  });

  try {
    const res = await fetch("/lorarena/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Save failed");
    status.textContent = STRINGS.saved;
  } catch (err) {
    status.textContent = STRINGS.saveFailed;
    console.error("[LoRArena] Failed to save settings:", err);
  } finally {
    saveBtn.disabled = false;
  }
}

function addLauncherButton() {
  if (document.getElementById("lorarena-ball")) return;

  ensureStyles();

  // Create floating ball
  const ball = document.createElement("div");
  ball.id = "lorarena-ball";
  ball.className = "lorarena-ball";
  ball.textContent = "🏆";
  ball.tabIndex = 0;
  ball.setAttribute("role", "button");
  ball.setAttribute("aria-haspopup", "menu");
  ball.setAttribute("aria-expanded", "false");
  ball.setAttribute("aria-label", STRINGS.openMenu);

  // Create menu
  const menu = document.createElement("div");
  menu.id = "lorarena-menu";
  menu.className = "lorarena-menu";
  menu.setAttribute("role", "menu");
  menu.innerHTML = `
    <div class="lorarena-menu-item" data-action="settings" role="menuitem" tabindex="0">${STRINGS.openSettings}</div>
    <div class="lorarena-menu-item" data-action="scan" role="menuitem" tabindex="0">${STRINGS.scanLoras}</div>
    <div class="lorarena-menu-item" data-action="refresh" role="menuitem" tabindex="0">${STRINGS.refreshStatus}</div>
    <div class="lorarena-menu-item danger" data-action="eliminate" role="menuitem" tabindex="0">${STRINGS.eliminate}</div>
    <div class="lorarena-menu-item danger" data-action="reset" role="menuitem" tabindex="0">${STRINGS.resetElo}</div>
  `;

  // Create settings panel
  const settingsPanel = createSettingsPanel();

  // Position ball from localStorage or default
  const BALL_SIZE = 52;
  const loadPosition = () => {
    try {
      const raw = localStorage.getItem("lorarena-ball-pos");
      if (raw) {
        const pos = JSON.parse(raw);
        ball.style.left = `${pos.x}px`;
        ball.style.top = `${pos.y}px`;
        return;
      }
    } catch (e) {}
    // Default position
    ball.style.left = `${window.innerWidth - 72}px`;
    ball.style.top = `${window.innerHeight - 100}px`;
  };

  const savePosition = () => {
    const rect = ball.getBoundingClientRect();
    localStorage.setItem("lorarena-ball-pos", JSON.stringify({ x: rect.left, y: rect.top }));
  };

  // Dragging with threshold to avoid accidental menu toggles
  const DRAG_THRESHOLD_PX = 4;
  let isDragging = false;
  let hasDragged = false;
  let suppressNextClick = false;
  let dragStartX = 0;
  let dragStartY = 0;

  const onMouseMove = (e) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    if (!hasDragged && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
    hasDragged = true;
    let x = e.clientX - BALL_SIZE / 2;
    let y = e.clientY - BALL_SIZE / 2;
    x = Math.max(0, Math.min(x, window.innerWidth - BALL_SIZE));
    y = Math.max(0, Math.min(y, window.innerHeight - BALL_SIZE));
    ball.style.left = `${x}px`;
    ball.style.top = `${y}px`;
  };

  const onMouseUp = () => {
    if (!isDragging) return;
    isDragging = false;
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    if (hasDragged) {
      savePosition();
      suppressNextClick = true;
      setTimeout(() => {
        suppressNextClick = false;
      }, 0);
    }
    hasDragged = false;
  };

  ball.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    isDragging = true;
    hasDragged = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });

  const openMenuNearBall = () => {
    // Position menu above the ball
    const rect = ball.getBoundingClientRect();
    const menuHeight = menu.offsetHeight || 200;
    let top = rect.top - menuHeight - 8;
    let left = rect.left + BALL_SIZE / 2 - 70;

    if (top < 10) top = rect.bottom + 8;
    left = Math.max(10, Math.min(left, window.innerWidth - 150));

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  };

  const closeMenu = () => {
    menu.classList.remove("open");
    ball.setAttribute("aria-expanded", "false");
  };

  const closeFloatingPanels = () => {
    closeMenu();
    settingsPanel.classList.remove("open");
  };

  const toggleMenu = () => {
    const isOpen = menu.classList.contains("open");
    if (isOpen) {
      closeMenu();
      return;
    }
    menu.classList.add("open");
    ball.setAttribute("aria-expanded", "true");
    settingsPanel.classList.remove("open");
    openMenuNearBall();
  };

  // Click to toggle menu
  ball.addEventListener("click", (e) => {
    e.stopPropagation();
    if (suppressNextClick) {
      return;
    }
    toggleMenu();
  });

  // Keyboard support for launcher button
  ball.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleMenu();
    } else if (e.key === "Escape") {
      closeFloatingPanels();
    }
  });

  // Close menu when clicking outside
  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target) && e.target !== ball) {
      closeMenu();
    }
    if (!settingsPanel.contains(e.target) && !menu.contains(e.target) && e.target !== ball) {
      settingsPanel.classList.remove("open");
    }
  });

  // Menu item handlers
  menu.addEventListener("click", async (e) => {
    const item = e.target.closest(".lorarena-menu-item");
    if (!item) return;

    const action = item.dataset.action;
    closeMenu();

    switch (action) {
      case "settings":
        settingsPanel.classList.add("open");
        loadSettings(settingsPanel);
        // Position settings panel
        const rect = ball.getBoundingClientRect();
        let top = rect.top - settingsPanel.offsetHeight - 8;
        let left = rect.left + BALL_SIZE / 2 - 160;
        if (top < 10) top = rect.bottom + 8;
        left = Math.max(10, Math.min(left, window.innerWidth - 330));
        top = Math.max(10, Math.min(top, window.innerHeight - settingsPanel.offsetHeight - 10));
        settingsPanel.style.left = `${left}px`;
        settingsPanel.style.top = `${top}px`;
        break;

      case "scan":
        item.textContent = STRINGS.scanning;
        try {
          const res = await fetch("/lorarena/api/checkpoints/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          const data = await res.json();
          if (res.ok) {
            alert(`${STRINGS.scanSuccess}: ${data.imported}/${data.scanned}`);
          } else {
            throw new Error(data.detail || "Scan failed");
          }
        } catch (err) {
          alert(STRINGS.scanFailed);
          console.error("[LoRArena] Scan failed:", err);
        }
        item.textContent = STRINGS.scanLoras;
        break;

      case "eliminate":
        if (!confirm(STRINGS.confirmEliminate)) return;
        item.textContent = STRINGS.eliminating;
        try {
          const res = await fetch("/lorarena/api/checkpoints/eliminate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const data = await res.json();
          if (res.ok && data.success) {
            alert(`${STRINGS.eliminateSuccess}: ${data.eliminated} (${data.moved} moved)`);
          } else {
            alert(data.errors?.join(", ") || STRINGS.eliminateFailed);
          }
        } catch (err) {
          alert(STRINGS.eliminateFailed);
          console.error("[LoRArena] Eliminate failed:", err);
        }
        item.textContent = STRINGS.eliminate;
        break;

      case "refresh":
        item.textContent = STRINGS.refreshing;
        try {
          const res = await fetch("/lorarena/api/checkpoints/refresh", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const data = await res.json();
          if (res.ok) {
            alert(`${STRINGS.refreshSuccess}: ${data.deactivated} deactivated`);
          } else {
            throw new Error("Refresh failed");
          }
        } catch (err) {
          alert(STRINGS.refreshFailed);
          console.error("[LoRArena] Refresh failed:", err);
        }
        item.textContent = STRINGS.refreshStatus;
        break;

      case "reset":
        if (!confirm(STRINGS.confirmReset)) return;
        item.textContent = STRINGS.resetting;
        try {
          const res = await fetch("/lorarena/api/checkpoints/reset-all", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          });
          const data = await res.json();
          if (res.ok) {
            alert(`${STRINGS.resetSuccess}: ${data.count} reset`);
          } else {
            throw new Error("Reset failed");
          }
        } catch (err) {
          alert(STRINGS.resetFailed);
          console.error("[LoRArena] Reset failed:", err);
        }
        item.textContent = STRINGS.resetElo;
        break;
    }
  });

  // Keyboard support for menu items
  menu.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      closeMenu();
      ball.focus();
      return;
    }
    const item = e.target.closest(".lorarena-menu-item");
    if (!item) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      item.click();
    }
  });

  loadPosition();
  document.body.appendChild(ball);
  document.body.appendChild(menu);
  console.log("[LoRArena] Floating ball added");
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
