"""
LoRArena Random Prompt Node - Randomly selects a prompt for battle.

Supports reading prompts from txt files in a directory.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Tuple

# Built-in prompt presets
DEFAULT_PROMPTS = [
    "masterpiece, best quality, 1girl, solo, looking at viewer",
    "masterpiece, best quality, 1girl, solo, smile, outdoors",
    "masterpiece, best quality, 1girl, solo, long hair, dress",
    "masterpiece, best quality, 1girl, solo, school uniform",
    "masterpiece, best quality, 1girl, solo, fantasy, magic",
]

DEFAULT_NEGATIVE = "lowres, bad anatomy, bad hands, text, error, worst quality"

# Track recently used prompts to avoid repetition
_used_prompts: list[str] = []
_MAX_HISTORY = 50  # Remember last N prompts


class LoRArenaRandomPrompt:
    """
    Randomly selects a prompt for LoRA battle testing.

    Reads prompts from txt files in the configured training_data_directory.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            },
            "optional": {
                "prompt_prefix": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
                "negative_prompt": ("STRING", {
                    "default": DEFAULT_NEGATIVE,
                    "multiline": True,
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("prompt", "negative", "seed")
    FUNCTION = "select_prompt"
    CATEGORY = "LoRArena"

    def select_prompt(
        self,
        seed: int,
        prompt_prefix: str = "",
        negative_prompt: str = DEFAULT_NEGATIVE,
    ) -> Tuple[str, str, int]:
        """Select a random prompt from training data directory."""
        original_seed = seed
        if seed == 0:
            seed = random.randint(0, 0xffffffffffffffff)

        print(f"[LoRArena] RandomPrompt: original_seed={original_seed}, actual_seed={seed}")

        gen = random.Random(seed)

        prompt_directory = self._load_config_training_directory()
        print(f"[LoRArena] RandomPrompt: training_data_directory = '{prompt_directory}'")
        prompt = self._from_directory(prompt_directory, gen)

        # Apply prefix if provided
        if prompt_prefix and prompt_prefix.strip():
            prompt = f"{prompt_prefix.strip()}, {prompt}"

        print(f"[LoRArena] RandomPrompt: Final prompt = '{prompt[:50]}...' (truncated)")
        return (prompt, negative_prompt, seed)

    def _from_directory(self, directory: str, gen: random.Random) -> str:
        """Read prompts from txt files in directory (recursive), avoiding recently used."""
        global _used_prompts

        if not directory or not os.path.isdir(directory):
            print(f"[LoRArena] RandomPrompt: Invalid prompt directory: '{directory}' (exists={os.path.isdir(directory) if directory else False})")
            return gen.choice(DEFAULT_PROMPTS)

        # Recursively find all txt files and sort for consistent ordering
        txt_files = sorted(Path(directory).rglob("*.txt"))
        print(f"[LoRArena] RandomPrompt: Found {len(txt_files)} txt files in '{directory}' (recursive)")

        if not txt_files:
            print(f"[LoRArena] No txt files found in {directory}")
            return gen.choice(DEFAULT_PROMPTS)

        # Filter out recently used files
        file_paths_str = [str(f) for f in txt_files]
        available_files = [f for f in file_paths_str if f not in _used_prompts]

        # If all files have been used, clear history and use all files
        if not available_files:
            print(f"[LoRArena] RandomPrompt: All {len(txt_files)} files used, clearing history")
            _used_prompts.clear()
            available_files = file_paths_str

        print(f"[LoRArena] RandomPrompt: {len(available_files)} available (excluded {len(file_paths_str) - len(available_files)} recently used)")

        # Shuffle and select first file
        gen.shuffle(available_files)
        selected_file = available_files[0]

        # Add to history
        _used_prompts.append(selected_file)
        if len(_used_prompts) > _MAX_HISTORY:
            _used_prompts.pop(0)

        file_name = Path(selected_file).name
        print(f"[LoRArena] RandomPrompt: Selected file = '{file_name}'")

        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            print(f"[LoRArena] RandomPrompt: Read {len(content)} chars from '{file_name}'")
            return content if content else gen.choice(DEFAULT_PROMPTS)
        except Exception as e:
            print(f"[LoRArena] Failed to read {selected_file}: {e}")
            return gen.choice(DEFAULT_PROMPTS)

    def _load_config_training_directory(self) -> str:
        """Load training_data_directory from LoRArena config if available."""
        try:
            config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                value = str(data.get("training_data_directory", "")).strip()
                return value
        except Exception:
            pass
        return ""

    @classmethod
    def IS_CHANGED(cls, seed, prompt_prefix=None, negative_prompt=None, **kwargs):
        """Only re-execute when seed=0 (random mode)."""
        if seed == 0:
            import time
            return time.time()  # Random mode: always change
        return seed  # Fixed seed: only change when seed changes
