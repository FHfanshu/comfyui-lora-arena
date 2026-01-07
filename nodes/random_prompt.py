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
        """Read prompts from txt files in directory."""
        if not directory or not os.path.isdir(directory):
            print(f"[LoRArena] RandomPrompt: Invalid prompt directory: '{directory}' (exists={os.path.isdir(directory) if directory else False})")
            return gen.choice(DEFAULT_PROMPTS)

        # Find all txt files and sort for consistent ordering
        txt_files = sorted([f for f in os.listdir(directory) if f.endswith(".txt")])
        print(f"[LoRArena] RandomPrompt: Found {len(txt_files)} txt files in '{directory}'")

        if not txt_files:
            print(f"[LoRArena] No txt files found in {directory}")
            return gen.choice(DEFAULT_PROMPTS)

        # Shuffle and select first file for true randomness
        gen.shuffle(txt_files)
        selected_file = txt_files[0]
        file_path = os.path.join(directory, selected_file)
        print(f"[LoRArena] RandomPrompt: Selected file = '{selected_file}'")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            print(f"[LoRArena] RandomPrompt: Read {len(content)} chars from '{selected_file}'")
            return content if content else gen.choice(DEFAULT_PROMPTS)
        except Exception as e:
            print(f"[LoRArena] Failed to read {file_path}: {e}")
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
