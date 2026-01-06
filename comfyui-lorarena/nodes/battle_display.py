"""
LoRArena Battle Display Node - Displays two images for A/B comparison voting.

This node receives two images and their LoRA names, displays them in an
iframe widget for user voting.
"""

from __future__ import annotations

import base64
import io
import uuid
from typing import Any, Tuple

import numpy as np
from PIL import Image


class LoRArenaBattleDisplay:
    """
    Displays two LoRA-generated images for A/B comparison voting.

    Inputs:
    - image_a: First image (from LoRA A)
    - image_b: Second image (from LoRA B)
    - lora_name_a: Name/path of LoRA A
    - lora_name_b: Name/path of LoRA B

    Output:
    - winner: Vote result ("a", "b", "tie", "skip")
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
                "lora_name_a": ("STRING", {"default": "LoRA A"}),
                "lora_name_b": ("STRING", {"default": "LoRA B"}),
            },
            "optional": {
                "trigger": ("*",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("winner",)
    FUNCTION = "display_battle"
    CATEGORY = "LoRArena"
    OUTPUT_NODE = True

    def display_battle(
        self,
        image_a: Any,
        image_b: Any,
        lora_name_a: str,
        lora_name_b: str,
        trigger=None,
    ) -> Tuple[str]:
        """
        Display battle images and wait for user vote.

        Converts images to base64, stores in battle_state, and waits
        for user to vote via the iframe widget.
        """
        from ..services import battle_state

        # Convert tensor images to base64
        image_a_b64 = self._tensor_to_base64(image_a, "image_a")
        image_b_b64 = self._tensor_to_base64(image_b, "image_b")

        # Generate unique battle ID
        battle_id = str(uuid.uuid4())[:8]

        # Set battle state for iframe to display
        battle_state.set_battle(
            battle_id=battle_id,
            image_a_base64=image_a_b64,
            image_b_base64=image_b_b64,
            lora_name_a=lora_name_a,
            lora_name_b=lora_name_b,
        )

        # Return immediately - voting happens asynchronously via iframe
        # The winner will be available via battle_state.get_winner()
        # For now, return empty string as placeholder
        return ("",)

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        # Always run to refresh battle state even if outputs are cached.
        import time
        return time.time()

    def _tensor_to_base64(self, tensor: Any, name: str) -> str:
        """Convert ComfyUI image tensor to base64 PNG string."""
        if tensor is None:
            raise RuntimeError(
                f"{name} is empty. Connect VAE Decode outputs to image inputs."
            )
        # ComfyUI images are [B, H, W, C] float tensors in range [0, 1]
        if hasattr(tensor, "cpu"):
            tensor = tensor.cpu()
        if hasattr(tensor, "numpy"):
            arr = tensor.numpy()
        else:
            arr = np.array(tensor)

        # Take first image if batch
        if len(arr.shape) == 4:
            arr = arr[0]

        # Ensure HWC layout
        if len(arr.shape) == 3 and arr.shape[-1] not in (1, 3, 4):
            if arr.shape[0] in (1, 3, 4):
                arr = np.transpose(arr, (1, 2, 0))
            else:
                raise RuntimeError(
                    f"{name} is not an IMAGE tensor. "
                    "Make sure you connect VAE Decode, not LATENT."
                )

        # Convert to uint8
        arr = (arr * 255).clip(0, 255).astype(np.uint8)

        # Create PIL image
        img = Image.fromarray(arr)

        # Encode to base64 PNG
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{b64}"
