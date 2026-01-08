from __future__ import annotations

import json
import locale
from pathlib import Path

print("[LoRArena] custom node package loaded")

from .nodes import (
    LoRArenaBattleGenerator,
    LoRArenaCheckpointScanner,
    LoRArenaELODisplay,
    LoRArenaMatchmaker,
    LoRArenaVoteRecorder,
    LoRArenaPanelNode,
    LoRArenaBattleDisplay,
    LoRArenaLeaderboardDisplay,
    LoRArenaLoraLoader,
    LoRArenaRandomPrompt,
)

NODE_CLASS_MAPPINGS = {
    "LoRArenaMatchmaker": LoRArenaMatchmaker,
    "LoRArenaBattleGenerator": LoRArenaBattleGenerator,
    "LoRArenaVoteRecorder": LoRArenaVoteRecorder,
    "LoRArenaCheckpointScanner": LoRArenaCheckpointScanner,
    "LoRArenaELODisplay": LoRArenaELODisplay,
    "LoRArenaPanelNode": LoRArenaPanelNode,
    "LoRArenaBattleDisplay": LoRArenaBattleDisplay,
    "LoRArenaLeaderboardDisplay": LoRArenaLeaderboardDisplay,
    "LoRArenaLoraLoader": LoRArenaLoraLoader,
    "LoRArenaRandomPrompt": LoRArenaRandomPrompt,
}

_locale = locale.getdefaultlocale()[0] or ""
_is_zh = _locale.lower().startswith("zh")

if _is_zh:
    NODE_DISPLAY_NAME_MAPPINGS = {
        "LoRArenaMatchmaker": "LoRArena 对战匹配",
        "LoRArenaBattleGenerator": "LoRArena 对战生成",
        "LoRArenaVoteRecorder": "LoRArena 投票记录",
        "LoRArenaCheckpointScanner": "LoRArena 扫描导入",
        "LoRArenaELODisplay": "LoRArena ELO 统计",
        "LoRArenaPanelNode": "LoRArena 面板",
        "LoRArenaBattleDisplay": "LoRArena 对战展示",
        "LoRArenaLeaderboardDisplay": "LoRArena 排行榜展示",
        "LoRArenaLoraLoader": "LoRArena 加载LoRA(字符串)",
        "LoRArenaRandomPrompt": "LoRArena 随机提示词",
    }
else:
    NODE_DISPLAY_NAME_MAPPINGS = {
        "LoRArenaMatchmaker": "LoRArena Matchmaker",
        "LoRArenaBattleGenerator": "LoRArena Battle Generator",
        "LoRArenaVoteRecorder": "LoRArena Vote Recorder",
        "LoRArenaCheckpointScanner": "LoRArena Checkpoint Scanner",
        "LoRArenaELODisplay": "LoRArena ELO Display",
        "LoRArenaPanelNode": "LoRArena Panel",
        "LoRArenaBattleDisplay": "LoRArena Battle Display",
        "LoRArenaLeaderboardDisplay": "LoRArena Leaderboard Display",
        "LoRArenaLoraLoader": "LoRArena Load LoRA (String)",
        "LoRArenaRandomPrompt": "LoRArena Random Prompt",
    }

WEB_DIRECTORY = "web/js"
print(f"[LoRArena] locale={_locale} ui={'zh' if _is_zh else 'en'}")
print(f"[LoRArena] web directory: {Path(__file__).resolve().parent / 'web'}")


