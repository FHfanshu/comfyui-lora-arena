"""
ComfyUI Workflow Builder

Builds ComfyUI workflow JSON for SDXL + LoRA image generation.
"""

import copy
from typing import Dict, Any, Optional


class WorkflowBuilder:
    """Builds ComfyUI workflow JSON for image generation"""

    # Base SDXL workflow template with LoRA support
    SDXL_LORA_WORKFLOW = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": 1,
                "height": 1024,
                "width": 1024
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["10", 1],
                "text": ""
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["10", 1],
                "text": ""
            }
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": 7,
                "denoise": 1,
                "latent_image": ["5", 0],
                "model": ["10", 0],
                "negative": ["7", 0],
                "positive": ["6", 0],
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "seed": 0,
                "steps": 20
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "arena",
                "images": ["8", 0]
            }
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "clip": ["4", 1],
                "lora_name": "",
                "model": ["4", 0],
                "strength_clip": 1.0,
                "strength_model": 1.0
            }
        }
    }

    def build(
        self,
        lora_name: str,
        prompt: str,
        negative_prompt: str = "",
        seed: int = 0,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler: str = "euler_ancestral",
        scheduler: str = "normal",
        lora_strength: float = 0.8,
        base_model: str = "sd_xl_base_1.0.safetensors",
        filename_prefix: str = "arena"
    ) -> Dict[str, Any]:
        """
        Build a complete workflow JSON.

        Args:
            lora_name: Name of the LoRA file
            prompt: Positive prompt
            negative_prompt: Negative prompt
            seed: Random seed for reproducibility
            width: Image width
            height: Image height
            steps: Number of sampling steps
            cfg_scale: CFG scale
            sampler: Sampler name
            scheduler: Scheduler name
            lora_strength: LoRA strength (applied to both model and clip)
            base_model: Base checkpoint model name
            filename_prefix: Prefix for output filename

        Returns:
            Complete workflow dictionary
        """
        workflow = copy.deepcopy(self.SDXL_LORA_WORKFLOW)

        # Set base model
        workflow["4"]["inputs"]["ckpt_name"] = base_model

        # Set LoRA
        workflow["10"]["inputs"]["lora_name"] = lora_name
        workflow["10"]["inputs"]["strength_model"] = lora_strength
        workflow["10"]["inputs"]["strength_clip"] = lora_strength

        # Set prompts
        workflow["6"]["inputs"]["text"] = prompt
        workflow["7"]["inputs"]["text"] = negative_prompt

        # Set generation parameters
        workflow["3"]["inputs"]["seed"] = seed
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["cfg"] = cfg_scale
        workflow["3"]["inputs"]["sampler_name"] = sampler
        workflow["3"]["inputs"]["scheduler"] = scheduler

        # Set image dimensions
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height

        # Set output filename
        workflow["9"]["inputs"]["filename_prefix"] = filename_prefix

        return workflow

    def build_without_lora(
        self,
        prompt: str,
        negative_prompt: str = "",
        seed: int = 0,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler: str = "euler_ancestral",
        scheduler: str = "normal",
        base_model: str = "sd_xl_base_1.0.safetensors",
        filename_prefix: str = "arena"
    ) -> Dict[str, Any]:
        """Build workflow without LoRA (base model only)"""
        # Simplified workflow without LoRA loader
        workflow = {
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": base_model
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt
                }
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg_scale,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "seed": seed,
                    "steps": steps
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix,
                    "images": ["8", 0]
                }
            }
        }

        return workflow


    def build_dual_lora(
        self,
        lora_name_left: str,
        lora_name_right: str,
        prompt: str,
        negative_prompt: str = "",
        seed: int = 0,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler: str = "euler_ancestral",
        scheduler: str = "normal",
        lora_strength: float = 0.8,
        base_model: str = "sd_xl_base_1.0.safetensors",
        filename_prefix_left: str = "arena_left",
        filename_prefix_right: str = "arena_right"
    ) -> Dict[str, Any]:
        """
        Build a dual-branch workflow that generates two images in one execution.

        This optimizes generation speed by:
        - Loading the base model only once (shared)
        - Loading both LoRAs simultaneously
        - Reducing HTTP request overhead

        Args:
            lora_name_left: LoRA file for left image
            lora_name_right: LoRA file for right image
            prompt: Positive prompt (shared)
            negative_prompt: Negative prompt (shared)
            seed: Random seed (shared for fair comparison)
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG scale
            sampler: Sampler name
            scheduler: Scheduler name
            lora_strength: LoRA strength
            base_model: Base checkpoint model
            filename_prefix_left: Output filename prefix for left image
            filename_prefix_right: Output filename prefix for right image

        Returns:
            Complete dual-branch workflow dictionary
        """
        workflow = {
            # Shared: Checkpoint Loader
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": base_model
                }
            },
            # Shared: Empty Latent Image
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },

            # ===== LEFT BRANCH =====
            # LoRA Loader (Left)
            "10": {
                "class_type": "LoraLoader",
                "inputs": {
                    "clip": ["4", 1],
                    "lora_name": lora_name_left,
                    "model": ["4", 0],
                    "strength_clip": lora_strength,
                    "strength_model": lora_strength
                }
            },
            # CLIP Text Encode Positive (Left)
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["10", 1],
                    "text": prompt
                }
            },
            # CLIP Text Encode Negative (Left)
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["10", 1],
                    "text": negative_prompt
                }
            },
            # KSampler (Left)
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg_scale,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["10", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "seed": seed,
                    "steps": steps
                }
            },
            # VAE Decode (Left)
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            # Save Image (Left)
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix_left,
                    "images": ["8", 0]
                }
            },

            # ===== RIGHT BRANCH =====
            # LoRA Loader (Right)
            "20": {
                "class_type": "LoraLoader",
                "inputs": {
                    "clip": ["4", 1],
                    "lora_name": lora_name_right,
                    "model": ["4", 0],
                    "strength_clip": lora_strength,
                    "strength_model": lora_strength
                }
            },
            # CLIP Text Encode Positive (Right)
            "16": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["20", 1],
                    "text": prompt
                }
            },
            # CLIP Text Encode Negative (Right)
            "17": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["20", 1],
                    "text": negative_prompt
                }
            },
            # KSampler (Right)
            "13": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg_scale,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["20", 0],
                    "negative": ["17", 0],
                    "positive": ["16", 0],
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "seed": seed,
                    "steps": steps
                }
            },
            # VAE Decode (Right)
            "18": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["13", 0],
                    "vae": ["4", 2]
                }
            },
            # Save Image (Right)
            "19": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix_right,
                    "images": ["18", 0]
                }
            }
        }

        return workflow


# Singleton instance
workflow_builder = WorkflowBuilder()
