from __future__ import annotations

import json

from sqlalchemy import select

from ..services import db_manager
from ..services.models import Checkpoint


class LoRArenaLeaderboard:
    """Return leaderboard data as JSON."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_battles": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "limit": ("INT", {"default": 50, "min": 1, "max": 1000}),
                "refresh": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("leaderboard_json",)
    FUNCTION = "get_leaderboard"
    CATEGORY = "LoRArena"

    def get_leaderboard(self, min_battles: int, limit: int, refresh: bool):
        with db_manager.session_scope() as db:
            query = (
                select(Checkpoint)
                .where(Checkpoint.total_battles >= min_battles)
                .order_by(Checkpoint.elo_rating.desc())
                .limit(limit)
            )
            checkpoints = list(db.execute(query).scalars().all())

        data = []
        for idx, checkpoint in enumerate(checkpoints, start=1):
            data.append(
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
                }
            )

        return (json.dumps({"items": data, "total": len(data)}, ensure_ascii=False),)
