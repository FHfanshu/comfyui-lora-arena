"""
Matchmaking Service

Handles checkpoint selection for battles.
"""

import random
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from models.database import Checkpoint


class MatchmakingService:
    """Service for selecting checkpoints for battles"""

    async def select_matchup(
        self,
        db: AsyncSession,
        strategy: str = "balanced",
        exclude_ids: Optional[List[int]] = None
    ) -> Tuple[Checkpoint, Checkpoint]:
        """
        Select two checkpoints for a battle.

        Args:
            db: Database session
            strategy: Selection strategy
                - "random": Completely random selection
                - "balanced": Prefer similar ELO ratings (±200)
                - "exploration": Prioritize checkpoints with fewer battles
            exclude_ids: Checkpoint IDs to exclude

        Returns:
            Tuple of two checkpoints (left, right)
        """
        if strategy == "random":
            return await self._random_matchup(db, exclude_ids)
        elif strategy == "balanced":
            return await self._balanced_matchup(db, exclude_ids)
        elif strategy == "exploration":
            return await self._exploration_matchup(db, exclude_ids)
        else:
            return await self._balanced_matchup(db, exclude_ids)

    async def _get_active_checkpoints(
        self,
        db: AsyncSession,
        exclude_ids: Optional[List[int]] = None
    ) -> List[Checkpoint]:
        """Get all active checkpoints, optionally excluding some"""
        query = select(Checkpoint).where(Checkpoint.is_active == True)

        if exclude_ids:
            query = query.where(Checkpoint.id.notin_(exclude_ids))

        result = await db.execute(query)
        return list(result.scalars().all())

    async def _random_matchup(
        self,
        db: AsyncSession,
        exclude_ids: Optional[List[int]] = None
    ) -> Tuple[Checkpoint, Checkpoint]:
        """Randomly select two different checkpoints"""
        checkpoints = await self._get_active_checkpoints(db, exclude_ids)

        if len(checkpoints) < 2:
            raise ValueError("Not enough active checkpoints for a battle (need at least 2)")

        selected = random.sample(checkpoints, 2)
        return selected[0], selected[1]

    async def _balanced_matchup(
        self,
        db: AsyncSession,
        exclude_ids: Optional[List[int]] = None
    ) -> Tuple[Checkpoint, Checkpoint]:
        """
        Select checkpoints with similar ELO ratings.

        1. Randomly select first checkpoint
        2. Find candidates within 200 ELO points
        3. Randomly select second from candidates
        """
        checkpoints = await self._get_active_checkpoints(db, exclude_ids)

        if len(checkpoints) < 2:
            raise ValueError("Not enough active checkpoints for a battle (need at least 2)")

        # Select first checkpoint randomly
        first = random.choice(checkpoints)

        # Find candidates within 200 ELO
        elo_range = 200
        candidates = [
            c for c in checkpoints
            if c.id != first.id and abs(c.elo_rating - first.elo_rating) <= elo_range
        ]

        # If no candidates in range, use all others
        if not candidates:
            candidates = [c for c in checkpoints if c.id != first.id]

        second = random.choice(candidates)

        # Randomize left/right position
        if random.random() > 0.5:
            return first, second
        else:
            return second, first

    async def _exploration_matchup(
        self,
        db: AsyncSession,
        exclude_ids: Optional[List[int]] = None
    ) -> Tuple[Checkpoint, Checkpoint]:
        """
        Prioritize checkpoints with fewer battles.

        Uses weighted random selection where weight = 1 / (battles + 1)
        """
        checkpoints = await self._get_active_checkpoints(db, exclude_ids)

        if len(checkpoints) < 2:
            raise ValueError("Not enough active checkpoints for a battle (need at least 2)")

        # Calculate weights (inverse of battle count)
        weights = [1 / (c.total_battles + 1) for c in checkpoints]

        # Select first checkpoint
        first = random.choices(checkpoints, weights=weights)[0]

        # Remove first from candidates and recalculate weights
        remaining = [(c, w) for c, w in zip(checkpoints, weights) if c.id != first.id]
        remaining_checkpoints = [c for c, _ in remaining]
        remaining_weights = [w for _, w in remaining]

        # Select second checkpoint
        second = random.choices(remaining_checkpoints, weights=remaining_weights)[0]

        return first, second

    def generate_seed(self) -> int:
        """Generate a random seed for image generation"""
        return random.randint(0, 2**32 - 1)


# Singleton instance
matchmaking_service = MatchmakingService()
