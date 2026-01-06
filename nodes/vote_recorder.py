from __future__ import annotations

import json

from sqlalchemy import select

from ..services import battle_service, db_manager
from ..services.models import Checkpoint
from .battle_types import LORARENA_BATTLE


class LoRArenaVoteRecorder:
    """Record a vote for a battle and update ELO."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "battle_info": ("LORARENA_BATTLE",),
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
                "result": (["left", "right", "tie", "skip"],),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("winner_name", "elo_summary")
    FUNCTION = "record_vote"
    CATEGORY = "LoRArena"

    def record_vote(self, battle_info: LORARENA_BATTLE, image_a, image_b, result: str):
        if isinstance(battle_info, dict):
            battle = LORARENA_BATTLE.from_dict(battle_info)
        else:
            battle = battle_info

        if not battle.battle_id:
            raise RuntimeError("Battle ID missing. Run battle generation first.")

        with db_manager.session_scope() as db:
            battle_record, changes = battle_service.submit_vote(db, battle.battle_id, result)

            left = db.execute(
                select(Checkpoint).where(Checkpoint.id == battle_record.left_checkpoint_id)
            ).scalar_one_or_none()
            right = db.execute(
                select(Checkpoint).where(Checkpoint.id == battle_record.right_checkpoint_id)
            ).scalar_one_or_none()

        if result == "left":
            winner_name = left.name if left else "left"
        elif result == "right":
            winner_name = right.name if right else "right"
        else:
            winner_name = result

        summary = json.dumps(
            {
                "battle_id": battle.battle_id,
                "result": result,
                "changes": changes,
            },
            ensure_ascii=False,
        )

        return (winner_name, summary)
