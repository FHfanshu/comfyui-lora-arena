from __future__ import annotations

import json
from typing import Tuple

from sqlalchemy import select

from ..services import battle_service, db_manager
from ..services.models import Checkpoint
from .battle_types import LORARENA_BATTLE


class LoRArenaBattleGenerator:
    """Generate two images using two LoRAs for comparison."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "battle_info": ("LORARENA_BATTLE",),
                "prompt": ("STRING", {"default": ""}),
                "negative_prompt": ("STRING", {"default": ""}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 200}),
                "cfg_scale": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0}),
                "sampler": ("STRING", {"default": "euler_ancestral"}),
                "scheduler": ("STRING", {"default": "normal"}),
                "lora_strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 2.0}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "LORARENA_BATTLE")
    RETURN_NAMES = ("image_a", "image_b", "battle_info")
    FUNCTION = "generate"
    CATEGORY = "LoRArena"

    def _load_lora(self, lora_name: str):
        import folder_paths
        import comfy.utils

        lora_path = folder_paths.get_full_path("loras", lora_name)
        if not lora_path:
            raise RuntimeError(f"LoRA not found: {lora_name}")
        return comfy.utils.load_torch_file(lora_path, safe_load=True)

    def _apply_lora(self, model, clip, lora_name: str, strength: float):
        import comfy.sd

        lora = self._load_lora(lora_name)
        return comfy.sd.load_lora_for_models(model, clip, lora, strength, strength)

    def _encode(self, clip, text: str):
        import nodes

        return nodes.CLIPTextEncode().encode(clip, text)[0]

    def _make_latent(self, width: int, height: int):
        import nodes

        return nodes.EmptyLatentImage().generate(width, height, 1)[0]

    def _sample(
        self,
        model,
        positive,
        negative,
        latent,
        seed: int,
        steps: int,
        cfg: float,
        sampler: str,
        scheduler: str,
    ):
        import nodes

        return nodes.common_ksampler(
            model,
            seed,
            steps,
            cfg,
            sampler,
            scheduler,
            positive,
            negative,
            latent,
        )[0]

    def _decode(self, vae, latent):
        import nodes

        return nodes.VAEDecode().decode(vae, latent)[0]

    def generate(
        self,
        model,
        clip,
        vae,
        battle_info: LORARENA_BATTLE,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        sampler: str,
        scheduler: str,
        lora_strength: float,
    ) -> Tuple:
        if isinstance(battle_info, dict):
            battle = LORARENA_BATTLE.from_dict(battle_info)
        else:
            battle = battle_info

        if not battle.lora_left or not battle.lora_right:
            raise RuntimeError("Battle info missing LoRA names")

        seed = battle.seed or 0
        if seed == 0:
            seed = 1

        battle.prompt = prompt
        battle.negative_prompt = negative_prompt
        battle.width = width
        battle.height = height
        battle.steps = steps
        battle.cfg_scale = cfg_scale
        battle.sampler = sampler
        battle.scheduler = scheduler
        battle.lora_strength = lora_strength

        battle_id = battle.battle_id
        with db_manager.session_scope() as db:
            left = db.execute(
                select(Checkpoint).where(Checkpoint.id == battle.left_checkpoint_id)
            ).scalar_one_or_none()
            right = db.execute(
                select(Checkpoint).where(Checkpoint.id == battle.right_checkpoint_id)
            ).scalar_one_or_none()

            if left is None or right is None:
                raise RuntimeError("Checkpoint records missing for battle")

            if battle_id:
                record = battle_service.get_battle(db, battle_id)
                if record is None:
                    battle_id = 0

            if not battle_id:
                record = battle_service.create_battle(
                    db,
                    left,
                    right,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    width=width,
                    height=height,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    sampler=sampler,
                    lora_strength=lora_strength,
                    base_model=left.base_model or right.base_model,
                )
                battle_id = record.id

            record = battle_service.get_battle(db, battle_id)
            if record:
                record.status = "generating"
                db.commit()

        try:
            model_left, clip_left = self._apply_lora(model, clip, battle.lora_left, lora_strength)
            model_right, clip_right = self._apply_lora(model, clip, battle.lora_right, lora_strength)

            latent = self._make_latent(width, height)

            positive_left = self._encode(clip_left, prompt)
            negative_left = self._encode(clip_left, negative_prompt)
            samples_left = self._sample(
                model_left,
                positive_left,
                negative_left,
                latent,
                seed,
                steps,
                cfg_scale,
                sampler,
                scheduler,
            )
            image_left = self._decode(vae, samples_left)

            positive_right = self._encode(clip_right, prompt)
            negative_right = self._encode(clip_right, negative_prompt)
            samples_right = self._sample(
                model_right,
                positive_right,
                negative_right,
                latent,
                seed,
                steps,
                cfg_scale,
                sampler,
                scheduler,
            )
            image_right = self._decode(vae, samples_right)

            status = "completed"
            error_message = None
        except Exception as exc:
            image_left = None
            image_right = None
            status = "failed"
            error_message = str(exc)

        with db_manager.session_scope() as db:
            record = battle_service.get_battle(db, battle_id)
            if record:
                record.status = status
                record.error_message = error_message
                db.commit()

        battle.battle_id = battle_id
        battle.meta["status"] = status
        if error_message:
            battle.meta["error"] = error_message

        if image_left is None or image_right is None:
            raise RuntimeError(
                f"Battle generation failed: {json.dumps(battle.meta, ensure_ascii=False)}"
            )

        return (image_left, image_right, battle)