def _register_api_routes() -> None:
    try:
        from aiohttp import web
        from server import PromptServer
        from sqlalchemy import select, func

        from .services import battle_service, checkpoint_service, db_manager, model_state, battle_state
        from .services.models import Battle, Checkpoint, ELOHistory
    except Exception:
        return

    print("[LoRArena] registering API routes")
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path = data_dir / "config.json"
    print(f"[LoRArena] db path: {db_manager.db_path}")
    print(f"[LoRArena] config path: {config_path}")

    def _default_config() -> dict:
        return {
            "lora_directory": "",
            "lora_strength": 0.8,
            "training_data_directory": "",
            "battle_royale_enabled": False,
            "battle_royale_threshold": 10,
            "battle_royale_win_rate": 0.5,
            "auto_queue_enabled": False,
            "auto_queue_target": 10,  # Target queue depth
            "auto_queue_max": 30,     # Maximum queue depth
            "prompt_prefix": "",      # Custom prompt prefix
            "mode": "host",           # "host" or "guest" mode
        }

    def _load_config() -> dict:
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                base = _default_config()
                base.update(data)
                return base
            except Exception:
                return _default_config()
        return _default_config()

    def _save_config(data: dict) -> dict:
        base = _default_config()
        base.update(data)
        config_path.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
        return base

    config_state = _load_config()
    print("[LoRArena] config loaded")

    # Helper to check if current mode allows host-only actions
    def _is_guest_mode() -> bool:
        return config_state.get("mode", "host") == "guest"

    # Full-page web app disabled. Using lightweight in-canvas widgets only.

    @PromptServer.instance.routes.get("/lorarena/api/leaderboard")
    async def lorarena_leaderboard(request):
        try:
            limit = int(request.query.get("limit", 50))
            min_battles = int(request.query.get("min_battles", 0))
        except Exception:
            limit = 50
            min_battles = 0

        lora_directory = (
            request.query.get("lora_directory", "")
            or config_state.get("lora_directory", "")
            or ""
        )
        lora_directory = str(lora_directory).strip()

        with db_manager.session_scope() as db:
            query = (
                select(Checkpoint)
                .where(Checkpoint.total_battles >= min_battles)
                .order_by(Checkpoint.elo_rating.desc())
            )
            if not lora_directory:
                query = query.limit(limit)
            checkpoints = list(db.execute(query).scalars().all())

        if lora_directory:
            checkpoints = [
                cp for cp in checkpoints
                if checkpoint_service._matches_directory(cp.filename, lora_directory)
            ][:limit]

        # Get Battle Royale settings for elimination status
        br_enabled = config_state.get("battle_royale_enabled", False)
        br_threshold = config_state.get("battle_royale_threshold", 10)
        br_win_rate = config_state.get("battle_royale_win_rate", 0.3)

        items = []
        for idx, checkpoint in enumerate(checkpoints, start=1):
            # Check if checkpoint is eliminated in Battle Royale
            eliminated = False
            if br_enabled:
                eliminated = (
                    checkpoint.total_battles >= br_threshold
                    and checkpoint.win_rate < br_win_rate
                )
            items.append(
                {
                    "rank": idx,
                    "checkpoint_id": checkpoint.id,
                    "name": checkpoint.name,
                    "elo_rating": checkpoint.elo_rating,
                    "total_battles": checkpoint.total_battles,
                    "wins": checkpoint.wins,
                    "losses": checkpoint.losses,
                    "ties": checkpoint.ties,
                    "win_rate": checkpoint.win_rate,
                    "eliminated": eliminated,
                }
            )

        return web.json_response({
            "items": items,
            "total": len(items),
            "battle_royale_enabled": br_enabled,
        })

    @PromptServer.instance.routes.get("/lorarena/api/leaderboard/{checkpoint_id}/history")
    async def lorarena_leaderboard_history(request):
        checkpoint_id = int(request.match_info["checkpoint_id"])
        limit = int(request.query.get("limit", 100))
        with db_manager.session_scope() as db:
            history = (
                db.execute(
                    select(ELOHistory)
                    .where(ELOHistory.checkpoint_id == checkpoint_id)
                    .order_by(ELOHistory.recorded_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            checkpoint = (
                db.execute(select(Checkpoint).where(Checkpoint.id == checkpoint_id))
                .scalar_one_or_none()
            )

        return web.json_response(
            {
                "checkpoint_id": checkpoint_id,
                "checkpoint_name": checkpoint.name if checkpoint else "",
                "history": [
                    {
                        "elo_rating": h.elo_rating,
                        "recorded_at": h.recorded_at.isoformat(),
                        "battle_id": h.battle_id,
                    }
                    for h in history
                ],
            }
        )

    @PromptServer.instance.routes.get("/lorarena/api/checkpoints")
    async def lorarena_checkpoints(request):
        page = int(request.query.get("page", 1))
        limit = int(request.query.get("limit", 50))
        sort_by = request.query.get("sort_by", "elo_rating")
        sort_order = request.query.get("sort_order", "desc")
        active_only = request.query.get("active_only", "false").lower() == "true"
        with db_manager.session_scope() as db:
            checkpoints, total = checkpoint_service.list_checkpoints(
                db, page, limit, sort_by, sort_order, active_only
            )

        items = [
            {
                "id": c.id,
                "name": c.name,
                "filename": c.filename,
                "file_path": c.file_path,
                "description": c.description,
                "trigger_words": c.trigger_words or [],
                "tags": c.tags or [],
                "training_data_path": c.training_data_path,
                "elo_rating": c.elo_rating,
                "total_battles": c.total_battles,
                "wins": c.wins,
                "losses": c.losses,
                "ties": c.ties,
                "win_rate": c.win_rate,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in checkpoints
        ]
        return web.json_response(
            {"items": items, "total": total, "page": page, "limit": limit}
        )

    @PromptServer.instance.routes.post("/lorarena/api/checkpoints/scan")
    async def lorarena_checkpoints_scan(request):
        # Guest mode: scanning not allowed
        if _is_guest_mode():
            return web.json_response(
                {"error": "Guest mode: scanning not allowed"},
                status=403,
            )
        data = await request.json()
        directory = data.get("directory") if isinstance(data, dict) else None
        with db_manager.session_scope() as db:
            result = checkpoint_service.scan_directory(db, directory)
        return web.json_response(
            {
                "scanned": result.scanned,
                "imported": result.imported,
                "skipped": result.skipped,
                "errors": result.errors,
            }
        )

    @PromptServer.instance.routes.get("/lorarena/api/checkpoints/{checkpoint_id}")
    async def lorarena_checkpoints_get(request):
        checkpoint_id = int(request.match_info["checkpoint_id"])
        with db_manager.session_scope() as db:
            checkpoint = checkpoint_service.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return web.json_response({"detail": "Checkpoint not found"}, status=404)
        return web.json_response(
            {
                "id": checkpoint.id,
                "name": checkpoint.name,
                "filename": checkpoint.filename,
                "file_path": checkpoint.file_path,
                "description": checkpoint.description,
                "trigger_words": checkpoint.trigger_words or [],
                "tags": checkpoint.tags or [],
                "training_data_path": checkpoint.training_data_path,
                "elo_rating": checkpoint.elo_rating,
                "total_battles": checkpoint.total_battles,
                "wins": checkpoint.wins,
                "losses": checkpoint.losses,
                "ties": checkpoint.ties,
                "win_rate": checkpoint.win_rate,
                "is_active": checkpoint.is_active,
                "created_at": checkpoint.created_at.isoformat(),
                "updated_at": checkpoint.updated_at.isoformat(),
            }
        )

    @PromptServer.instance.routes.put("/lorarena/api/checkpoints/{checkpoint_id}")
    async def lorarena_checkpoints_update(request):
        checkpoint_id = int(request.match_info["checkpoint_id"])
        data = await request.json()
        with db_manager.session_scope() as db:
            checkpoint = checkpoint_service.update_checkpoint(db, checkpoint_id, data or {})
        if not checkpoint:
            return web.json_response({"detail": "Checkpoint not found"}, status=404)
        return web.json_response(
            {
                "id": checkpoint.id,
                "name": checkpoint.name,
                "filename": checkpoint.filename,
                "file_path": checkpoint.file_path,
                "description": checkpoint.description,
                "trigger_words": checkpoint.trigger_words or [],
                "tags": checkpoint.tags or [],
                "training_data_path": checkpoint.training_data_path,
                "elo_rating": checkpoint.elo_rating,
                "total_battles": checkpoint.total_battles,
                "wins": checkpoint.wins,
                "losses": checkpoint.losses,
                "ties": checkpoint.ties,
                "win_rate": checkpoint.win_rate,
                "is_active": checkpoint.is_active,
                "created_at": checkpoint.created_at.isoformat(),
                "updated_at": checkpoint.updated_at.isoformat(),
            }
        )

    @PromptServer.instance.routes.patch("/lorarena/api/checkpoints/{checkpoint_id}/toggle")
    async def lorarena_checkpoints_toggle(request):
        checkpoint_id = int(request.match_info["checkpoint_id"])
        with db_manager.session_scope() as db:
            checkpoint = checkpoint_service.toggle_active(db, checkpoint_id)
        if not checkpoint:
            return web.json_response({"detail": "Checkpoint not found"}, status=404)
        return web.json_response(
            {
                "id": checkpoint.id,
                "name": checkpoint.name,
                "filename": checkpoint.filename,
                "file_path": checkpoint.file_path,
                "description": checkpoint.description,
                "trigger_words": checkpoint.trigger_words or [],
                "tags": checkpoint.tags or [],
                "training_data_path": checkpoint.training_data_path,
                "elo_rating": checkpoint.elo_rating,
                "total_battles": checkpoint.total_battles,
                "wins": checkpoint.wins,
                "losses": checkpoint.losses,
                "ties": checkpoint.ties,
                "win_rate": checkpoint.win_rate,
                "is_active": checkpoint.is_active,
                "created_at": checkpoint.created_at.isoformat(),
                "updated_at": checkpoint.updated_at.isoformat(),
            }
        )

    @PromptServer.instance.routes.post("/lorarena/api/checkpoints/batch-delete")
    async def lorarena_checkpoints_batch_delete(request):
        data = await request.json()
        ids = data.get("checkpoint_ids", []) if isinstance(data, dict) else []
        with db_manager.session_scope() as db:
            count = checkpoint_service.batch_delete_checkpoints(db, ids)
        return web.json_response({"success": True, "message": f"Deleted {count} checkpoints"})

    @PromptServer.instance.routes.post("/lorarena/api/checkpoints/batch-status")
    async def lorarena_checkpoints_batch_status(request):
        data = await request.json()
        ids = data.get("checkpoint_ids", []) if isinstance(data, dict) else []
        is_active = bool(data.get("is_active", False)) if isinstance(data, dict) else False
        with db_manager.session_scope() as db:
            count = checkpoint_service.batch_update_status(db, ids, is_active)
        status = "enabled" if is_active else "disabled"
        return web.json_response(
            {"success": True, "message": f"{status.capitalize()} {count} checkpoints"}
        )

    @PromptServer.instance.routes.post("/lorarena/api/checkpoints/reset-all")
    async def lorarena_checkpoints_reset_all(request):
        """Reset all checkpoints to initial state (ELO=1500, stats=0)."""
        if _is_guest_mode():
            return web.json_response(
                {"error": "Guest mode: reset not allowed"},
                status=403,
            )
        # Get lora_directory from config for filtering
        lora_directory = config_state.get("lora_directory", "")
        with db_manager.session_scope() as db:
            count = checkpoint_service.reset_all_checkpoints(db, lora_directory if lora_directory else None)
        return web.json_response({
            "success": True,
            "message": f"Reset {count} checkpoints to initial state",
            "count": count,
        })

    @PromptServer.instance.routes.post("/lorarena/api/checkpoints/eliminate")
    async def lorarena_checkpoints_eliminate(request):
        """Eliminate checkpoints based on Battle Royale rules and move files to parent directory."""
        if _is_guest_mode():
            return web.json_response(
                {"error": "Guest mode: elimination not allowed"},
                status=403,
            )
        lora_directory = config_state.get("lora_directory", "")
        with db_manager.session_scope() as db:
            result = checkpoint_service.eliminate_checkpoints(
                db, lora_directory if lora_directory else None
            )
        return web.json_response({
            "success": result.eliminated > 0 or not result.errors,
            "eliminated": result.eliminated,
            "moved": result.moved,
            "errors": result.errors,
        })

    @PromptServer.instance.routes.post("/lorarena/api/checkpoints/refresh")
    async def lorarena_checkpoints_refresh(request):
        """Refresh checkpoint status by checking if files still exist."""
        lora_directory = config_state.get("lora_directory", "")
        with db_manager.session_scope() as db:
            result = checkpoint_service.refresh_checkpoints(
                db, lora_directory if lora_directory else None
            )
        return web.json_response({
            "success": True,
            **result,
        })

    @PromptServer.instance.routes.post("/lorarena/api/battles/new")
    async def lorarena_battles_new(request):
        # Guest mode: battle creation not allowed
        if _is_guest_mode():
            return web.json_response(
                {"error": "Guest mode: battle creation not allowed"},
                status=403,
            )
        data = await request.json()
        prompt = data.get("prompt") if isinstance(data, dict) else None
        strategy = data.get("strategy", "balanced") if isinstance(data, dict) else "balanced"
        use_training_tags = bool(data.get("use_training_tags", False)) if isinstance(data, dict) else False

        with db_manager.session_scope() as db:
            checkpoints = db.execute(
                select(Checkpoint).where(Checkpoint.is_active == True)
            ).scalars().all()
            if len(checkpoints) < 2:
                return web.json_response(
                    {"detail": "Not enough active checkpoints for a battle"},
                    status=400,
                )

            # Create a battle record
            from .services.matchmaking_service import matchmaking_service

            left, right = matchmaking_service.select_matchup(db, strategy=strategy)
            seed = matchmaking_service.generate_seed()

            # Get LoRA filenames for generation
            left_lora = left.filename
            right_lora = right.filename

            battle = battle_service.create_battle(
                db,
                left,
                right,
                prompt=prompt or "masterpiece, best quality, 1girl",
                negative_prompt="",
                seed=seed,
                width=1024,   # Default, workflow can override
                height=1024,
                steps=20,
                cfg_scale=7.0,
                sampler="euler_ancestral",
                lora_strength=config_state.get("lora_strength", 0.8),
                base_model="",
            )
            battle.status = "generating"
            db.commit()
            battle_id = battle.id
            battle_prompt = battle.prompt
            battle_negative = battle.negative_prompt
            battle_seed = battle.seed
            battle_width = battle.width
            battle_height = battle.height
            battle_steps = battle.steps
            battle_cfg = battle.cfg_scale
            battle_sampler = battle.sampler

        # Try internal generation first
        try:
            from .services.comfyui_generator import generate_battle_images_async

            left_path, right_path = await generate_battle_images_async(
                lora_left=left_lora,
                lora_right=right_lora,
                prompt=battle_prompt,
                negative_prompt=battle_negative,
                seed=battle_seed,
                width=battle_width,
                height=battle_height,
                steps=battle_steps,
                cfg_scale=battle_cfg,
                sampler_name=battle_sampler,
                scheduler="normal",
                lora_strength=config_state.get("lora_strength", 0.8),
                base_model="",
                battle_id=battle_id,
            )

            with db_manager.session_scope() as db:
                battle = db.execute(select(Battle).where(Battle.id == battle_id)).scalar_one()
                if left_path and right_path:
                    battle.left_image_path = left_path
                    battle.right_image_path = right_path
                    battle.status = "completed"
                    battle.error_message = None
                else:
                    battle.status = "failed"
                    battle.error_message = "Image generation failed"
                db.commit()

                return web.json_response(
                    {
                        "battle_id": battle.id,
                        "status": battle.status,
                        "left_image_url": battle.left_image_path,
                        "right_image_url": battle.right_image_path,
                        "prompt": battle.prompt,
                        "negative_prompt": battle.negative_prompt,
                        "seed": battle.seed,
                        "width": battle.width,
                        "height": battle.height,
                        "steps": battle.steps,
                        "cfg_scale": battle.cfg_scale,
                        "error_message": battle.error_message,
                    }
                )

        except Exception as e:
            print(f"[LoRArena] Internal generation failed: {e}")
            import traceback
            traceback.print_exc()

            # Fallback: mark as failed
            with db_manager.session_scope() as db:
                battle = db.execute(select(Battle).where(Battle.id == battle_id)).scalar_one()
                battle.status = "failed"
                battle.error_message = f"Generation failed: {str(e)}"
                db.commit()

            return web.json_response(
                {
                    "battle_id": battle_id,
                    "status": "failed",
                    "left_image_url": None,
                    "right_image_url": None,
                    "prompt": battle_prompt,
                    "negative_prompt": battle_negative,
                    "seed": battle_seed,
                    "width": battle_width,
                    "height": battle_height,
                    "steps": battle_steps,
                    "cfg_scale": battle_cfg,
                    "error_message": f"Generation failed: {str(e)}",
                }
            )

    @PromptServer.instance.routes.get("/lorarena/api/battles/{battle_id}")
    async def lorarena_battles_status(request):
        battle_id = int(request.match_info["battle_id"])
        with db_manager.session_scope() as db:
            battle = db.execute(select(Battle).where(Battle.id == battle_id)).scalar_one_or_none()
        if not battle:
            return web.json_response({"detail": "Battle not found"}, status=404)
        return web.json_response(
            {
                "battle_id": battle.id,
                "status": battle.status,
                "left_image_url": battle.left_image_path,
                "right_image_url": battle.right_image_path,
                "prompt": battle.prompt,
                "negative_prompt": battle.negative_prompt,
                "seed": battle.seed,
                "width": battle.width,
                "height": battle.height,
                "steps": battle.steps,
                "cfg_scale": battle.cfg_scale,
                "error_message": battle.error_message,
            }
        )

    @PromptServer.instance.routes.post("/lorarena/api/battles/{battle_id}/vote")
    async def lorarena_battles_vote(request):
        battle_id = int(request.match_info["battle_id"])
        data = await request.json()
        result = data.get("result", "skip") if isinstance(data, dict) else "skip"

        with db_manager.session_scope() as db:
            battle, changes = battle_service.submit_vote(db, battle_id, result)
            left = db.execute(
                select(Checkpoint).where(Checkpoint.id == battle.left_checkpoint_id)
            ).scalar_one_or_none()
            right = db.execute(
                select(Checkpoint).where(Checkpoint.id == battle.right_checkpoint_id)
            ).scalar_one_or_none()

        return web.json_response(
            {
                "success": True,
                "left_checkpoint": {
                    "id": left.id if left else 0,
                    "name": left.name if left else "",
                    "filename": left.filename if left else "",
                    "file_path": left.file_path if left else "",
                    "description": left.description if left else None,
                    "trigger_words": left.trigger_words if left else [],
                    "tags": left.tags if left else [],
                    "training_data_path": left.training_data_path if left else None,
                    "elo_rating": left.elo_rating if left else 0,
                    "total_battles": left.total_battles if left else 0,
                    "wins": left.wins if left else 0,
                    "losses": left.losses if left else 0,
                    "ties": left.ties if left else 0,
                    "win_rate": left.win_rate if left else 0,
                    "is_active": left.is_active if left else False,
                    "created_at": left.created_at.isoformat() if left else "",
                    "updated_at": left.updated_at.isoformat() if left else "",
                },
                "right_checkpoint": {
                    "id": right.id if right else 0,
                    "name": right.name if right else "",
                    "filename": right.filename if right else "",
                    "file_path": right.file_path if right else "",
                    "description": right.description if right else None,
                    "trigger_words": right.trigger_words if right else [],
                    "tags": right.tags if right else [],
                    "training_data_path": right.training_data_path if right else None,
                    "elo_rating": right.elo_rating if right else 0,
                    "total_battles": right.total_battles if right else 0,
                    "wins": right.wins if right else 0,
                    "losses": right.losses if right else 0,
                    "ties": right.ties if right else 0,
                    "win_rate": right.win_rate if right else 0,
                    "is_active": right.is_active if right else False,
                    "created_at": right.created_at.isoformat() if right else "",
                    "updated_at": right.updated_at.isoformat() if right else "",
                },
                "winner": battle.result,
                "elo_changes": changes,
            }
        )

    @PromptServer.instance.routes.get("/lorarena/api/battles/history/list")
    async def lorarena_battles_history(request):
        page = int(request.query.get("page", 1))
        limit = int(request.query.get("limit", 20))
        offset = (page - 1) * limit
        with db_manager.session_scope() as db:
            total = (
                db.execute(select(func.count(Battle.id)).where(Battle.result.isnot(None)))
                .scalar()
                or 0
            )
            battles = (
                db.execute(
                    select(Battle)
                    .where(Battle.result.isnot(None))
                    .order_by(Battle.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            checkpoints = {
                c.id: c.name for c in db.execute(select(Checkpoint)).scalars().all()
            }

        items = []
        for battle in battles:
            items.append(
                {
                    "id": battle.id,
                    "left_checkpoint_name": checkpoints.get(battle.left_checkpoint_id, ""),
                    "right_checkpoint_name": checkpoints.get(battle.right_checkpoint_id, ""),
                    "result": battle.result,
                    "prompt": battle.prompt,
                    "seed": battle.seed,
                    "left_image_url": battle.left_image_path,
                    "right_image_url": battle.right_image_path,
                    "created_at": battle.created_at.isoformat(),
                    "voted_at": battle.voted_at.isoformat() if battle.voted_at else None,
                }
            )
        return web.json_response({"items": items, "total": total, "page": page, "limit": limit})

    @PromptServer.instance.routes.get("/lorarena/api/config")
    async def lorarena_config_get(request):
        return web.json_response(config_state)

    @PromptServer.instance.routes.put("/lorarena/api/config")
    async def lorarena_config_put(request):
        # Guest mode: only allow reading config, not modifying
        if _is_guest_mode():
            return web.json_response(
                {"error": "Guest mode: configuration changes not allowed"},
                status=403,
            )
        data = await request.json()
        if isinstance(data, dict):
            config_state.update(data)
        _save_config(config_state)
        return web.json_response(config_state)

    @PromptServer.instance.routes.get("/lorarena/api/config/comfyui/status")
    async def lorarena_config_status(request):
        return web.json_response({"connected": True, "url": config_state.get("comfyui_url", "")})

    @PromptServer.instance.routes.get("/lorarena/api/config/comfyui/models")
    async def lorarena_config_models(request):
        checkpoints = []
        loras = []
        samplers = []
        try:
            import folder_paths
            import comfy.samplers

            checkpoints = list(folder_paths.get_filename_list("checkpoints"))
            loras = list(folder_paths.get_filename_list("loras"))
            samplers = list(comfy.samplers.KSampler.SAMPLERS)
        except Exception:
            pass
        return web.json_response({"checkpoints": checkpoints, "loras": loras, "samplers": samplers})

    @PromptServer.instance.routes.post("/lorarena/api/prompts/optimize")
    async def lorarena_prompts_optimize(request):
        data = await request.json()
        prompt = data.get("prompt", "") if isinstance(data, dict) else ""
        return web.json_response({"optimized_prompt": prompt})

    # Model state API for Panel Node
    @PromptServer.instance.routes.get("/lorarena/api/node/models-ready")
    async def lorarena_node_models_ready(request):
        """Check if models are available from the Panel Node."""
        return web.json_response(model_state.get_status())

    @PromptServer.instance.routes.post("/lorarena/api/node/clear-models")
    async def lorarena_node_clear_models(request):
        """Clear model state (for testing)."""
        model_state.clear_models()
        return web.json_response({"success": True})

    # Battle state API for Battle Display Node
    @PromptServer.instance.routes.get("/lorarena/api/node/battle/current")
    async def lorarena_node_battle_current(request):
        """Get current battle data for display."""
        return web.json_response(battle_state.get_battle())

    @PromptServer.instance.routes.get("/lorarena/images/{filename}")
    async def lorarena_serve_image(request):
        """Serve battle images from output/lorarena/ directory."""
        import folder_paths
        filename = request.match_info["filename"]

        # Security check: only allow access to lorarena directory
        if ".." in filename or "/" in filename or "\\" in filename:
            return web.Response(status=403, text="Forbidden")

        filepath = Path(folder_paths.get_output_directory()) / "lorarena" / filename
        if not filepath.exists():
            return web.Response(status=404, text="Not found")

        return web.FileResponse(filepath)

    @PromptServer.instance.routes.get("/lorarena/api/node/battle/status")
    async def lorarena_node_battle_status(request):
        """Get current battle status."""
        return web.json_response(battle_state.get_status())

    @PromptServer.instance.routes.post("/lorarena/api/node/battle/vote")
    async def lorarena_node_battle_vote(request):
        """Submit a vote for the current battle."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON body"}, status=400
            )
        winner = data.get("winner", "skip") if isinstance(data, dict) else "skip"

        if not battle_state.has_battle():
            return web.json_response(
                {"success": False, "error": "No active battle"},
                status=400,
            )

        try:
            # Get battle info before voting
            battle_info = battle_state.get_battle()
            lora_a = battle_info.get("lora_name_a", "")
            lora_b = battle_info.get("lora_name_b", "")

            # Submit vote to battle_state
            success = battle_state.submit_vote(winner)

            if success and winner != "skip":
                # Update ELO in database
                with db_manager.session_scope() as db:
                    # Find checkpoints by filename
                    cp_a = db.execute(
                        select(Checkpoint).where(Checkpoint.filename == lora_a)
                    ).scalar_one_or_none()
                    cp_b = db.execute(
                        select(Checkpoint).where(Checkpoint.filename == lora_b)
                    ).scalar_one_or_none()

                    if cp_a and cp_b:
                        from .services.elo_service import elo_service
                        # Map winner to result format
                        result_map = {"a": "left", "b": "right", "tie": "tie"}
                        result = result_map.get(winner, "skip")
                        if result != "skip":
                            # Calculate new ELO ratings
                            elo_update = elo_service.process_battle(
                                rating_a=cp_a.elo_rating,
                                rating_b=cp_b.elo_rating,
                                result=result,
                                games_a=cp_a.total_battles,
                                games_b=cp_b.total_battles,
                            )
                            # Update checkpoint stats
                            cp_a.elo_rating = elo_update.new_rating_a
                            cp_b.elo_rating = elo_update.new_rating_b
                            cp_a.total_battles += 1
                            cp_b.total_battles += 1
                            if result == "left":
                                cp_a.wins += 1
                                cp_b.losses += 1
                            elif result == "right":
                                cp_a.losses += 1
                                cp_b.wins += 1
                            else:  # tie
                                cp_a.ties += 1
                                cp_b.ties += 1
                            db.commit()

            return web.json_response({
                "success": success,
                "winner": winner,
                "pending_count": battle_state.get_pending_count(),
                "auto_queue_enabled": config_state.get("auto_queue_enabled", False),
                "auto_queue_target": config_state.get("auto_queue_target", 10),
                "auto_queue_max": config_state.get("auto_queue_max", 30),
            })
        except Exception as exc:
            return web.json_response(
                {"success": False, "error": str(exc)},
                status=500,
            )


_register_api_routes()
