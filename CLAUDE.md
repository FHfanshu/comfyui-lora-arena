# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRA Arena is an ELO-based LoRA checkpoint evaluation system for ComfyUI. It generates comparison images using identical prompts and seeds, with the LoRA being the only variable. Users vote on which image is better, and the system updates ELO ratings accordingly.

## Installation

```bash
pip install -r requirements.txt
# Symlink or copy this folder to ComfyUI's custom_nodes/ directory
# Restart ComfyUI to load the extension
```

## Architecture

### Entry Point (`__init__.py`)
- Registers all nodes via `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`
- Auto-detects locale for Chinese/English UI
- Registers REST API routes on `PromptServer.instance.routes` (endpoints prefixed `/lorarena/api/`)
- Sets `WEB_DIRECTORY = "web/js"` for frontend widgets

### Nodes (`nodes/`)
| Node | Purpose |
|------|---------|
| `matchmaker.py` | Selects two LoRAs for battle using strategies (random, balanced, exploration) |
| `battle_generator.py` | Creates battle record and triggers dual-LoRA image generation |
| `battle_display.py` | In-canvas widget showing both images with voting buttons |
| `leaderboard_display.py` | In-canvas widget showing ELO rankings |
| `random_lora_pair.py` | Outputs two random LoRA filenames for workflow use |
| `random_prompt.py` | Selects prompts from directories, presets, or custom lists |
| `checkpoint_scanner.py` | Scans directories and registers LoRAs in database |
| `lora_loader.py` | Loads LoRA by filename string (vs standard ComfyUI dropdown) |
| `panel_node.py` | Receives model/clip/vae from CheckpointLoader for internal generation |
| `vote_recorder.py` | Records vote result and updates battle status |

### Services (`services/`)
| Service | Responsibility |
|---------|----------------|
| `database.py` | SQLAlchemy session manager; SQLite at `data/lorarena.db` |
| `models.py` | ORM models: `Checkpoint`, `Battle`, `ELOHistory` |
| `elo_service.py` | ELO calculation with dynamic K-factor based on battle count |
| `matchmaking_service.py` | Opponent selection with Battle Royale filtering |
| `battle_service.py` | Battle lifecycle: create, update status, submit votes |
| `checkpoint_service.py` | CRUD and scanning for LoRA checkpoints |
| `battle_state.py` | Global singleton holding current battle for widget access |
| `model_state.py` | Tracks model/clip/vae loaded by Panel Node |
| `comfyui_generator.py` | Internal image generation using ComfyUI execution APIs |
| `training_data_service.py` | Handles training data directory scanning |

### Frontend (`web/js/`)
- `lorarena_extension.js`: Registers extension, adds 🏆 launcher button, manages config panel
- `battle_display_widget.js`: Voting UI rendered directly in ComfyUI canvas
- `leaderboard_display_widget.js` / `leaderboard_widget.js`: ELO ranking display
- `panel_widget.js`: Panel node widget
- `voting_widget.js`: Shared voting button components

### Key Data Flow
1. **Setup**: `CheckpointScanner` indexes LoRA files into SQLite
2. **Matchmaking**: `Matchmaker` selects two LoRAs based on strategy
3. **Generation**: `BattleGenerator` creates pending battle, generates images with identical seed/prompt
4. **Voting**: `BattleDisplay` widget shows images, user votes via API
5. **ELO Update**: Vote processed, ratings recalculated, history recorded

### REST API Endpoints (registered in `__init__.py`)
Key endpoints:
- `GET /lorarena/api/leaderboard` - Rankings with optional filtering
- `POST /lorarena/api/battles/new` - Create new battle with generation
- `POST /lorarena/api/battles/{id}/vote` - Submit vote
- `GET/PUT /lorarena/api/config` - Configuration management
- `POST /lorarena/api/checkpoints/scan` - Trigger directory scan
- `GET /lorarena/api/node/battle/current` - Current battle for widgets

## Configuration

`data/config.json` (created on first run):
- `lora_directory`: Path to LoRA files (relative to ComfyUI's lora folder)
- `base_model`: Stable Diffusion checkpoint filename
- `steps`, `cfg_scale`, `sampler`, `scheduler`: Generation parameters
- `lora_strength`: LoRA application strength (default 0.8)
- `width`, `height`: Image dimensions
- `battle_royale_enabled`, `battle_royale_threshold`, `battle_royale_win_rate`: Elimination mode
- `auto_queue_enabled`, `auto_queue_count`: Auto-queue after voting

## Coding Conventions

- **Python**: PEP 8, 4-space indentation
- **JavaScript**: ComfyUI widget patterns; widgets communicate via `/lorarena/api/` endpoints
- **Database**: Synchronous SQLAlchemy with `session_scope()` context manager

## Testing

No automated test suite. Validate changes by:
1. Installing extension in ComfyUI's `custom_nodes/` directory
2. Loading the example workflow from `examples/`
3. Testing node connections and voting flow
