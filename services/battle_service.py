"""
Battle Service.
Handles battle creation and voting (sync).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .elo_service import elo_service
from .models import Battle, Checkpoint, ELOHistory


class BattleService:
    """Service for managing battles."""

    def create_battle(
        self,
        db: Session,
        left_checkpoint: Checkpoint,
        right_checkpoint: Checkpoint,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        sampler: str,
        lora_strength: float,
        base_model: Optional[str] = None,
    ) -> Battle:
        battle = Battle(
            left_checkpoint_id=left_checkpoint.id,
            right_checkpoint_id=right_checkpoint.id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler=sampler,
            lora_strength=lora_strength,
            base_model=base_model,
            left_elo_before=left_checkpoint.elo_rating,
            right_elo_before=right_checkpoint.elo_rating,
            status="pending",
        )
        db.add(battle)
        db.commit()
        db.refresh(battle)
        return battle

    def get_battle(self, db: Session, battle_id: int) -> Optional[Battle]:
        result = db.execute(select(Battle).where(Battle.id == battle_id))
        return result.scalar_one_or_none()

    def submit_vote(
        self,
        db: Session,
        battle_id: int,
        result_value: str,
    ) -> Tuple[Battle, List[dict]]:
        battle = self.get_battle(db, battle_id)
        if not battle:
            raise ValueError(f"Battle {battle_id} not found")
        if battle.result is not None:
            raise ValueError(f"Battle {battle_id} already has a result")

        left_checkpoint = db.execute(
            select(Checkpoint).where(Checkpoint.id == battle.left_checkpoint_id)
        ).scalar_one()
        right_checkpoint = db.execute(
            select(Checkpoint).where(Checkpoint.id == battle.right_checkpoint_id)
        ).scalar_one()

        battle.result = result_value
        battle.voted_at = datetime.utcnow()

        elo_changes: List[dict] = []

        if result_value in ["left", "right", "tie"]:
            elo_update = elo_service.process_battle(
                rating_a=left_checkpoint.elo_rating,
                rating_b=right_checkpoint.elo_rating,
                result=result_value,  # type: ignore[arg-type]
                games_a=left_checkpoint.total_battles,
                games_b=right_checkpoint.total_battles,
            )

            left_checkpoint.elo_rating = elo_update.new_rating_a
            left_checkpoint.total_battles += 1
            if result_value == "left":
                left_checkpoint.wins += 1
            elif result_value == "right":
                left_checkpoint.losses += 1
            else:
                left_checkpoint.ties += 1

            right_checkpoint.elo_rating = elo_update.new_rating_b
            right_checkpoint.total_battles += 1
            if result_value == "right":
                right_checkpoint.wins += 1
            elif result_value == "left":
                right_checkpoint.losses += 1
            else:
                right_checkpoint.ties += 1

            db.add(
                ELOHistory(
                    checkpoint_id=left_checkpoint.id,
                    elo_rating=elo_update.new_rating_a,
                    battle_id=battle.id,
                )
            )
            db.add(
                ELOHistory(
                    checkpoint_id=right_checkpoint.id,
                    elo_rating=elo_update.new_rating_b,
                    battle_id=battle.id,
                )
            )

            battle.left_elo_after = elo_update.new_rating_a
            battle.right_elo_after = elo_update.new_rating_b

            elo_changes = [
                {
                    "checkpoint_id": left_checkpoint.id,
                    "name": left_checkpoint.name,
                    "old_rating": elo_update.old_rating_a,
                    "new_rating": elo_update.new_rating_a,
                    "change": elo_update.change_a,
                },
                {
                    "checkpoint_id": right_checkpoint.id,
                    "name": right_checkpoint.name,
                    "old_rating": elo_update.old_rating_b,
                    "new_rating": elo_update.new_rating_b,
                    "change": elo_update.change_b,
                },
            ]

        db.commit()
        db.refresh(battle)
        return battle, elo_changes


battle_service = BattleService()
