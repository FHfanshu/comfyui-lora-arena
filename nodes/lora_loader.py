from __future__ import annotations

from pathlib import Path
from typing import Tuple


class LoRArenaLoraLoader:
    """Load a LoRA by name from a string input."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "lora_name": ("STRING", {"default": ""}),
                "strength_model": (
                    "FLOAT",
                    {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01},
                ),
                "strength_clip": (
                    "FLOAT",
                    {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "load"
    CATEGORY = "LoRArena"

    def load(
        self,
        model,
        clip,
        lora_name: str,
        strength_model: float,
        strength_clip: float,
    ) -> Tuple:
        if not lora_name:
            return (model, clip)

        import folder_paths
        import comfy.sd
        import comfy.utils

        lora_path = None
        candidate = Path(lora_name)
        if candidate.is_absolute() and candidate.exists():
            lora_path = str(candidate)
        else:
            lora_path = folder_paths.get_full_path("loras", lora_name)
            if not lora_path and candidate.is_absolute():
                for base_dir in folder_paths.get_folder_paths("loras"):
                    base = Path(base_dir)
                    try:
                        rel = candidate.relative_to(base)
                    except Exception:
                        continue
                    lora_path = folder_paths.get_full_path("loras", str(rel))
                    if lora_path:
                        break

        if not lora_path:
            raise RuntimeError(f"LoRA not found: {lora_name}")

        lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
        return comfy.sd.load_lora_for_models(
            model,
            clip,
            lora,
            strength_model,
            strength_clip,
        )
