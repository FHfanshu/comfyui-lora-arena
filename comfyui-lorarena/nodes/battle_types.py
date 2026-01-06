from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LORARENA_BATTLE:
    """Lightweight container for battle metadata passed between nodes."""

    battle_id: int = 0
    left_checkpoint_id: Optional[int] = None
    right_checkpoint_id: Optional[int] = None
    lora_left: str = ""
    lora_right: str = ""
    left_name: str = ""
    right_name: str = ""
    seed: int = 0
    prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.0
    sampler: str = "euler_ancestral"
    scheduler: str = "normal"
    lora_strength: float = 0.8
    base_model: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = self.__dict__.copy()
        data["meta"] = dict(self.meta)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LORARENA_BATTLE":
        return cls(**data)
