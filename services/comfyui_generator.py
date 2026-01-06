"""
ComfyUI Internal Image Generator.

Uses ComfyUI's internal Python API to generate images without HTTP calls.
This is used when the plugin runs inside ComfyUI as a custom node package.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# Check if running inside ComfyUI
try:
    import folder_paths
    import comfy.sd
    import comfy.utils
    import comfy.samplers
    import comfy.sample
    import comfy.model_management
    from nodes import (
        CheckpointLoaderSimple,
        LoraLoader,
        CLIPTextEncode,
        EmptyLatentImage,
        VAEDecode,
    )
    COMFYUI_AVAILABLE = True
except ImportError:
    COMFYUI_AVAILABLE = False
    logger.warning("[LoRArena] ComfyUI modules not available, internal generation disabled")


class ComfyUIGenerator:
    """
    Internal ComfyUI image generator.
    Directly uses ComfyUI's Python API instead of HTTP calls.
    """

    def __init__(self):
        self._model_cache = {}
        self._output_dir = None

    def get_output_dir(self) -> Path:
        """Get the output directory for generated images."""
        if self._output_dir is None:
            if COMFYUI_AVAILABLE:
                self._output_dir = Path(folder_paths.get_output_directory())
            else:
                self._output_dir = Path(__file__).parent.parent / "output"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir

    def is_available(self) -> bool:
        """Check if ComfyUI internal generation is available."""
        return COMFYUI_AVAILABLE

    def generate_battle_images(
        self,
        lora_left: str,
        lora_right: str,
        prompt: str,
        negative_prompt: str = "",
        seed: int = 0,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler_name: str = "euler_ancestral",
        scheduler: str = "normal",
        lora_strength: float = 0.8,
        base_model: str = "",
        battle_id: int = 0,
        use_node_models: bool = True,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate two images using different LoRAs with the same parameters.

        Args:
            use_node_models: If True, use models from node state instead of loading from base_model.

        Returns:
            Tuple of (left_image_path, right_image_path) or (None, None) on failure.
        """
        if not COMFYUI_AVAILABLE:
            logger.error("[LoRArena] ComfyUI not available for internal generation")
            return None, None

        try:
            # Try to use models from node state first
            if use_node_models:
                from . import model_state
                if model_state.has_models():
                    models = model_state.get_models()
                    model = models["model"]
                    clip = models["clip"]
                    vae = models["vae"]
                    logger.info("[LoRArena] Using models from node state")
                else:
                    logger.warning("[LoRArena] Node models not available, falling back to checkpoint loading")
                    use_node_models = False

            # Fall back to loading from checkpoint
            if not use_node_models:
                if not base_model:
                    logger.error("[LoRArena] No base model specified and no node models available")
                    return None, None
                checkpoint_loader = CheckpointLoaderSimple()
                model, clip, vae = checkpoint_loader.load_checkpoint(base_model)

            # Create empty latent
            latent_creator = EmptyLatentImage()
            latent = latent_creator.generate(width, height, 1)[0]

            # Generate left image
            left_path = self._generate_single_image(
                model, clip, vae, latent,
                lora_name=lora_left,
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                steps=steps,
                cfg=cfg_scale,
                sampler_name=sampler_name,
                scheduler=scheduler,
                lora_strength=lora_strength,
                filename_prefix=f"battle_{battle_id}_left",
            )

            # Generate right image (with same seed for fair comparison)
            right_path = self._generate_single_image(
                model, clip, vae, latent,
                lora_name=lora_right,
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                steps=steps,
                cfg=cfg_scale,
                sampler_name=sampler_name,
                scheduler=scheduler,
                lora_strength=lora_strength,
                filename_prefix=f"battle_{battle_id}_right",
            )

            return left_path, right_path

        except Exception as e:
            logger.error(f"[LoRArena] Failed to generate battle images: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def _generate_single_image(
        self,
        model,
        clip,
        vae,
        latent,
        lora_name: str,
        prompt: str,
        negative_prompt: str,
        seed: int,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
        lora_strength: float,
        filename_prefix: str,
    ) -> Optional[str]:
        """Generate a single image with the given LoRA."""
        try:
            # Load LoRA
            lora_loader = LoraLoader()
            model_lora, clip_lora = lora_loader.load_lora(
                model, clip, lora_name, lora_strength, lora_strength
            )

            # Encode prompts
            text_encoder = CLIPTextEncode()
            positive = text_encoder.encode(clip_lora, prompt)[0]
            negative = text_encoder.encode(clip_lora, negative_prompt)[0]

            # Use comfy.sample directly instead of KSampler node to avoid callback issues
            # Get the latent tensor
            latent_image = latent["samples"]
            batch_size = latent_image.shape[0]

            # Generate noise
            import torch
            if seed == 0:
                seed = torch.randint(0, 2**32 - 1, (1,)).item()
            generator = torch.Generator(device="cpu").manual_seed(seed)
            noise = torch.randn(latent_image.shape, generator=generator, device="cpu")

            # Load model to GPU
            comfy.model_management.load_model_gpu(model_lora)

            # Get sampler and sigmas
            sampler_obj = comfy.samplers.KSampler(
                model_lora, steps=steps, device=comfy.model_management.get_torch_device(),
                sampler=sampler_name, scheduler=scheduler, denoise=1.0
            )

            # Sample without callback (disable_pbar=True to avoid the callback issue)
            samples = sampler_obj.sample(
                noise, positive, negative,
                cfg=cfg, latent_image=latent_image,
                start_step=0, last_step=steps,
                force_full_denoise=True, denoise_mask=None,
                callback=None, disable_pbar=True, seed=seed
            )

            # Decode
            decoder = VAEDecode()
            images = decoder.decode(vae, {"samples": samples})[0]

            # Save image
            output_path = self._save_image(images, filename_prefix)
            return output_path

        except Exception as e:
            logger.error(f"[LoRArena] Failed to generate image with LoRA {lora_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _save_image(self, images, filename_prefix: str) -> Optional[str]:
        """Save generated image to output directory."""
        try:
            from PIL import Image
            import numpy as np

            output_dir = self.get_output_dir()

            # Convert tensor to PIL Image
            # images is expected to be a tensor of shape [batch, height, width, channels]
            for i, image in enumerate(images):
                # Convert to numpy and then to PIL
                if hasattr(image, 'cpu'):
                    image_np = image.cpu().numpy()
                else:
                    image_np = np.array(image)

                # Ensure values are in 0-255 range
                if image_np.max() <= 1.0:
                    image_np = (image_np * 255).astype(np.uint8)
                else:
                    image_np = image_np.astype(np.uint8)

                pil_image = Image.fromarray(image_np)

                # Generate unique filename
                filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.png"
                filepath = output_dir / filename

                pil_image.save(filepath)
                logger.info(f"[LoRArena] Saved image to {filepath}")

                # Return relative path for web serving
                return f"/view?filename={filename}&type=output"

        except Exception as e:
            logger.error(f"[LoRArena] Failed to save image: {e}")
            import traceback
            traceback.print_exc()
            return None


# Async wrapper for use in aiohttp routes
async def generate_battle_images_async(
    lora_left: str,
    lora_right: str,
    prompt: str,
    negative_prompt: str = "",
    seed: int = 0,
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler_name: str = "euler_ancestral",
    scheduler: str = "normal",
    lora_strength: float = 0.8,
    base_model: str = "",
    battle_id: int = 0,
) -> Tuple[Optional[str], Optional[str]]:
    """Async wrapper for image generation."""
    generator = ComfyUIGenerator()

    # Run in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        generator.generate_battle_images,
        lora_left,
        lora_right,
        prompt,
        negative_prompt,
        seed,
        width,
        height,
        steps,
        cfg_scale,
        sampler_name,
        scheduler,
        lora_strength,
        base_model,
        battle_id,
    )


# Singleton instance
comfyui_generator = ComfyUIGenerator()
