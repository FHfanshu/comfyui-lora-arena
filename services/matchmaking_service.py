"""
Matchmaking Service.
Handles checkpoint selection for battles.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Checkpoint


def _load_config() -> dict:
    """Load config from data/config.json."""
    config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
    default = {
        "battle_royale_enabled": False,
        "battle_royale_threshold": 10,
        "battle_royale_win_rate": 0.3,
    }
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            default.update(data)
        except Exception:
            pass
    return default


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
        """Get all active checkpoints, optionally excluding some.

        Also applies Battle Royale filtering if enabled:
        - Only triggers when ALL checkpoints have reached the minimum battle threshold
        - Then eliminates checkpoints with low win rate AND low ELO ranking
        - Always keeps at least 2 checkpoints for battles
        """
        query = select(Checkpoint).where(Checkpoint.is_active == True)
        if exclude_ids:
            query = query.where(Checkpoint.id.notin_(exclude_ids))
        result = db.execute(query)
        checkpoints = list(result.scalars().all())

        # Apply Battle Royale filtering
        config = _load_config()
        if config.get("battle_royale_enabled", False) and len(checkpoints) > 2:
            threshold = config.get("battle_royale_threshold", 10)
            min_win_rate = config.get("battle_royale_win_rate", 0.3)

            # Only trigger elimination when ALL checkpoints have reached threshold
            all_reached_threshold = all(c.total_battles >= threshold for c in checkpoints)

            if all_reached_threshold:
                # Sort by ELO to identify bottom performers
                sorted_by_elo = sorted(checkpoints, key=lambda c: c.elo_rating)

                # Find low performers: low win rate AND in bottom half of ELO
                low_performers = [
                    c for c in sorted_by_elo
                    if c.win_rate < min_win_rate
                ]

                if low_performers:
                    # Ensure we keep at least 2 checkpoints
                    max_to_eliminate = len(checkpoints) - 2
                    to_eliminate = low_performers[:max_to_eliminate]

                    if to_eliminate:
                        eliminated_ids = {c.id for c in to_eliminate}
                        checkpoints = [c for c in checkpoints if c.id not in eliminated_ids]

        return checkpoints

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
