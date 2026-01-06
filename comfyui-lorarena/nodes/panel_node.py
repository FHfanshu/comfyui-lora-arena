"""
LoRArena Panel Node - Embeds React Arena UI inside a ComfyUI node.

This node requires model/clip/vae connections and displays the Arena
interface in an iframe widget.
"""

from __future__ import annotations

from ..services import model_state


class LoRArenaPanelNode:
    """
    Embeds the React Arena UI in a node.

    Requires model, clip, and vae inputs from a Checkpoint Loader.
    The embedded UI allows users to run LoRA battles and vote on results.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
            },
            "optional": {}
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("winner_lora", "battle_stats")
    FUNCTION = "run"
    CATEGORY = "LoRArena"
    OUTPUT_NODE = True

    def run(self, model, clip, vae):
        """
        Execute the panel node.

        Saves model references to global state for use by the Arena API,
        then returns the last vote result.
        """
        # Save model references for API to use
        model_state.set_models(model, clip, vae)

        # Return the last vote result (if any)
        return model_state.get_last_result()
