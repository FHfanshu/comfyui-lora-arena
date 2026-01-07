/**
 * LoRArena Battle Display Widget - Shows A/B comparison images for voting
 */
import { app } from "/scripts/app.js";

// Localization
const LANG = (() => {
    const lang = navigator.language || "en";
    const isZh = lang.toLowerCase().startsWith("zh");
    return {
        title: isZh ? "LoRA 对战 - 选择更好的图片" : "LoRA Battle - Vote for the better image",
        loraA: "LoRA A",
        loraB: "LoRA B",
        aBetter: isZh ? "A 更好" : "A is Better",
        bBetter: isZh ? "B 更好" : "B is Better",
        tie: isZh ? "平局" : "Tie",
        skip: isZh ? "跳过" : "Skip",
        noActiveBattle: isZh ? "没有进行中的对战" : "No active battle.",
        submitting: isZh ? "提交中..." : "Submitting vote...",
        voted: isZh ? "已投票" : "Voted",
        voteRejected: isZh ? "投票被拒绝" : "Vote rejected.",
        voteFailed: isZh ? "投票失败" : "Vote failed.",
        winnerA: isZh ? "LoRA A ✓ 胜出" : "LoRA A ✓ Winner",
        winnerB: isZh ? "LoRA B ✓ 胜出" : "LoRA B ✓ Winner",
        tieA: isZh ? "LoRA A - 平局" : "LoRA A - Tie",
        tieB: isZh ? "LoRA B - 平局" : "LoRA B - Tie",
        noBattleYet: isZh ? "暂无对战。请运行节点。" : "No battle yet. Run the node.",
        readyMissingImages: isZh ? "对战已准备好，但图片丢失。" : "Battle ready, images missing.",
        failedFetch: isZh ? "获取对战数据失败。" : "Failed to fetch battle data.",
    };
})();

