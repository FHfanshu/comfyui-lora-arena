# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRA Arena is an ELO-based evaluation system for Stable Diffusion LoRA checkpoints in ComfyUI. It generates comparison images using identical prompts and seeds with only the LoRA varying, then updates ELO ratings based on user votes.

## Installation

```bash
pip install -r requirements.txt
# Link or copy this folder to ComfyUI/custom_nodes/
# Restart ComfyUI
```

## Architecture

### Entry Point (`__init__.py`)
- Registers all nodes via `NODE_CLASS_MAPPINGS`
- Auto-detects locale (Chinese/English) for UI display names
- Registers REST API routes on `PromptServer.instance.routes` (prefix `/lorarena/api/`)
- `WEB_DIRECTORY = "web/js"` serves frontend widgets

### Nodes (`nodes/`)
| Node | Purpose |
|------|---------|
| `matchmaker.py` | Selects two LoRAs for battle (source: database or directory scan) |
| `battle_generator.py` | Creates battle record and generates images for both LoRAs |
| `battle_display.py` | In-canvas image display with voting buttons |
| `leaderboard_display.py` | In-canvas ELO leaderboard (supports `min_battles` filter) |
| `elo_display.py` | Shows single checkpoint ELO statistics |
| `random_prompt.py` | Selects prompts from presets/training_data directory/custom lists |
| `checkpoint_scanner.py` | Scans directories and registers LoRAs to database |
| `lora_loader.py` | Loads LoRA by string path (not dropdown) |
| `panel_node.py` | Receives model/clip/vae from CheckpointLoader |
| `vote_recorder.py` | Records votes and updates battle status |
| `battle_types.py` | Battle data type definitions |

### Services (`services/`)
| Service | Responsibility |
|---------|----------------|
| `database.py` | SQLAlchemy session management; SQLite at `data/lorarena.db` |
| `models.py` | ORM models: `Checkpoint`, `Battle`, `ELOHistory` |
| `elo_service.py` | Dynamic K-factor ELO calculation |
| `matchmaking_service.py` | Opponent selection with Battle Royale elimination filter |
| `battle_service.py` | Battle lifecycle management |
| `checkpoint_service.py` | LoRA checkpoint CRUD and directory scanning |
| `battle_state.py` | Global state for current battle |
| `model_state.py` | Panel Node model/clip/vae state |
| `comfyui_generator.py` | Internal image generation via ComfyUI API |
| `training_data_service.py` | Training data directory scanning |

### Frontend (`web/js/`)
- `lorarena_extension.js` - Registers extension, adds launch button, manages config panel
- `battle_display_widget.js` - In-canvas voting UI
- `leaderboard_display_widget.js` - ELO leaderboard display
- `panel_widget.js` - Panel node widget
- `voting_widget.js` - Shared voting button component

### Data Flow
1. **Initialize**: `CheckpointScanner` indexes LoRA files into SQLite
2. **Match**: `Matchmaker` selects two LoRAs by strategy
3. **Generate**: `BattleGenerator` creates battle with same seed/prompt for both LoRAs
4. **Vote**: `BattleDisplay` shows images, user votes via API
5. **Update**: Vote processed, ELO recalculated, history recorded

### REST API (registered in `__init__.py`)
- `GET /lorarena/api/leaderboard` - Leaderboard
- `GET /lorarena/api/leaderboard/{id}/history` - ELO history
- `POST /lorarena/api/battles/new` - Create battle
- `GET /lorarena/api/battles/{id}` - Get battle status
- `POST /lorarena/api/battles/{id}/vote` - Submit vote
- `GET /lorarena/api/battles/history/list` - Paginated battle history
- `GET /lorarena/api/checkpoints` - List all checkpoints
- `POST /lorarena/api/checkpoints/scan` - Trigger scan
- `GET/PUT /lorarena/api/checkpoints/{id}` - Get/update checkpoint
- `PATCH /lorarena/api/checkpoints/{id}/toggle` - Toggle active status
- `POST /lorarena/api/checkpoints/batch-delete` - Batch delete
- `POST /lorarena/api/checkpoints/batch-status` - Batch enable/disable
- `GET/PUT /lorarena/api/config` - Config management
- `GET /lorarena/api/config/comfyui/models` - Available models/samplers
- `GET /lorarena/api/node/battle/current` - Current battle
- `POST /lorarena/api/node/battle/vote` - Widget vote
- `GET /lorarena/api/node/models-ready` - Panel Node status
- `GET /lorarena/images/{filename}` - Serve battle images

## Configuration

`data/config.json` (created on first run):
- `lora_directory` - LoRA path (relative to ComfyUI lora directory)
- `base_model` - SD checkpoint filename
- `steps`, `cfg_scale`, `sampler`, `scheduler` - Generation parameters
- `lora_strength` - LoRA strength (default 0.8)
- `width`, `height` - Image dimensions
- `mode` - `"host"` (full control) or `"guest"` (vote only)
- `prompt_prefix` - Prompt prefix
- `battle_royale_enabled`, `battle_royale_threshold`, `battle_royale_win_rate` - Elimination mode
- `auto_queue_enabled`, `auto_queue_target`, `auto_queue_max` - Auto queue settings
- `parallel_generation` - Generate both images simultaneously (default true)
- `training_data_directory` - Training data directory path
- `worker_enabled`, `worker_interval`, `worker_target_cache`, `worker_use_training_tags` - Background worker
- `remote_comfyui` - Remote ComfyUI mode
- `tipo_tag_length` - TIPO tag length

## Code Conventions

- **Python**: PEP 8, 4-space indentation
- **JavaScript**: ComfyUI widget patterns; communicate via `/lorarena/api/`
- **Database**: Synchronous SQLAlchemy; always use `session_scope()` context manager

## Testing

No automated tests. To verify changes:
1. Install extension to ComfyUI's `custom_nodes/`
2. Load example workflows from `examples/`
3. Test node connections and voting flow
4. After changes, commit and push to main branch
