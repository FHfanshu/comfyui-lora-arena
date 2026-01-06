"""
ELO Rating Service

Implements the classic ELO rating system for comparing LoRA checkpoints.

Formula:
- Expected score: E_A = 1 / (1 + 10^((R_B - R_A) / 400))
- New rating: R'_A = R_A + K * (S_A - E_A)

Where:
- R_A, R_B: Current ratings of players A and B
- E_A: Expected score for player A
- S_A: Actual score (1 for win, 0.5 for tie, 0 for loss)
- K: K-factor (determines rating volatility)
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ELOUpdate:
    """Result of an ELO calculation"""
    old_rating_a: float
    old_rating_b: float
    new_rating_a: float
    new_rating_b: float
    expected_a: float
    expected_b: float
    change_a: float
    change_b: float


class ELOService:
    """ELO rating calculation service"""

    DEFAULT_RATING = 1500.0
    DEFAULT_K_FACTOR = 32.0

    def __init__(self, k_factor: float = None):
        self.k_factor = k_factor or self.DEFAULT_K_FACTOR

    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate the expected score for player A.

        E_A = 1 / (1 + 10^((R_B - R_A) / 400))

        Args:
            rating_a: Current rating of player A
            rating_b: Current rating of player B

        Returns:
            Expected score between 0 and 1
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def calculate_new_rating(
        self,
        current_rating: float,
        expected_score: float,
        actual_score: float,
        k_factor: float = None
    ) -> float:
        """
        Calculate the new rating after a match.

        R'_A = R_A + K * (S_A - E_A)

        Args:
            current_rating: Current rating
            expected_score: Expected score (from calculate_expected_score)
            actual_score: Actual score (1 for win, 0.5 for tie, 0 for loss)
            k_factor: Optional K-factor override

        Returns:
            New rating
        """
        k = k_factor or self.k_factor
        return current_rating + k * (actual_score - expected_score)

    def get_dynamic_k_factor(self, games_played: int, current_rating: float) -> float:
        """
        Get dynamic K-factor based on experience and rating.

        - New models (< 30 games): K = 40 (higher volatility)
        - Mid experience (30-100 games): K = 32
        - Experienced (> 100 games): K = 24 (more stable)
        - High rated (> 2400): K = 16 (very stable)

        Args:
            games_played: Number of games played
            current_rating: Current rating

        Returns:
            Appropriate K-factor
        """
        if games_played < 30:
            return 40.0
        elif current_rating > 2400:
            return 16.0
        elif games_played > 100:
            return 24.0
        return 32.0

    def process_battle(
        self,
        rating_a: float,
        rating_b: float,
        result: Literal["left", "right", "tie"],
        games_a: int = 0,
        games_b: int = 0,
        use_dynamic_k: bool = True
    ) -> ELOUpdate:
        """
        Process a battle result and calculate new ratings.

        Args:
            rating_a: Current rating of player A (left)
            rating_b: Current rating of player B (right)
            result: Battle result ("left" = A wins, "right" = B wins, "tie")
            games_a: Number of games played by A (for dynamic K)
            games_b: Number of games played by B (for dynamic K)
            use_dynamic_k: Whether to use dynamic K-factor

        Returns:
            ELOUpdate with old/new ratings and changes
        """
        # Calculate expected scores
        expected_a = self.calculate_expected_score(rating_a, rating_b)
        expected_b = 1 - expected_a

        # Determine actual scores
        if result == "left":
            actual_a, actual_b = 1.0, 0.0
        elif result == "right":
            actual_a, actual_b = 0.0, 1.0
        else:  # tie
            actual_a, actual_b = 0.5, 0.5

        # Get K-factors
        if use_dynamic_k:
            k_a = self.get_dynamic_k_factor(games_a, rating_a)
            k_b = self.get_dynamic_k_factor(games_b, rating_b)
        else:
            k_a = k_b = self.k_factor

        # Calculate new ratings
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


# Singleton instance
elo_service = ELOService()