app.registerExtension({
    name: "lorarena.battle_display",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "LoRArenaBattleDisplay") {
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
                min-height: 500px;
                background: #1a1a2e;
                border-radius: 8px;
                overflow: hidden;
                position: relative;
                display: flex;
                flex-direction: column;
                pointer-events: auto;
            `;

            // CRITICAL: Stop event propagation to prevent LiteGraph from intercepting
            const stopPropagation = (e) => {
                e.stopPropagation();
            };
            container.addEventListener("mousedown", stopPropagation);
            container.addEventListener("mouseup", stopPropagation);
            container.addEventListener("click", stopPropagation);
            container.addEventListener("dblclick", stopPropagation);
            container.addEventListener("pointerdown", stopPropagation);
            container.addEventListener("pointerup", stopPropagation);

            // Create battle display area
            const battleArea = this._createBattleArea();
            container.appendChild(battleArea);

            // Add DOM Widget
            const widget = this.addDOMWidget("battle_display", "custom", container, {
                serialize: false,
                hideOnZoom: false,
                computeSize: function(width) {
                    return [width, Math.max(500, node.size[1] - 100)];
                }
            });

            this._battleContainer = container;
            this._battleArea = battleArea;
            this.setSize([800, 600]);

            // Handle resize
            const originalOnResize = this.onResize;
            this.onResize = function(size) {
                if (size[0] < 600) size[0] = 600;
                if (size[1] < 500) size[1] = 500;
                if (originalOnResize) {
                    originalOnResize.call(this, size);
                }
            };

            console.log("[LoRArena] Battle Display widget created");
            setTimeout(() => this._fetchBattleData(), 200);
            this._battlePoll = setInterval(() => this._fetchBattleData(), 1500);

            const originalOnRemoved = this.onRemoved;
            this.onRemoved = function() {
                if (this._battlePoll) {
                    clearInterval(this._battlePoll);
                    this._battlePoll = null;
                }
                if (originalOnRemoved) {
                    originalOnRemoved.call(this);
                }
            };
        };

        // Create battle display area
        nodeType.prototype._createBattleArea = function() {
            const area = document.createElement("div");
            area.style.cssText = `
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 8px;
                gap: 4px;
                min-height: 0;
            `;

            // Title
            const title = document.createElement("div");
            title.style.cssText = `
                text-align: center;
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                flex-shrink: 0;
            `;
            title.textContent = LANG.title;
            area.appendChild(title);

            // Status + refresh
            const statusBar = document.createElement("div");
            statusBar.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
                color: #9ca3af;
                font-size: 11px;
                flex-shrink: 0;
            `;
            const statusText = document.createElement("span");
            statusText.textContent = "Waiting for images...";
            const refreshBtn = document.createElement("button");
            refreshBtn.textContent = "Refresh";
            refreshBtn.style.cssText = `
                padding: 4px 10px;
                border: 1px solid #374151;
                border-radius: 6px;
                background: #111827;
                color: #e5e7eb;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.15s ease;
                pointer-events: auto;
            `;
            refreshBtn.addEventListener("mouseenter", () => {
                refreshBtn.style.background = "#1f2937";
                refreshBtn.style.borderColor = "#4b5563";
            });
            refreshBtn.addEventListener("mouseleave", () => {
                refreshBtn.style.background = "#111827";
                refreshBtn.style.borderColor = "#374151";
            });
            refreshBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                e.preventDefault();
                this._fetchBattleData(true);
            });
            refreshBtn.addEventListener("mousedown", (e) => e.stopPropagation());
            refreshBtn.addEventListener("pointerdown", (e) => e.stopPropagation());
            statusBar.appendChild(statusText);
            statusBar.appendChild(refreshBtn);
            area.appendChild(statusBar);

            // Images container - takes all remaining space
            const imagesContainer = document.createElement("div");
            imagesContainer.style.cssText = `
                flex: 1;
                display: flex;
                gap: 8px;
                justify-content: center;
                align-items: stretch;
                min-height: 0;
                position: relative;
            `;

            // Image A
            const imageAWrapper = this._createImageWrapper("A");
            imagesContainer.appendChild(imageAWrapper);

            // VS divider - positioned absolutely in center
            const vs = document.createElement("div");
            vs.style.cssText = `
                position: absolute;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
                color: #f59e0b;
                font-size: 20px;
                font-weight: bold;
                text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                z-index: 10;
                pointer-events: none;
            `;
            vs.textContent = "VS";
            imagesContainer.appendChild(vs);

            // Image B
            const imageBWrapper = this._createImageWrapper("B");
            imagesContainer.appendChild(imageBWrapper);

            area.appendChild(imagesContainer);

            // Voting buttons
            const buttonsContainer = this._createVotingButtons();
            area.appendChild(buttonsContainer);

            // Store references
            this._imageA = imageAWrapper.querySelector("img");
            this._imageB = imageBWrapper.querySelector("img");
            this._labelA = imageAWrapper.querySelector(".lora-label");
            this._labelB = imageBWrapper.querySelector(".lora-label");
            this._statusText = statusText;
            this._hasBattle = false;
            this._currentBattleId = null;

            return area;
        };

        // Create image wrapper
        nodeType.prototype._createImageWrapper = function(label) {
            const wrapper = document.createElement("div");
            wrapper.style.cssText = `
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
                min-width: 0;
                min-height: 0;
            `;

            const imgContainer = document.createElement("div");
            imgContainer.style.cssText = `
                flex: 1;
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                background: #0f0f1a;
                border-radius: 8px;
                border: 2px solid #333;
                overflow: hidden;
                min-height: 0;
            `;

            const img = document.createElement("img");
            img.style.cssText = `
                max-width: 100%;
                max-height: 100%;
                width: auto;
                height: auto;
                object-fit: contain;
                display: block;
            `;
            img.src = "";
            imgContainer.appendChild(img);
            wrapper.appendChild(imgContainer);

            const labelDiv = document.createElement("div");
            labelDiv.className = "lora-label";
            labelDiv.style.cssText = `
                color: #888;
                font-size: 12px;
                text-align: center;
                width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-family: monospace;
                flex-shrink: 0;
            `;
            labelDiv.textContent = `LoRA ${label}`;
            wrapper.appendChild(labelDiv);

            // Store ref to container for border styling
            wrapper._imgContainer = imgContainer;

            return wrapper;
        };

        // Create voting buttons
        nodeType.prototype._createVotingButtons = function() {
            const self = this;
            const container = document.createElement("div");
            container.style.cssText = `
                display: flex;
                justify-content: center;
                gap: 12px;
                padding: 8px 0;
                flex-shrink: 0;
            `;

            const buttons = [
                { label: LANG.aBetter, value: "a", color: "rgba(59, 130, 246, 0.2)", borderColor: "rgba(59, 130, 246, 0.5)", hoverColor: "rgba(59, 130, 246, 0.4)" },
                { label: LANG.tie, value: "tie", color: "rgba(107, 114, 128, 0.2)", borderColor: "rgba(107, 114, 128, 0.5)", hoverColor: "rgba(107, 114, 128, 0.4)" },
                { label: LANG.bBetter, value: "b", color: "rgba(34, 197, 94, 0.2)", borderColor: "rgba(34, 197, 94, 0.5)", hoverColor: "rgba(34, 197, 94, 0.4)" },
                { label: LANG.skip, value: "skip", color: "rgba(239, 68, 68, 0.2)", borderColor: "rgba(239, 68, 68, 0.5)", hoverColor: "rgba(239, 68, 68, 0.4)" },
            ];

            this._voteButtons = [];
            buttons.forEach(btn => {
                const button = document.createElement("button");
                button.style.cssText = `
                    padding: 12px 28px;
                    border: 1px solid ${btn.borderColor};
                    border-radius: 12px;
                    background: ${btn.color};
                    color: white;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    backdrop-filter: blur(8px);
                    -webkit-backdrop-filter: blur(8px);
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    pointer-events: auto;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
                    min-width: 100px;
                `;
                button.textContent = btn.label;

                // Hover effects
                button.addEventListener("mouseenter", () => {
                    if (!button.disabled) {
                        button.style.background = btn.hoverColor;
                        button.style.transform = "translateY(-2px)";
                        button.style.boxShadow = "0 6px 12px rgba(0, 0, 0, 0.2)";
                        button.style.borderColor = btn.borderColor.replace("0.5", "0.8");
                    }
                });
                button.addEventListener("mouseleave", () => {
                    button.style.background = btn.color;
                    button.style.transform = "translateY(0)";
                    button.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
                    button.style.borderColor = btn.borderColor;
                });

                // Click with animation
                button.addEventListener("click", (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    if (button.disabled) return;

                    // Click animation
                    button.style.transform = "scale(0.95)";
                    setTimeout(() => {
                        button.style.transform = "translateY(0)";
                    }, 100);

                    self._submitVote(btn.value);
                });

                // Prevent event bubbling
                button.addEventListener("mousedown", (e) => e.stopPropagation());
                button.addEventListener("pointerdown", (e) => e.stopPropagation());

                container.appendChild(button);
                this._voteButtons.push({ element: button, config: btn });
            });

            return container;
        };

        nodeType.prototype._setVotingEnabled = function(enabled) {
            if (!this._voteButtons) return;
            this._voteButtons.forEach(({ element: btn, config }) => {
                btn.disabled = !enabled;
                btn.style.opacity = enabled ? "1" : "0.5";
                btn.style.cursor = enabled ? "pointer" : "not-allowed";
                btn.style.background = config.color;
            });
        };

        // Submit vote
        nodeType.prototype._submitVote = async function(winner) {
            try {
                if (!this._hasBattle) {
                    if (this._statusText) {
                        this._statusText.textContent = LANG.noActiveBattle;
                    }
                    return;
                }

                this._setVotingEnabled(false);
                if (this._statusText) {
                    this._statusText.textContent = LANG.submitting;
                }

                const response = await fetch("/lorarena/api/node/battle/vote", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ winner }),
                });
                let data = null;
                const contentType = response.headers.get("content-type") || "";
                if (contentType.includes("application/json")) {
                    data = await response.json();
                } else {
                    const text = await response.text();
                    throw new Error(text || `HTTP ${response.status}`);
                }

                if (data.success) {
                    console.log("[LoRArena] Vote submitted:", winner);
                    this._showVoteResult(winner);
                    if (this._statusText) {
                        this._statusText.textContent = `${LANG.voted}: ${winner.toUpperCase()}`;
                    }

                    // Smart auto-queue if enabled
                    if (data.auto_queue_enabled) {
                        const target = data.auto_queue_target || 30;
                        const max = data.auto_queue_max || 100;
                        console.log(`[LoRArena] Smart auto-queue: target=${target}, max=${max}`);
                        setTimeout(() => {
                            this._autoQueuePrompts(target, max);
                        }, 500);
                    }
                } else {
                    if (this._statusText) {
                        this._statusText.textContent = data.error || LANG.voteRejected;
                    }
                    this._setVotingEnabled(true);
                }
            } catch (error) {
                console.error("[LoRArena] Vote failed:", error);
                if (this._statusText) {
                    this._statusText.textContent = LANG.voteFailed;
                }
                this._setVotingEnabled(true);
            }
        };

        // Show vote result with animation
        nodeType.prototype._showVoteResult = function(winner) {
            const loraNameA = this._loraNameA || "LoRA A";
            const loraNameB = this._loraNameB || "LoRA B";

            // Add winner highlight animation
            if (winner === "a" && this._imageA && this._imageA.parentNode) {
                const container = this._imageA.parentNode;
                container.style.transition = "all 0.3s ease";
                container.style.border = "3px solid #22c55e";
                container.style.boxShadow = "0 0 20px rgba(34, 197, 94, 0.5)";

                if (this._labelA) {
                    this._labelA.style.color = "#22c55e";
                    this._labelA.style.fontWeight = "bold";
                    this._labelA.textContent = `${loraNameA} ✓`;
                    this._labelA.title = loraNameA;
                }

                // Show loser name too but dimmed
                if (this._labelB) {
                    this._labelB.textContent = loraNameB;
                    this._labelB.title = loraNameB;
                }

                if (this._imageB && this._imageB.parentNode) {
                    this._imageB.parentNode.style.opacity = "0.5";
                }
            } else if (winner === "b" && this._imageB && this._imageB.parentNode) {
                const container = this._imageB.parentNode;
                container.style.transition = "all 0.3s ease";
                container.style.border = "3px solid #22c55e";
                container.style.boxShadow = "0 0 20px rgba(34, 197, 94, 0.5)";

                if (this._labelB) {
                    this._labelB.style.color = "#22c55e";
                    this._labelB.style.fontWeight = "bold";
                    this._labelB.textContent = `${loraNameB} ✓`;
                    this._labelB.title = loraNameB;
                }

                // Show loser name too but dimmed
                if (this._labelA) {
                    this._labelA.textContent = loraNameA;
                    this._labelA.title = loraNameA;
                }

                if (this._imageA && this._imageA.parentNode) {
                    this._imageA.parentNode.style.opacity = "0.5";
                }
            } else if (winner === "tie") {
                if (this._labelA) {
                    this._labelA.style.color = "#f59e0b";
                    this._labelA.textContent = `${loraNameA} (=)`;
                    this._labelA.title = loraNameA;
                }
                if (this._labelB) {
                    this._labelB.style.color = "#f59e0b";
                    this._labelB.textContent = `${loraNameB} (=)`;
                    this._labelB.title = loraNameB;
                }
            }
        };

        // Smart auto-queue prompts for pre-generation
        // target: desired queue depth, max: never exceed this
        nodeType.prototype._autoQueuePrompts = async function(target, max) {
            try {
                // Use ComfyUI's API to check current queue depth
                const app = window.app;
                if (!app || !app.queuePrompt) {
                    console.warn("[LoRArena] ComfyUI app.queuePrompt not available");
                    return;
                }

                // Get current queue status
                let currentQueueSize = 0;
                try {
                    const queueData = await app.api.getQueue();
                    const running = queueData.queue_running?.length || 0;
                    const pending = queueData.queue_pending?.length || 0;
                    currentQueueSize = running + pending;
                } catch (err) {
                    console.warn("[LoRArena] Could not get queue status:", err);
                }

                // Calculate how many to queue
                if (currentQueueSize >= max) {
                    console.log(`[LoRArena] Queue already at max (${currentQueueSize}/${max}), skipping`);
                    return;
                }

                const needed = Math.max(0, Math.min(target - currentQueueSize, max - currentQueueSize));
                if (needed <= 0) {
                    console.log(`[LoRArena] Queue at target (${currentQueueSize}/${target}), no need to add more`);
                    return;
                }

                console.log(`[LoRArena] Smart queue: current=${currentQueueSize}, adding ${needed} (target=${target}, max=${max})`);
                for (let i = 0; i < needed; i++) {
                    await app.queuePrompt(0, 1);  // queue at front, batch size 1
                }
                console.log(`[LoRArena] Queued ${needed} prompts successfully`);
            } catch (error) {
                console.error("[LoRArena] Auto-queue failed:", error);
            }
        };

        // Reset image styles to default (clear vote result highlights)
        nodeType.prototype._resetImageStyles = function() {
            if (this._imageA && this._imageA.parentNode) {
                const container = this._imageA.parentNode;
                container.style.transition = "";
                container.style.border = "2px solid #333";
                container.style.boxShadow = "";
                container.style.opacity = "1";
            }
            if (this._imageB && this._imageB.parentNode) {
                const container = this._imageB.parentNode;
                container.style.transition = "";
                container.style.border = "2px solid #333";
                container.style.boxShadow = "";
                container.style.opacity = "1";
            }
            if (this._labelA) {
                this._labelA.style.color = "#888";
                this._labelA.style.fontWeight = "normal";
            }
            if (this._labelB) {
                this._labelB.style.color = "#888";
                this._labelB.style.fontWeight = "normal";
            }
        };

        // Update images when node is executed
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(output) {
            if (onExecuted) {
                onExecuted.call(this, output);
            }
            // Fetch current battle data after a short delay
            setTimeout(() => this._fetchBattleData(), 200);
        };

        // Fetch battle data from API
        nodeType.prototype._fetchBattleData = async function(force = false) {
            try {
                const response = await fetch("/lorarena/api/node/battle/current");
                const data = await response.json();
                const hasImages = !!(data.image_a && data.image_b);

                // Store LoRA names for reveal
                this._loraNameA = data.lora_name_a;
                this._loraNameB = data.lora_name_b;

                if (this._statusText) {
                    if (hasImages) {
                        this._statusText.textContent = "";
                    } else if (!data.has_battle) {
                        this._statusText.textContent = LANG.noBattleYet;
                    } else {
                        this._statusText.textContent = LANG.readyMissingImages;
                    }
                }
                this._hasBattle = !!(data.has_battle && hasImages);
                this._setVotingEnabled(this._hasBattle);

                // Check if this is a new battle (different battle_id or not voted yet)
                const isNewBattle = data.battle_id !== this._currentBattleId;
                const shouldResetStyles = isNewBattle && !data.voted;

                if (hasImages || data.has_battle || force) {
                    // Reset styles only when loading a NEW battle that hasn't been voted on
                    if (shouldResetStyles) {
                        this._resetImageStyles();
                        this._currentBattleId = data.battle_id;
                    }
                    if (this._imageA) this._imageA.src = data.image_a || "";
                    if (this._imageB) this._imageB.src = data.image_b || "";

                    // Only mask names if not voted yet
                    if (!data.voted) {
                        if (this._labelA) this._labelA.textContent = LANG.loraA;
                        if (this._labelB) this._labelB.textContent = LANG.loraB;
                    } else if (data.winner) {
                        // Restore winner display if already voted
                        this._showVoteResult(data.winner);
                    }
                } else {
                    if (this._imageA) this._imageA.src = "";
                    if (this._imageB) this._imageB.src = "";
                }
            } catch (error) {
                if (this._statusText) {
                    this._statusText.textContent = LANG.failedFetch;
                }
                console.error("[LoRArena] Failed to fetch battle data:", error);
            }
        };
    }
});
