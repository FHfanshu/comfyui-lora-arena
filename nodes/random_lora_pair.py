"""
LoRArena Random LoRA Pair Node - Randomly selects two LoRAs for battle.

Supports scanning from a specified directory or using database matchmaking.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Tuple


class LoRArenaRandomLoraPair:
    """
    Randomly selects two LoRAs for A/B comparison battle.

    Scans a subdirectory under ComfyUI's loras folder.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("lora_a", "lora_b", "seed")
    FUNCTION = "select_pair"
    CATEGORY = "LoRArena"

    def select_pair(
        self,
        seed: int,
    ) -> Tuple[str, str, int]:
        """Select a random pair of LoRAs from directory."""
        if seed == 0:
            seed = random.randint(0, 0xffffffffffffffff)

        gen = random.Random(seed)

        lora_a, lora_b = self._scan_directory(gen)
        return (lora_a, lora_b, seed)

    def _scan_directory(self, gen: random.Random) -> Tuple[str, str]:
        """Scan directory for LoRA files and select two randomly."""
        lora_subdir = self._load_config_lora_directory()
        print(f"[LoRArena] RandomLoraPair: lora_directory from config = '{lora_subdir}'")

        try:
            import folder_paths
            lora_base = folder_paths.get_folder_paths("loras")[0]
            print(f"[LoRArena] RandomLoraPair: ComfyUI loras base = '{lora_base}'")
        except Exception as e:
            print(f"[LoRArena] Cannot get ComfyUI loras folder: {e}")
            return "", ""

        if os.path.isabs(lora_subdir):
            full_dir = lora_subdir
            print(f"[LoRArena] RandomLoraPair: Using absolute path = '{full_dir}'")
        else:
            full_dir = os.path.join(lora_base, lora_subdir) if lora_subdir else lora_base
            print(f"[LoRArena] RandomLoraPair: Using relative path, full_dir = '{full_dir}'")

        if not os.path.isdir(full_dir):
            print(f"[LoRArena] Invalid directory: {full_dir}")
            return "", ""

        # Find all LoRA files
        lora_extensions = {".safetensors", ".pt", ".ckpt"}
        lora_files = []

        for f in os.listdir(full_dir):
            if Path(f).suffix.lower() in lora_extensions:
                lora_files.append(f)

        print(f"[LoRArena] RandomLoraPair: Found {len(lora_files)} LoRA files in {full_dir}")

        if len(lora_files) < 2:
            print(f"[LoRArena] Need at least 2 LoRA files, found {len(lora_files)}")
            return "", ""

        # Sort for consistent ordering, then shuffle for true randomness
        lora_files.sort()
        gen.shuffle(lora_files)

        # Select first two from shuffled list
        selected = lora_files[:2]
        print(f"[LoRArena] RandomLoraPair: Selected files = {selected}")

        # Return relative path for LoRA Loader (e.g., "748\\xxx.safetensors")
        relative_dir = lora_subdir
        if os.path.isabs(lora_subdir):
            try:
                relative_dir = os.path.relpath(full_dir, lora_base)
                print(f"[LoRArena] RandomLoraPair: Computed relative_dir = '{relative_dir}'")
                if relative_dir.startswith(".."):
                    print(f"[LoRArena] Directory '{full_dir}' is NOT under ComfyUI loras path '{lora_base}'")
                    print(f"[LoRArena] Please ensure your LoRA directory is under ComfyUI's models/loras folder")
                    return "", ""
            except Exception as e:
                print(f"[LoRArena] Failed to compute relative path: {e}")
                relative_dir = ""

        if relative_dir:
            relative_dir = relative_dir.replace("/", "\\").rstrip("\\")
            lora_a = f"{relative_dir}\\{selected[0]}"
            lora_b = f"{relative_dir}\\{selected[1]}"
        else:
            lora_a, lora_b = selected[0], selected[1]

        print(f"[LoRArena] RandomLoraPair: Final lora_a = '{lora_a}', lora_b = '{lora_b}'")
        return lora_a, lora_b

    def _load_config_lora_directory(self) -> str:
        """Load lora_directory from LoRArena config if available."""
        try:
            config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                value = str(data.get("lora_directory", "")).strip()
                return value
        except Exception:
            pass
        return ""

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        """Always re-execute to select new random LoRAs each time."""
        import time
        return time.time()
