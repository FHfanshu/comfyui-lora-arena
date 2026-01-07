from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Tuple

from ..services import db_manager, matchmaking_service
from .battle_types import LORARENA_BATTLE


class LoRArenaMatchmaker:
    """Select two LoRAs for a battle.

    Supports two sources:
    - database: Use ELO-based matchmaking from the database
    - directory: Scan directory directly for random selection
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": (["database", "directory"],),
                "strategy": (["balanced", "random", "exploration"],),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "LORARENA_BATTLE")
    RETURN_NAMES = ("lora_a", "lora_b", "battle_id", "battle_info")
    FUNCTION = "select"
    CATEGORY = "LoRArena"

    def select(self, source: str, strategy: str, seed: int):
        actual_seed = seed if seed else random.randint(0, 0xffffffffffffffff)
        gen = random.Random(actual_seed)

        if source == "directory":
            lora_left, lora_right = self._select_from_directory(gen)
            battle = LORARENA_BATTLE(
                battle_id=0,
                left_checkpoint_id=0,
                right_checkpoint_id=0,
                lora_left=lora_left,
                lora_right=lora_right,
                left_name=Path(lora_left).stem if lora_left else "",
                right_name=Path(lora_right).stem if lora_right else "",
                seed=actual_seed,
            )
        else:
            # Database matchmaking
            if seed:
                random.seed(seed)
            with db_manager.session_scope() as db:
                left, right = matchmaking_service.select_matchup(db, strategy=strategy)

            battle = LORARENA_BATTLE(
                battle_id=0,
                left_checkpoint_id=left.id,
                right_checkpoint_id=right.id,
                lora_left=left.filename,
                lora_right=right.filename,
                left_name=left.name,
                right_name=right.name,
                seed=actual_seed,
            )

        return (battle.lora_left, battle.lora_right, battle.battle_id, battle)

    def _select_from_directory(self, gen: random.Random) -> Tuple[str, str]:
        """Scan directory for LoRA files and select two randomly."""
        lora_subdir = self._load_config_lora_directory()
        print(f"[LoRArena] Matchmaker: lora_directory from config = '{lora_subdir}'")

        try:
            import folder_paths
            all_lora_paths = folder_paths.get_folder_paths("loras")
        except Exception as e:
            print(f"[LoRArena] Cannot get ComfyUI loras folder: {e}")
            return "", ""

        if not all_lora_paths:
            print("[LoRArena] No lora paths registered in ComfyUI")
            return "", ""

        lora_base = all_lora_paths[0]

        if os.path.isabs(lora_subdir):
            full_dir = lora_subdir
        else:
            full_dir = os.path.join(lora_base, lora_subdir) if lora_subdir else lora_base

        if not os.path.isdir(full_dir):
            print(f"[LoRArena] Invalid directory: {full_dir}")
            return "", ""

        # Find all LoRA files
        lora_extensions = {".safetensors", ".pt", ".ckpt"}
        lora_files = [f for f in os.listdir(full_dir) if Path(f).suffix.lower() in lora_extensions]

        print(f"[LoRArena] Matchmaker: Found {len(lora_files)} LoRA files in {full_dir}")

        if len(lora_files) < 2:
            print(f"[LoRArena] Need at least 2 LoRA files, found {len(lora_files)}")
            return "", ""

        # Sort for consistent ordering, then shuffle
        lora_files.sort()
        gen.shuffle(lora_files)
        selected = lora_files[:2]

        # Build relative path for LoRA Loader
        relative_dir = lora_subdir
        if os.path.isabs(lora_subdir):
            for base_path in all_lora_paths:
                try:
                    rel = os.path.relpath(full_dir, base_path)
                    if not rel.startswith(".."):
                        relative_dir = rel
                        break
                except Exception:
                    continue

        if relative_dir:
            relative_dir = relative_dir.replace("/", "\\").rstrip("\\")
            lora_a = f"{relative_dir}\\{selected[0]}"
            lora_b = f"{relative_dir}\\{selected[1]}"
        else:
            lora_a, lora_b = selected[0], selected[1]

        print(f"[LoRArena] Matchmaker: Selected lora_a = '{lora_a}', lora_b = '{lora_b}'")
        return lora_a, lora_b

    def _load_config_lora_directory(self) -> str:
        """Load lora_directory from LoRArena config if available."""
        try:
            config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                return str(data.get("lora_directory", "")).strip()
        except Exception:
            pass
        return ""

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        """Always re-execute to select new random LoRAs each time."""
        import time
        return time.time()
