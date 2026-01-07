/**
 * LoRArena Leaderboard Display Widget - Shows LoRA rankings
 */
import { app } from "/scripts/app.js";

// Localization
const isZh = (navigator.language || "en").toLowerCase().startsWith("zh");
const LANG = {
    title: isZh ? "LoRA 排行榜" : "LoRA Leaderboard",
    refresh: isZh ? "刷新" : "Refresh",
    reset: isZh ? "重置" : "Reset",
    resetConfirm: isZh ? "确定要重置所有 LoRA 的统计数据吗？\n\n所有 ELO 评分将恢复为 1500，对战记录将清零。" : "Reset all LoRA stats?\n\nAll ELO ratings will be reset to 1500 and battle records cleared.",
    resetting: isZh ? "重置中..." : "Resetting...",
    resetSuccess: isZh ? "重置成功" : "Reset complete",
    resetFailed: isZh ? "重置失败" : "Reset failed",
    loading: isZh ? "加载中..." : "Loading...",
    noData: isZh ? "暂无排行。快去对战吧！" : "No LoRAs ranked yet. Start voting!",
    battles: isZh ? "场次" : "Battles",
    winRate: isZh ? "胜率" : "Win%",
    updated: isZh ? "已更新" : "Updated",
    dir: isZh ? "目录" : "Dir",
    name: isZh ? "名称" : "Name",
    loadFailed: isZh ? "加载排行榜失败" : "Failed to load leaderboard",
    loadFailedShort: isZh ? "加载失败" : "Failed to load",
};

