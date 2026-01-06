"""
Matchmaking Service.
Handles checkpoint selection for battles.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Checkpoint


class MatchmakingService:
    """Service for selecting checkpoints for battles."""

    def select_matchup(
        self,
        db: Session,
        strategy: str = "balanced",
        exclude_ids: Optional[List[int]] = None,
    ) -> Tuple[Checkpoint, Checkpoint]:
        """
        Select two checkpoints for a battle.

        Strategies:
        - random: Completely random selection
        - balanced: Prefer similar ELO ratings (±200)
        - exploration: Prioritize checkpoints with fewer battles
        """
        if strategy == "random":
            return self._random_matchup(db, exclude_ids)
        if strategy == "exploration":
            return self._exploration_matchup(db, exclude_ids)
        return self._balanced_matchup(db, exclude_ids)

    def _get_active_checkpoints(
        self,
        db: Session,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[Checkpoint]:
        """Get all active checkpoints, optionally excluding some."""
        query = select(Checkpoint).where(Checkpoint.is_active == True)
        if exclude_ids:
            query = query.where(Checkpoint.id.notin_(exclude_ids))
        result = db.execute(query)
        return list(result.scalars().all())

    def _random_matchup(
        self,
        db: Session,
        exclude_ids: Optional[List[int]] = None,
    ) -> Tuple[Checkpoint, Checkpoint]:
        checkpoints = self._get_active_checkpoints(db, exclude_ids)
        if len(checkpoints) < 2:
            raise ValueError("Not enough active checkpoints for a battle (need at least 2)")
        left, right = random.sample(checkpoints, 2)
        return left, right

    def _balanced_matchup(
        self,
        db: Session,
        exclude_ids: Optional[List[int]] = None,
    ) -> Tuple[Checkpoint, Checkpoint]:
        checkpoints = self._get_active_checkpoints(db, exclude_ids)
        if len(checkpoints) < 2:
            raise ValueError("Not enough active checkpoints for a battle (need at least 2)")

        first = random.choice(checkpoints)
        elo_range = 200
        candidates = [
            c
            for c in checkpoints
            if c.id != first.id and abs(c.elo_rating - first.elo_rating) <= elo_range
        ]
        if not candidates:
            candidates = [c for c in checkpoints if c.id != first.id]

        second = random.choice(candidates)
        if random.random() > 0.5:
            return first, second
        return second, first

    def _exploration_matchup(
        self,
        db: Session,
        exclude_ids: Optional[List[int]] = None,
    ) -> Tuple[Checkpoint, Checkpoint]:
        checkpoints = self._get_active_checkpoints(db, exclude_ids)
        if len(checkpoints) < 2:
            raise ValueError("Not enough active checkpoints for a battle (need at least 2)")

        weights = [1 / (c.total_battles + 1) for c in checkpoints]
        first = random.choices(checkpoints, weights=weights)[0]

        remaining = [(c, w) for c, w in zip(checkpoints, weights) if c.id != first.id]
        remaining_checkpoints = [c for c, _ in remaining]
        remaining_weights = [w for _, w in remaining]
        second = random.choices(remaining_checkpoints, weights=remaining_weights)[0]

        return first, second

    def generate_seed(self) -> int:
        """Generate a random seed for image generation."""
        return random.randint(0, 2**32 - 1)


matchmaking_service = MatchmakingService()
