# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRA Arena is an ELO-based LoRA checkpoint evaluation system for ComfyUI. It generates comparison images and lets users vote to determine which LoRA produces better results. The system uses the same seed/prompt for both images, with the LoRA being the only variable.

## Installation

```bash
pip install -r comfyui-lorarena/requirements.txt
# Symlink or copy comfyui-lorarena/ to ComfyUI's custom_nodes/ directory
# Restart ComfyUI to load the extension
```

## Architecture

### ComfyUI Extension (`comfyui-lorarena/`)
- `__init__.py`: Node registration (`NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`) and API route registration on `PromptServer.instance.routes`
- `nodes/`: ComfyUI node implementations
  - `battle_display.py`, `leaderboard_display.py`: Nodes with in-canvas widget UI
  - `random_lora_pair.py`, `random_prompt.py`: Random selection nodes
  - `lora_loader.py`, `checkpoint_scanner.py`: LoRA management nodes
  - `vote_recorder.py`, `battle_generator.py`: Battle workflow nodes
  - `panel_node.py`: Receives model/clip/vae from CheckpointLoader
- `services/`: Business logic
  - `database.py`: Synchronous SQLAlchemy session (SQLite at `data/lorarena.db`)
  - `battle_service.py`, `checkpoint_service.py`: Core domain services
  - `elo_service.py`: ELO rating calculation
  - `matchmaking_service.py`: Opponent selection strategies
  - `battle_state.py`: Global state for current battle accessed by web widgets
  - `model_state.py`: Tracks loaded model/clip/vae for Panel Node
  - `comfyui_generator.py`: Internal image generation using ComfyUI execution APIs
- `web/js/`: JavaScript widgets for in-canvas node UI
- `data/`: Runtime data (SQLite DB, config.json)

### Key Data Flow
1. **Battle Creation**: Matchmaking selects two LoRAs → Battle record created → Generation triggered
2. **Image Generation**: ComfyUI workflow built with dual LoRA branches → Images saved
3. **Voting**: User votes → ELO ratings updated → ELO history recorded
4. **Battle Royale**: LoRAs with low win rate after threshold battles are excluded from matchmaking

## Configuration

`comfyui-lorarena/data/config.json`:
- `lora_directory`: Path to LoRA files (relative to ComfyUI's lora folder)
- `base_model`: Stable Diffusion checkpoint filename
- `battle_royale_enabled`, `battle_royale_threshold`, `battle_royale_win_rate`: Elimination mode settings
- `auto_queue_enabled`, `auto_queue_count`: Auto-queue settings

## Coding Conventions

- **Python**: PEP 8, 4-space indentation
- **JavaScript**: ComfyUI widget patterns in `web/js/`
- **Naming**: Domain-focused (e.g., `battle_service`, `matchmaking_service`)

## Testing

No automated test suite. Validate changes by installing extension in ComfyUI and testing node workflows.
