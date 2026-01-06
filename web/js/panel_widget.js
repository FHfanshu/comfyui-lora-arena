/**
 * LoRArena Panel Widget - Embeds React Arena UI in a ComfyUI node
 */
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "lorarena.panel",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "LoRArenaPanelNode") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            if (onNodeCreated) {
                onNodeCreated.apply(this, arguments);
            }

            const node = this;

            // Lightweight placeholder (full-page panel removed)
            const container = document.createElement("div");
            container.style.cssText = `
                width: 100%;
                height: 100%;
                min-height: 200px;
                background: #0f1115;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #9ca3af;
                font-size: 13px;
                padding: 16px;
                text-align: center;
            `;
            container.textContent = "LoRArena full-page panel has been disabled. Use the hover settings button instead.";

            // Add DOM Widget to node with dynamic sizing
            const widget = this.addDOMWidget("arena_panel", "custom", container, {
                serialize: false,
                hideOnZoom: false,
                // Compute size dynamically based on node size
                computeSize: function(width) {
                    // Leave room for inputs/outputs and title
                    const headerHeight = 30;
                    const inputsHeight = Math.max((node.inputs?.length || 0) * 20, 60);
                    const minHeight = 400;
                    // Return width and calculated height
                    return [width, Math.max(minHeight, node.size[1] - headerHeight - inputsHeight - 40)];
                }
            });

            this._arenaContainer = container;

            // Set initial node size
            this.setSize([520, 260]);

            // Handle node resize - update container dimensions
            const originalOnResize = this.onResize;
            this.onResize = function(size) {
                // Enforce minimum size
                if (size[0] < 500) size[0] = 500;
                if (size[1] < 400) size[1] = 400;

                // Call original if exists
                if (originalOnResize) {
                    originalOnResize.call(this, size);
                }

                // Update widget size
                if (widget && widget.computeSize) {
                    const newSize = widget.computeSize(size[0]);
                    container.style.height = `${newSize[1]}px`;
                }
            };

            console.log("[LoRArena] Panel widget created");
        };

        // Custom drawing to show status - check actual execution state
        const onDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function(ctx) {
            if (onDrawForeground) {
                onDrawForeground.apply(this, arguments);
            }

            // Draw status based on connection AND execution
            if (this.inputs && this.inputs.length > 0) {
                const allConnected = this.inputs.every(input => input.link !== null);
                // Check if node has been executed (has output data)
                const hasBeenExecuted = this.is_executed === true;

                let statusColor, statusText;
                if (allConnected && hasBeenExecuted) {
                    statusColor = "#22c55e";
                    statusText = "✓ Ready";
                } else if (allConnected) {
                    statusColor = "#f59e0b";
                    statusText = "⚡ Run Queue";
                } else {
                    statusColor = "#ef4444";
                    statusText = "⚠ Connect model";
                }

                ctx.font = "12px Arial";
                ctx.fillStyle = statusColor;
                ctx.textAlign = "right";
                ctx.fillText(statusText, this.size[0] - 10, -8);
            }
        };

        // Track when node is executed
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(output) {
            this.is_executed = true;
            if (onExecuted) {
                onExecuted.call(this, output);
            }
            // No iframe to refresh
        };
    }
});
