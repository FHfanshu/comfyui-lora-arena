# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRA Arena is an ELO-based LoRA checkpoint evaluation system. It generates comparison images using ComfyUI and lets users vote to determine which LoRA produces better results. The system uses the same seed/prompt for both images, with the LoRA being the only variable.

The project has **two deployment modes**:
1. **Standalone mode**: FastAPI backend + React frontend running separately
2. **Embedded mode**: ComfyUI custom nodes with in-canvas widgets and API routes registered on ComfyUI's PromptServer

## Development Commands

### Backend (FastAPI + SQLAlchemy + SQLite)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (React + TypeScript + Vite + Tailwind)
```bash
cd frontend
npm install
npm run dev      # Development server on :5173
npm run build    # TypeScript build + Vite build
npm run lint     # ESLint
npm run preview  # Preview production build
```

### ComfyUI Extension
```bash
pip install -r comfyui-lorarena/requirements.txt
# Symlink or copy comfyui-lorarena/ to ComfyUI's custom_nodes/ directory
```

## Architecture

### Dual-Mode API Pattern

The frontend auto-detects its environment via URL path:
- Path starting with `/lorarena` → embedded mode, API base is `/lorarena/api`
- Otherwise → standalone mode, API base is `/api`

Both modes expose identical API endpoints, but served by different backends:
- **Standalone**: `backend/routers/*.py` (FastAPI)
- **Embedded**: `comfyui-lorarena/__init__.py` registers routes on `PromptServer.instance.routes`

### Backend (`backend/`)
- `main.py`: FastAPI entry point with lifespan handler for DB init and background cache worker
- `config.py` / `config.json`: Runtime configuration
- `routers/`: API route handlers (`battles.py`, `checkpoints.py`, `leaderboard.py`, `config.py`, `prompts.py`)
- `services/`: Business logic
  - `battle_service.py`: Battle creation/generation orchestration
  - `checkpoint_service.py`: LoRA file scanning and metadata
  - `elo_service.py`: ELO rating calculation
  - `matchmaking_service.py`: Opponent selection strategies (balanced, random, exploration)
  - `comfyui/client.py`: ComfyUI WebSocket/HTTP client
  - `comfyui/workflow_builder.py`: Dual-branch workflow JSON construction
- `models/database.py`: SQLAlchemy ORM models (Battle, Checkpoint, ELOHistory, PromptTemplate)
- `models/schemas.py`: Pydantic request/response schemas
- `db/session.py`: Async SQLite session management

### ComfyUI Extension (`comfyui-lorarena/`)
- `__init__.py`: Node registration (`NODE_CLASS_MAPPINGS`) and API route registration on ComfyUI's PromptServer
- `nodes/`: ComfyUI node implementations
  - `battle_display.py`, `leaderboard_display.py`: Nodes that render in-canvas widgets
  - `random_lora_pair.py`, `lora_loader.py`: LoRA selection nodes
  - `vote_recorder.py`, `battle_generator.py`: Battle workflow nodes
  - `panel_node.py`: Receives model/clip/vae from CheckpointLoader for internal generation
- `services/`: Shared services (duplicated/adapted from backend)
  - `battle_state.py`: Global state for current battle (images, vote status) accessed by web widgets
  - `model_state.py`: Tracks loaded model/clip/vae for Panel Node
  - `comfyui_generator.py`: Internal image generation using ComfyUI execution APIs
  - `database.py`: Synchronous SQLAlchemy session (SQLite at `data/lorarena.db`)
- `web/js/`: JavaScript widgets for in-canvas node UI
- `data/`: Runtime data (SQLite DB, config.json)

### Frontend (`frontend/src/`)
- `pages/`: Main views (ArenaPage, LeaderboardPage, CheckpointsPage, SettingsPage)
- `contexts/BattleContext.tsx`: Battle state management with polling for async generation
- `services/api.ts`: Unified API client that switches base URL by mode
- `locales/`: i18n translation files (en.json, zh.json)

### Key Data Flow
1. **Battle Creation**: Matchmaking selects two LoRAs → Battle record created → Background generation queued
2. **Image Generation**: ComfyUI workflow built with dual LoRA branches → Images saved to `static/battles/{id}/`
3. **Voting**: User votes → ELO ratings updated → ELO history recorded
4. **Pre-generation**: Background worker maintains cache of ready battles for instant serving

## Configuration

- `backend/config.json`: Primary configuration
  - `comfyui_url`: ComfyUI server address
  - `base_model`: Stable Diffusion checkpoint filename
  - `lora_directory`: Path to LoRA files (relative to ComfyUI's lora folder)
  - `worker_enabled`, `worker_interval`, `worker_target_cache`: Background pre-generation
  - `battle_royale_enabled`, `battle_royale_threshold`: Elimination mode settings
- `comfyui-lorarena/data/config.json`: Embedded mode configuration (same schema)

## Coding Conventions

- **Python**: PEP 8, 4-space indentation, async/await for DB and HTTP operations
- **TypeScript/React**: 2-space indentation, functional components with hooks
- **Naming**: Domain-focused (e.g., `battle_service`, `ArenaPage`, `useBattle`)
- **i18n**: All user-facing strings should use `useTranslation()` hook with keys in `locales/`

## Testing

No automated test suite. Validate changes manually by:
1. Running backend + frontend against a ComfyUI server
2. Testing Arena voting, Checkpoints scanning, Settings configuration, Leaderboard display
3. For embedded mode, install extension in ComfyUI and test node workflows
