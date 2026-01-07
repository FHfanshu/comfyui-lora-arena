"""
LoRArena Leaderboard Display Node - Shows LoRA rankings in an iframe widget.

This node displays the current LoRA leaderboard with ELO ratings,
win rates, and battle statistics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple


class LoRArenaLeaderboardDisplay:
    """
    Displays the LoRA leaderboard in an iframe widget.

    Also outputs top LoRA info and full leaderboard as JSON.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "limit": ("INT", {"default": 20, "min": 1, "max": 100}),
                "min_battles": ("INT", {"default": 0, "min": 0, "max": 9999}),
            },
            "optional": {
                "trigger": ("*",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("top_lora", "top_lora_elo", "total_count", "leaderboard_json")
    FUNCTION = "show_leaderboard"
    CATEGORY = "LoRArena"
    OUTPUT_NODE = True

    def show_leaderboard(self, limit: int = 20, min_battles: int = 0, trigger=None) -> Tuple:
        """Fetch and display leaderboard data."""
        from sqlalchemy import select
        from ..services import db_manager, checkpoint_service
        from ..services.models import Checkpoint

        top_lora = ""
        top_elo = "0"
        total_count = 0
        items = []
        lora_directory = self._load_config_lora_directory()

        try:
            with db_manager.session_scope() as db:
                query = (
                    select(Checkpoint)
                    .where(Checkpoint.is_active == True)
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

                total_count = len(checkpoints)

                for idx, cp in enumerate(checkpoints, start=1):
                    items.append({
                        "rank": idx,
                        "name": cp.name,
                        "filename": cp.filename,
                        "elo": cp.elo_rating,
                        "battles": cp.total_battles,
                        "wins": cp.wins,
                        "win_rate": round(cp.win_rate * 100, 1),
                    })

                if checkpoints:
                    top_lora = checkpoints[0].filename
                    top_elo = str(checkpoints[0].elo_rating)

        except Exception as e:
            print(f"[LoRArena] Leaderboard error: {e}")

        leaderboard_json = json.dumps(items, ensure_ascii=False)
        return (top_lora, top_elo, total_count, leaderboard_json)

    def _load_config_lora_directory(self) -> str:
        try:
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / "data" / "config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                return str(data.get("lora_directory", "")).strip()
        except Exception:
            pass
        return ""
