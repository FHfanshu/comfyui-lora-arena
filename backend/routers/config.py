"""
Config API Router

Handles system configuration and ComfyUI status.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from models.schemas import (
    ConfigResponse,
    ConfigUpdate,
    ComfyUIStatus,
    ComfyUIModelsResponse,
)
from config import get_config, load_runtime_config, save_runtime_config
from services.comfyui.client import ComfyUIClient

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
async def get_configuration():
    """Get current configuration"""
    config = get_config()
    return ConfigResponse(**config)


@router.put("", response_model=ConfigResponse)
async def update_configuration(data: ConfigUpdate):
    """Update configuration"""
    current = load_runtime_config()

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    current.update(update_data)

    save_runtime_config(current)

    # Return merged config
    config = get_config()
    return ConfigResponse(**config)


@router.get("/comfyui/status", response_model=ComfyUIStatus)
async def check_comfyui_status():
    """Check ComfyUI connection status"""
    config = get_config()
    url = config["comfyui_url"]

    client = ComfyUIClient(url)
    connected = await client.check_connection()

    return ComfyUIStatus(
        connected=connected,
        url=url,
        error=None if connected else "Cannot connect to ComfyUI server"
    )


@router.get("/comfyui/models", response_model=ComfyUIModelsResponse)
async def get_comfyui_models():
    """Get available models from ComfyUI"""
    config = get_config()
    client = ComfyUIClient(config["comfyui_url"])

    try:
        checkpoints = await client.get_available_checkpoints()
        loras = await client.get_available_loras()
        samplers = await client.get_available_samplers()

        return ComfyUIModelsResponse(
            checkpoints=checkpoints,
            loras=loras,
            samplers=samplers,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get models from ComfyUI: {str(e)}"
        )
