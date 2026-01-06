"""
Checkpoints API Router

Handles checkpoint management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from db.session import get_db
from models.schemas import (
    CheckpointResponse,
    CheckpointListResponse,
    CheckpointUpdate,
    ScanRequest,
    ScanResponse,
    BatchDeleteRequest,
    BatchStatusRequest,
)
from services.checkpoint_service import checkpoint_service
from services.training_data_service import training_data_service
from config import get_config

router = APIRouter(prefix="/api/checkpoints", tags=["checkpoints"])


@router.post("/scan", response_model=ScanResponse)
async def scan_lora_directory(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan a directory for LoRA files and import new checkpoints.

    If no directory is specified, uses the configured LoRA directory.
    """
    config = get_config()
    directory = request.directory or config.get("lora_directory")

    if not directory:
        raise HTTPException(
            status_code=400,
            detail="No directory specified and no default configured"
        )

    # Get available loras from ComfyUI to match names
    available_loras = []
    try:
        from services.comfyui.client import ComfyUIClient
        client = ComfyUIClient(config["comfyui_url"])
        available_loras = await client.get_available_loras()
    except Exception as e:
        # Continue without available loras if ComfyUI is not reachable
        pass

    remote_mode = config.get("remote_comfyui", False)
    return await checkpoint_service.scan_directory(db, directory, available_loras, remote_mode)


@router.get("", response_model=CheckpointListResponse)
async def list_checkpoints(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("elo_rating", pattern="^(elo_rating|name|total_battles|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    active_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of checkpoints"""
    checkpoints, total = await checkpoint_service.list_checkpoints(
        db, page, limit, sort_by, sort_order, active_only
    )

    items = [
        CheckpointResponse(
            id=c.id,
            name=c.name,
            filename=c.filename,
            file_path=c.file_path,
            description=c.description,
            trigger_words=c.trigger_words or [],
            tags=c.tags or [],
            training_data_path=c.training_data_path,
            elo_rating=c.elo_rating,
            total_battles=c.total_battles,
            wins=c.wins,
            losses=c.losses,
            ties=c.ties,
            win_rate=c.win_rate,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in checkpoints
    ]

    return CheckpointListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(
    checkpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a single checkpoint by ID"""
    checkpoint = await checkpoint_service.get_checkpoint(db, checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return CheckpointResponse(
        id=checkpoint.id,
        name=checkpoint.name,
        filename=checkpoint.filename,
        file_path=checkpoint.file_path,
        description=checkpoint.description,
        trigger_words=checkpoint.trigger_words or [],
        tags=checkpoint.tags or [],
        training_data_path=checkpoint.training_data_path,
        elo_rating=checkpoint.elo_rating,
        total_battles=checkpoint.total_battles,
        wins=checkpoint.wins,
        losses=checkpoint.losses,
        ties=checkpoint.ties,
        win_rate=checkpoint.win_rate,
        is_active=checkpoint.is_active,
        created_at=checkpoint.created_at,
        updated_at=checkpoint.updated_at,
    )


@router.put("/{checkpoint_id}", response_model=CheckpointResponse)
async def update_checkpoint(
    checkpoint_id: int,
    data: CheckpointUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update checkpoint metadata"""
    checkpoint = await checkpoint_service.update_checkpoint(db, checkpoint_id, data)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return CheckpointResponse(
        id=checkpoint.id,
        name=checkpoint.name,
        filename=checkpoint.filename,
        file_path=checkpoint.file_path,
        description=checkpoint.description,
        trigger_words=checkpoint.trigger_words or [],
        tags=checkpoint.tags or [],
        training_data_path=checkpoint.training_data_path,
        elo_rating=checkpoint.elo_rating,
        total_battles=checkpoint.total_battles,
        wins=checkpoint.wins,
        losses=checkpoint.losses,
        ties=checkpoint.ties,
        win_rate=checkpoint.win_rate,
        is_active=checkpoint.is_active,
        created_at=checkpoint.created_at,
        updated_at=checkpoint.updated_at,
    )


@router.patch("/{checkpoint_id}/toggle", response_model=CheckpointResponse)
async def toggle_checkpoint_active(
    checkpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Toggle checkpoint active status"""
    checkpoint = await checkpoint_service.toggle_active(db, checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return CheckpointResponse(
        id=checkpoint.id,
        name=checkpoint.name,
        filename=checkpoint.filename,
        file_path=checkpoint.file_path,
        description=checkpoint.description,
        trigger_words=checkpoint.trigger_words or [],
        tags=checkpoint.tags or [],
        training_data_path=checkpoint.training_data_path,
        elo_rating=checkpoint.elo_rating,
        total_battles=checkpoint.total_battles,
        wins=checkpoint.wins,
        losses=checkpoint.losses,
        ties=checkpoint.ties,
        win_rate=checkpoint.win_rate,
        is_active=checkpoint.is_active,
        created_at=checkpoint.created_at,
        updated_at=checkpoint.updated_at,
    )


@router.delete("/{checkpoint_id}")
async def delete_checkpoint(
    checkpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a checkpoint"""
    success = await checkpoint_service.delete_checkpoint(db, checkpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return {"success": True, "message": "Checkpoint deleted"}


@router.post("/batch-delete")
async def batch_delete_checkpoints(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Batch delete checkpoints"""
    count = await checkpoint_service.batch_delete_checkpoints(db, request.checkpoint_ids)
    return {"success": True, "message": f"Deleted {count} checkpoints"}


@router.post("/batch-status")
async def batch_update_status(
    request: BatchStatusRequest,
    db: AsyncSession = Depends(get_db)
):
    """Batch update checkpoint active status"""
    count = await checkpoint_service.batch_update_status(db, request.checkpoint_ids, request.is_active)
    status = "enabled" if request.is_active else "disabled"
    return {"success": True, "message": f"{status.capitalize()} {count} checkpoints"}


@router.get("/{checkpoint_id}/training-stats")
async def get_training_stats(
    checkpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get training data statistics for a checkpoint"""
    checkpoint = await checkpoint_service.get_checkpoint(db, checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if not checkpoint.training_data_path:
        return {
            "has_training_data": False,
            "stats": None
        }

    stats = training_data_service.get_stats(checkpoint.training_data_path)
    return {
        "has_training_data": stats["total_images"] > 0,
        "stats": stats
    }


@router.post("/{checkpoint_id}/training-data/refresh")
async def refresh_training_data_cache(
    checkpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Refresh cached training data for a checkpoint"""
    checkpoint = await checkpoint_service.get_checkpoint(db, checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if not checkpoint.training_data_path:
        raise HTTPException(status_code=400, detail="No training data path configured")

    training_data_service.clear_cache(checkpoint.training_data_path)
    stats = training_data_service.get_stats(checkpoint.training_data_path)

    return {
        "success": True,
        "stats": stats
    }

