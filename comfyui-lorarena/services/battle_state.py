"""
Battle state management for LoRArena Battle Display Node.

Stores battle images and metadata from node execution for display in iframe.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Global battle state - shared between node execution and iframe
_current_battle: Dict[str, Any] = {
    "battle_id": None,
    "image_a": None,  # base64 encoded
    "image_b": None,  # base64 encoded
    "lora_name_a": "",
    "lora_name_b": "",
    "timestamp": 0,
    "voted": False,
    "winner": None,
}

# Lock for thread-safe access
_lock = threading.Lock()

# Event for waiting on vote
_vote_event = threading.Event()


def set_battle(
    battle_id: str,
    image_a_base64: str,
    image_b_base64: str,
    lora_name_a: str,
    lora_name_b: str,
) -> None:
    """Set current battle data from node execution."""
    global _current_battle
    with _lock:
        _current_battle = {
            "battle_id": battle_id,
            "image_a": image_a_base64,
            "image_b": image_b_base64,
            "lora_name_a": lora_name_a,
            "lora_name_b": lora_name_b,
            "timestamp": time.time(),
            "voted": False,
            "winner": None,
        }
        _vote_event.clear()
    logger.info(
        "[LoRArena] Battle set: id=%s, lora_a=%s, lora_b=%s",
        battle_id, lora_name_a, lora_name_b
    )


def get_battle() -> Dict[str, Any]:
    """Get current battle data for iframe display."""
    with _lock:
        result = _current_battle.copy()
        # Add has_battle flag for frontend compatibility
        result["has_battle"] = (
            _current_battle.get("battle_id") is not None
            and not _current_battle.get("voted", False)
        )
        return result


def has_battle() -> bool:
    """Check if there's an active battle."""
    with _lock:
        return (
            _current_battle.get("battle_id") is not None
            and not _current_battle.get("voted", False)
        )


def submit_vote(winner: str) -> bool:
    """
    Submit a vote for the current battle.

    Args:
        winner: "a", "b", "tie", or "skip"

    Returns:
        True if vote was recorded, False if no active battle
    """
    global _current_battle
    with _lock:
        if _current_battle.get("battle_id") is None:
            return False
        if _current_battle.get("voted", False):
            return False

        _current_battle["voted"] = True
        _current_battle["winner"] = winner
        _vote_event.set()

    logger.info(
        "[LoRArena] Vote submitted: battle=%s, winner=%s",
        _current_battle.get("battle_id"), winner
    )
    return True


def wait_for_vote(timeout: float = 300.0) -> Optional[str]:
    """
    Wait for a vote to be submitted.

    Args:
        timeout: Maximum time to wait in seconds

    Returns:
        The winner ("a", "b", "tie", "skip") or None if timeout
    """
    if _vote_event.wait(timeout=timeout):
        with _lock:
            return _current_battle.get("winner")
    return None


def get_winner() -> Optional[str]:
    """Get the winner of the current battle (if voted)."""
    with _lock:
        if _current_battle.get("voted", False):
            return _current_battle.get("winner")
        return None


def clear_battle() -> None:
    """Clear current battle state."""
    global _current_battle
    with _lock:
        _current_battle = {
            "battle_id": None,
            "image_a": None,
            "image_b": None,
            "lora_name_a": "",
            "lora_name_b": "",
            "timestamp": 0,
            "voted": False,
            "winner": None,
        }
        _vote_event.clear()
    logger.info("[LoRArena] Battle cleared")


def get_status() -> Dict[str, Any]:
    """Get current battle status for API response."""
    with _lock:
        has_active = (
            _current_battle.get("battle_id") is not None
            and not _current_battle.get("voted", False)
        )
        return {
            "has_battle": has_active,
            "battle_id": _current_battle.get("battle_id"),
            "lora_name_a": _current_battle.get("lora_name_a", ""),
            "lora_name_b": _current_battle.get("lora_name_b", ""),
            "voted": _current_battle.get("voted", False),
            "winner": _current_battle.get("winner"),
        }
