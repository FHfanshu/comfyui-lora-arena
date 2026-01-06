from __future__ import annotations

import json

from sqlalchemy import select

from ..services import db_manager
from ..services.models import Checkpoint


class LoRArenaELODisplay:
    """Display ELO stats for a single checkpoint."""

    @classmethod
    def INPUT_TYPES(cls):
        with db_manager.session_scope() as db:
            names = [row[0] for row in db.execute(select(Checkpoint.name)).all()]
        if not names:
            names = [""]
        return {"required": {"checkpoint_name": (sorted(names),)}}

    RETURN_TYPES = ("FLOAT", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("elo_rating", "total_battles", "win_rate", "stats_json")
    FUNCTION = "show"
    CATEGORY = "LoRArena"

    def show(self, checkpoint_name: str):
        if not checkpoint_name:
            return (0.0, 0, 0.0, json.dumps({"error": "No checkpoint selected"}))

        with db_manager.session_scope() as db:
            checkpoint = db.execute(
                select(Checkpoint).where(Checkpoint.name == checkpoint_name)
            ).scalar_one_or_none()

        if not checkpoint:
            return (0.0, 0, 0.0, json.dumps({"error": "Checkpoint not found"}))

        stats = {
            "checkpoint_id": checkpoint.id,
            "name": checkpoint.name,
            "elo_rating": checkpoint.elo_rating,
            "total_battles": checkpoint.total_battles,
            "wins": checkpoint.wins,
            "losses": checkpoint.losses,
            "ties": checkpoint.ties,
            "win_rate": checkpoint.win_rate,
        }
        return (
            float(checkpoint.elo_rating),
            int(checkpoint.total_battles),
            float(checkpoint.win_rate),
            json.dumps(stats, ensure_ascii=False),
        )
