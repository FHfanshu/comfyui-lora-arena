"""
Model state management for LoRArena Panel Node.

Stores model references from node execution for use by API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Global model state - shared between node execution and API calls
_current_models: Dict[str, Any] = {
    "model": None,
    "clip": None,
    "vae": None,
}

_last_result: Tuple[str, str] = ("", "{}")


def set_models(model: Any, clip: Any, vae: Any) -> None:
    """Save model references from node execution."""
    global _current_models
    _current_models = {
        "model": model,
        "clip": clip,
        "vae": vae,
    }
    logger.info("[LoRArena] Models set from node: model=%s, clip=%s, vae=%s",
                type(model).__name__ if model else None,
                type(clip).__name__ if clip else None,
                type(vae).__name__ if vae else None)


def get_models() -> Dict[str, Any]:
    """Get current model references."""
    return _current_models


def get_model() -> Optional[Any]:
    """Get current model."""
    return _current_models.get("model")


def get_clip() -> Optional[Any]:
    """Get current CLIP."""
    return _current_models.get("clip")


def get_vae() -> Optional[Any]:
    """Get current VAE."""
    return _current_models.get("vae")


def has_models() -> bool:
    """Check if all required models are available."""
    return all(v is not None for v in _current_models.values())


def clear_models() -> None:
    """Clear all model references."""
    global _current_models
    _current_models = {
        "model": None,
        "clip": None,
        "vae": None,
    }
    logger.info("[LoRArena] Models cleared")


def set_last_result(winner: str, stats: str) -> None:
    """Save the last vote result."""
    global _last_result
    _last_result = (winner, stats)


def get_last_result() -> Tuple[str, str]:
    """Get the last vote result."""
    return _last_result


def get_status() -> Dict[str, Any]:
    """Get current status for API response."""
    return {
        "ready": has_models(),
        "model_loaded": _current_models.get("model") is not None,
        "clip_loaded": _current_models.get("clip") is not None,
        "vae_loaded": _current_models.get("vae") is not None,
        "message": "模型已就绪，可以开始对战" if has_models() else "请先连接模型并执行节点",
    }
