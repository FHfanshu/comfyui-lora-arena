"""
ELO Rating Service.
Implements the classic ELO rating system for comparing LoRA checkpoints.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ELOUpdate:
    """Result of an ELO calculation."""

    old_rating_a: float
    old_rating_b: float
    new_rating_a: float
    new_rating_b: float
    expected_a: float
    expected_b: float
    change_a: float
    change_b: float


class ELOService:
    """ELO rating calculation service."""

    DEFAULT_RATING = 1500.0
    DEFAULT_K_FACTOR = 32.0

    def __init__(self, k_factor: float | None = None) -> None:
        self.k_factor = k_factor or self.DEFAULT_K_FACTOR

    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for player A."""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def calculate_new_rating(
        self,
        current_rating: float,
        expected_score: float,
        actual_score: float,
        k_factor: float | None = None,
    ) -> float:
        """Calculate new rating after a match."""
        k = k_factor or self.k_factor
        return current_rating + k * (actual_score - expected_score)

    def get_dynamic_k_factor(self, games_played: int, current_rating: float) -> float:
        """Return dynamic K-factor based on experience and rating."""
        if games_played < 30:
            return 40.0
        if current_rating > 2400:
            return 16.0
        if games_played > 100:
            return 24.0
        return 32.0

    def process_battle(
        self,
        rating_a: float,
        rating_b: float,
        result: Literal["left", "right", "tie"],
        games_a: int = 0,
        games_b: int = 0,
        use_dynamic_k: bool = True,
    ) -> ELOUpdate:
        """Process a battle result and calculate new ratings."""
        expected_a = self.calculate_expected_score(rating_a, rating_b)
        expected_b = 1 - expected_a

        if result == "left":
            actual_a, actual_b = 1.0, 0.0
        elif result == "right":
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a, actual_b = 0.5, 0.5

        if use_dynamic_k:
            k_a = self.get_dynamic_k_factor(games_a, rating_a)
            k_b = self.get_dynamic_k_factor(games_b, rating_b)
        else:
            k_a = k_b = self.k_factor

        new_rating_a = self.calculate_new_rating(rating_a, expected_a, actual_a, k_a)
        new_rating_b = self.calculate_new_rating(rating_b, expected_b, actual_b, k_b)

        return ELOUpdate(
            old_rating_a=rating_a,
            old_rating_b=rating_b,
            new_rating_a=new_rating_a,
            new_rating_b=new_rating_b,
            expected_a=expected_a,
            expected_b=expected_b,
            change_a=new_rating_a - rating_a,
            change_b=new_rating_b - rating_b,
        )


elo_service = ELOService()
