# Repository Guidelines

## Project Structure & Module Organization
- `backend/` FastAPI API + SQLAlchemy services; routes in `backend/routers`, domain logic in `backend/services`, models in `backend/models`, config in `backend/config.py` and `backend/config.json`, SQLite DB at `backend/lorarena.db`.
- `frontend/` React + TypeScript + Vite app; entry at `frontend/src/main.tsx`, pages in `frontend/src/pages`, UI in `frontend/src/components`, i18n in `frontend/src/locales`.
- `comfyui-lorarena/` ComfyUI extension; nodes in `comfyui-lorarena/nodes`, supporting services in `comfyui-lorarena/services`, web widgets in `comfyui-lorarena/web`, example workflows in `comfyui-lorarena/examples`.

## Build, Test, and Development Commands
Backend (API server):
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```
Frontend (UI):
```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
npm run preview
```
ComfyUI nodes (dependency):
```bash
pip install -r comfyui-lorarena/requirements.txt
```

## Coding Style & Naming Conventions
- Python follows PEP 8 with 4-space indentation; prefer async/await in DB and HTTP code.
- TypeScript/React uses 2-space indentation; favor functional components and hooks.
- Naming is domain-driven, e.g., `battle_service.py`, `ArenaPage.tsx`, `useBattle.ts`.

## Testing Guidelines
- No dedicated test suite or test runner is present in this repository.
- Validate changes manually by running backend + frontend and exercising Arena, Checkpoints, Settings, and Leaderboard flows against a running ComfyUI server.

## Commit & Pull Request Guidelines
- This workspace has no `.git` history, so commit conventions cannot be inferred here.
- Use short, imperative commit messages (example: `Fix battle pairing edge case`) and keep each commit focused.
- PRs should explain the change, list testing performed (or "not tested"), and include screenshots for UI changes.

## Configuration & Data
- Runtime settings live in `backend/config.json`, with environment overrides in `backend/.env`.
- ComfyUI extension data and defaults are under `comfyui-lorarena/data/`; avoid committing personal paths or secrets.