app.registerExtension({
    name: "lorarena.leaderboard_display",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "LoRArenaLeaderboardDisplay") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            if (onNodeCreated) {
                onNodeCreated.apply(this, arguments);
            }

            const node = this;

            // Create container
            const container = document.createElement("div");
            container.style.cssText = `
                width: 100%;
                height: 100%;
                min-height: 400px;
                background: #1a1a2e;
                border-radius: 8px;
                overflow: hidden;
                position: relative;
                pointer-events: auto;
            `;

            // Create leaderboard content
            const content = this._createLeaderboardContent();
            container.appendChild(content);

            // Add DOM Widget
            this.addDOMWidget("leaderboard_display", "custom", container, {
                serialize: false,
                hideOnZoom: false,
                computeSize: function(width) {
                    return [width, Math.max(400, node.size[1] - 60)];
                }
            });

            this._leaderboardContainer = container;
            this._leaderboardContent = content;
            this.setSize([500, 500]);

            // Fetch initial data
            this._fetchLeaderboard();
            this._leaderboardPoll = setInterval(() => this._fetchLeaderboard(), 5000);

            console.log("[LoRArena] Leaderboard Display widget created");

            const originalOnRemoved = this.onRemoved;
            this.onRemoved = function() {
                if (this._leaderboardPoll) {
                    clearInterval(this._leaderboardPoll);
                    this._leaderboardPoll = null;
                }
                if (originalOnRemoved) {
                    originalOnRemoved.call(this);
                }
            };
        };

        // Create leaderboard content
        nodeType.prototype._createLeaderboardContent = function() {
            const content = document.createElement("div");
            content.style.cssText = `
                padding: 16px;
                height: 100%;
                overflow-y: auto;
                pointer-events: auto;
            `;

            // Title with refresh button
            const header = document.createElement("div");
            header.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            `;

            const title = document.createElement("div");
            title.style.cssText = `
                color: #fff;
                font-size: 16px;
                font-weight: bold;
            `;
            title.textContent = LANG.title;
            header.appendChild(title);

            // Button container for refresh and reset
            const btnContainer = document.createElement("div");
            btnContainer.style.cssText = `
                display: flex;
                gap: 8px;
            `;

            const refreshBtn = document.createElement("button");
            refreshBtn.style.cssText = `
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                background: #3b82f6;
                color: white;
                font-size: 12px;
                cursor: pointer;
                pointer-events: auto;
            `;
            refreshBtn.textContent = LANG.refresh;
            refreshBtn.onpointerdown = (e) => e.stopPropagation();
            refreshBtn.onmousedown = (e) => e.stopPropagation();
            refreshBtn.onclick = () => this._fetchLeaderboard(true);
            btnContainer.appendChild(refreshBtn);

            const resetBtn = document.createElement("button");
            resetBtn.style.cssText = `
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                background: #ef4444;
                color: white;
                font-size: 12px;
                cursor: pointer;
                pointer-events: auto;
            `;
            resetBtn.textContent = LANG.reset;
            resetBtn.onpointerdown = (e) => e.stopPropagation();
            resetBtn.onmousedown = (e) => e.stopPropagation();
            resetBtn.onclick = () => this._resetAllStats();
            btnContainer.appendChild(resetBtn);

            header.appendChild(btnContainer);

            content.appendChild(header);

            const status = document.createElement("div");
            status.style.cssText = `
                color: #9ca3af;
                font-size: 11px;
                margin-bottom: 12px;
            `;
            status.textContent = "Ready";
            content.appendChild(status);

            // Table container
            const tableContainer = document.createElement("div");
            tableContainer.className = "leaderboard-table";
            content.appendChild(tableContainer);

            this._tableContainer = tableContainer;
            this._statusLabel = status;
            this._refreshBtn = refreshBtn;
            this._resetBtn = resetBtn;
            return content;
        };

        // Reset all LoRA stats
        nodeType.prototype._resetAllStats = async function() {
            if (!confirm(LANG.resetConfirm)) {
                return;
            }

            if (this._resetBtn) {
                this._resetBtn.disabled = true;
                this._resetBtn.textContent = LANG.resetting;
            }
            if (this._statusLabel) {
                this._statusLabel.textContent = LANG.resetting;
            }

            try {
                const response = await fetch("/lorarena/api/checkpoints/reset-all", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                });
                const data = await response.json();

                if (response.ok && data.success) {
                    if (this._statusLabel) {
                        this._statusLabel.textContent = LANG.resetSuccess;
                    }
                    // Refresh leaderboard after reset
                    await this._fetchLeaderboard(true);
                } else {
                    throw new Error(data.error || "Unknown error");
                }
            } catch (error) {
                console.error("[LoRArena] Failed to reset stats:", error);
                if (this._statusLabel) {
                    this._statusLabel.textContent = LANG.resetFailed;
                }
            } finally {
                if (this._resetBtn) {
                    this._resetBtn.disabled = false;
                    this._resetBtn.textContent = LANG.reset;
                }
            }
        };

        // Fetch leaderboard data
        nodeType.prototype._fetchLeaderboard = async function(force = false) {
            const limitWidget = this.widgets?.find(w => w.name === "limit");
            const limitValue = limitWidget?.value ?? 20;
            if (this._statusLabel) {
                this._statusLabel.textContent = LANG.loading;
            }
            if (this._refreshBtn) {
                this._refreshBtn.disabled = true;
                this._refreshBtn.textContent = LANG.loading;
            }
            try {
                let loraDirectory = "";
                try {
                    const configRes = await fetch("/lorarena/api/config");
                    if (configRes.ok) {
                        const config = await configRes.json();
                        loraDirectory = (config?.lora_directory || "").toString().trim();
                    }
                } catch (err) {
                    // ignore config fetch errors
                }

                const params = new URLSearchParams();
                params.set("limit", String(limitValue));
                if (loraDirectory) {
                    params.set("lora_directory", loraDirectory);
                }
                const response = await fetch(`/lorarena/api/leaderboard?${params.toString()}`);
                const data = await response.json();
                this._renderLeaderboard(data.items || []);
                if (this._statusLabel) {
                    if (force) {
                        this._statusLabel.textContent = LANG.updated;
                    } else if (loraDirectory) {
                        this._statusLabel.textContent = `${LANG.dir}: ${loraDirectory}`;
                    } else {
                        this._statusLabel.textContent = "";
                    }
                }
            } catch (error) {
                console.error("[LoRArena] Failed to fetch leaderboard:", error);
                this._tableContainer.innerHTML = `
                    <div style="color: #ef4444; text-align: center; padding: 20px;">
                        ${LANG.loadFailed}
                    </div>
                `;
                if (this._statusLabel) {
                    this._statusLabel.textContent = LANG.loadFailedShort;
                }
            } finally {
                if (this._refreshBtn) {
                    this._refreshBtn.disabled = false;
                    this._refreshBtn.textContent = LANG.refresh;
                }
            }
        };

        // Format LoRA name to prioritize showing the end (usually contains version numbers)
        nodeType.prototype._formatLoraName = function(name) {
            // Remove file extension if present
            let displayName = name.replace(/\.(safetensors|ckpt|pt)$/i, "");
            return displayName;
        };

        // Render leaderboard table
        nodeType.prototype._renderLeaderboard = function(items) {
            if (!items.length) {
                this._tableContainer.innerHTML = `
                    <div style="color: #888; text-align: center; padding: 20px;">
                        ${LANG.noData}
                    </div>
                `;
                return;
            }

            let html = `
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead>
                        <tr style="color: #888; border-bottom: 1px solid #333;">
                            <th style="padding: 8px; text-align: left;">#</th>
                            <th style="padding: 8px; text-align: left;">${LANG.name}</th>
                            <th style="padding: 8px; text-align: right;">ELO</th>
                            <th style="padding: 8px; text-align: right;">${LANG.battles}</th>
                            <th style="padding: 8px; text-align: right;">${LANG.winRate}</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            items.forEach((item, idx) => {
                const rankColor = idx === 0 ? "#ffd700" : idx === 1 ? "#c0c0c0" : idx === 2 ? "#cd7f32" : "#fff";
                const displayName = this._formatLoraName(item.name);
                const eloRounded = Math.round(item.elo_rating);
                // Apply strikethrough style for eliminated LoRAs in Battle Royale mode
                const eliminatedStyle = item.eliminated
                    ? "text-decoration: line-through; opacity: 0.5;"
                    : "";
                const eliminatedTitle = item.eliminated
                    ? ` (${isZh ? "已淘汰" : "Eliminated"})`
                    : "";
                html += `
                    <tr style="color: #ddd; border-bottom: 1px solid #222; ${eliminatedStyle}">
                        <td style="padding: 8px; color: ${rankColor}; font-weight: bold;">${item.rank}</td>
                        <td style="padding: 8px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; direction: rtl; text-align: left;" title="${item.name}${eliminatedTitle}">${displayName}</td>
                        <td style="padding: 8px; text-align: right; color: #3b82f6;">${eloRounded}</td>
                        <td style="padding: 8px; text-align: right;">${item.total_battles}</td>
                        <td style="padding: 8px; text-align: right; color: ${item.win_rate >= 0.5 ? '#22c55e' : '#ef4444'};">${(item.win_rate * 100).toFixed(1)}%</td>
                    </tr>
                `;
            });

            html += "</tbody></table>";
            this._tableContainer.innerHTML = html;
        };

        // Refresh on execute
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(output) {
            if (onExecuted) {
                onExecuted.call(this, output);
            }
            this._fetchLeaderboard();
        };
    }
});
