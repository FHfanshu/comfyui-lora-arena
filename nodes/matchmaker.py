from __future__ import annotations

import random

from ..services import db_manager, matchmaking_service
from .battle_types import LORARENA_BATTLE


class LoRArenaMatchmaker:
    """Select two LoRAs for a battle."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "strategy": (["balanced", "random", "exploration"],),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "LORARENA_BATTLE")
    RETURN_NAMES = ("lora_a", "lora_b", "battle_id", "battle_info")
    FUNCTION = "select"
    CATEGORY = "LoRArena"

    def select(self, strategy: str, seed: int):
        if seed:
            random.seed(seed)

        with db_manager.session_scope() as db:
            left, right = matchmaking_service.select_matchup(db, strategy=strategy)

        battle = LORARENA_BATTLE(
            battle_id=0,
            left_checkpoint_id=left.id,
            right_checkpoint_id=right.id,
            lora_left=left.filename,
            lora_right=right.filename,
            left_name=left.name,
            right_name=right.name,
            seed=seed or matchmaking_service.generate_seed(),
        )

        return (battle.lora_left, battle.lora_right, battle.battle_id, battle)
