# LoRA Arena (ComfyUI Custom Nodes)

An ELO-based evaluation system for Stable Diffusion LoRA checkpoints. Compare two LoRAs side-by-side with the same prompt and seed to scientifically determine which one performs better.

[中文说明 (README_CN.md)](./README_CN.md)

## Key Features

- **ELO Rating System**: Scientifically evaluate LoRA quality using the classic ELO algorithm.
- **Fair Comparison**: Generates two images with identical prompts and seeds; the only variable is the LoRA.
- **Random Matchmaking**: Automatic pair selection with stable random distribution.
- **Dynamic Prompting**: Randomly pick prompts from local directories, presets, or custom lists.
- **Pre-generation (Auto-Queue)**: Asynchronous generation flow to speed up the evaluation process.
- **In-Canvas Widgets**: Interactive voting and leaderboard widgets directly inside ComfyUI.
- **Localized UI**: Full support for both English and Chinese.

## Installation

1. Clone or download this repository into your ComfyUI `custom_nodes` folder:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/FHfanshu/comfyui-lora-arena
   ```
2. Install requirements:
   ```bash
   pip install -r comfyui-lora-arena/comfyui-lorarena/requirements.txt
   ```
3. Restart ComfyUI.

## Quick Start

1. **Load Workflow**: Import `comfyui-lorarena/examples/lorarena_battle_workflow.json` into ComfyUI.
2. **Scan LoRAs**: Use the `LoRArena Checkpoint Scanner` node to index your LoRA files.
3. **Configure**: Click the 🏆 button in the bottom-right corner to set your LoRA and prompt directories.
4. **Battle**: Click "Queue Prompt" to start a battle. Use the `Battle Display` widget to vote.
5. **Auto-Queue**: Enable "Pre-generate" in the settings to automatically queue the next battles after voting.

## Core Nodes

- **LoRArena Random LoRA Pair**: Randomly selects two LoRAs for comparison.
- **LoRArena Random Prompt**: Selects a random prompt from various sources.
- **LoRArena Battle Display**: Interactive widget for viewing images and casting votes.
- **LoRArena Leaderboard Display**: In-canvas widget showing real-time ELO rankings.
- **LoRArena Checkpoint Scanner**: Scans directories to add LoRAs to the evaluation database.

## License

MIT
