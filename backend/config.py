from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import json
import logging
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = "sqlite+aiosqlite:///./lorarena.db"

    # ComfyUI
    comfyui_url: str = "http://localhost:8188"

    # LoRA directory (can be overridden via config)
    lora_directory: str = ""

    # Default generation parameters
    default_base_model: str = "sd_xl_base_1.0.safetensors"
    default_steps: int = 20
    default_cfg_scale: float = 7.0
    default_sampler: str = "euler_ancestral"
    default_scheduler: str = "normal"
    default_lora_strength: float = 0.8
    default_width: int = 1024
    default_height: int = 1024

    # ELO settings
    default_elo_rating: float = 1500.0
    default_k_factor: float = 32.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Config file path for runtime settings
CONFIG_FILE = Path(__file__).parent / "config.json"
logger = logging.getLogger(__name__)


def load_runtime_config() -> dict:
    """Load runtime configuration from JSON file"""
    if not CONFIG_FILE.exists():
        logger.info("Runtime config not found at %s; using defaults", CONFIG_FILE)
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.warning("Runtime config invalid JSON at %s: %s", CONFIG_FILE, exc)
        return {}
    except OSError as exc:
        logger.warning("Failed to read runtime config at %s: %s", CONFIG_FILE, exc)
        return {}

    keys = ", ".join(sorted(data.keys())) if isinstance(data, dict) else "non-dict"
    logger.info("Loaded runtime config from %s (keys: %s)", CONFIG_FILE, keys)
    return data if isinstance(data, dict) else {}


def save_runtime_config(config: dict) -> None:
    """Save runtime configuration to JSON file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Failed to save runtime config to %s: %s", CONFIG_FILE, exc)
        raise

    keys = ", ".join(sorted(config.keys())) if isinstance(config, dict) else "non-dict"
    logger.info("Saved runtime config to %s (keys: %s)", CONFIG_FILE, keys)


def get_config() -> dict:
    """Get merged configuration (env + runtime)"""
    settings = Settings()
    runtime = load_runtime_config()

    merged = {
        "comfyui_url": runtime.get("comfyui_url", settings.comfyui_url),        
        "lora_directory": runtime.get("lora_directory", settings.lora_directory),
        "base_model": runtime.get("base_model", settings.default_base_model),   
        "steps": runtime.get("steps", settings.default_steps),
        "cfg_scale": runtime.get("cfg_scale", settings.default_cfg_scale),      
        "sampler": runtime.get("sampler", settings.default_sampler),
        "scheduler": runtime.get("scheduler", settings.default_scheduler),      
        "lora_strength": runtime.get("lora_strength", settings.default_lora_strength),
        "width": runtime.get("width", settings.default_width),
        "height": runtime.get("height", settings.default_height),
        # TIPO and Worker settings
        "tipo_tag_length": runtime.get("tipo_tag_length", "long"),
        "tipo_use_gguf": runtime.get("tipo_use_gguf", True),
        "tipo_model_repo": runtime.get("tipo_model_repo", "KBlueLeaf/TIPO-500M"),
        "tipo_gguf_filename": runtime.get("tipo_gguf_filename", "TIPO-500M_epoch5-F16.gguf"),
        "models_cache_dir": runtime.get("models_cache_dir", str(Path(__file__).parent / "models")),
        "worker_enabled": runtime.get("worker_enabled", True),
        "worker_interval": runtime.get("worker_interval", 10),
        "worker_target_cache": runtime.get("worker_target_cache", 5),
        "worker_use_training_tags": runtime.get("worker_use_training_tags", False),
        "parallel_generation": runtime.get("parallel_generation", True),
        # Battle Royale settings
        "battle_royale_enabled": runtime.get("battle_royale_enabled", False),
        "battle_royale_threshold": runtime.get("battle_royale_threshold", 10),
        "battle_royale_win_rate": runtime.get("battle_royale_win_rate", 0.5),
        # Remote ComfyUI mode
        "remote_comfyui": runtime.get("remote_comfyui", False),
        # Training data directory for tag extraction
        "training_data_directory": runtime.get("training_data_directory", ""),
    }
    logger.debug(
        "Merged config comfyui_url=%s base_model=%s lora_directory=%s",
        merged.get("comfyui_url"),
        merged.get("base_model"),
        merged.get("lora_directory"),
    )
    return merged


settings = Settings()
