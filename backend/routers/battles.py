"""
Battles API Router

Handles battle creation, voting, and history.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import json
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.schemas import (
    NewBattleRequest,
    NewBattleResponse,
    VoteRequest,
    VoteResponse,
    BattleHistoryItem,
    BattleHistoryResponse,
    CheckpointResponse,
)
from services.battle_service import battle_service
from services.checkpoint_service import checkpoint_service


def _parse_comfyui_validation_error(error: Exception) -> str | None:
    message = str(error)
    if "Failed to queue prompt:" in message:
        message = message.split("Failed to queue prompt:", 1)[1].strip()

    parsed_message = message
    try:
        data = json.loads(message)
        if isinstance(data, dict):
            parsed_message = json.dumps(data)
    except json.JSONDecodeError:
        pass

    lowered = parsed_message.lower()
    if "prompt_outputs_failed_validation" not in lowered and "prompt outputs failed validation" not in lowered:
        return None

    if "checkpointloadersimple" in lowered or "ckpt_name" in lowered or "checkpoint" in lowered:
        return (
            "ComfyUI validation failed: base model not found. "
            "Please select a valid base model in Settings."
        )
    if "loraloader" in lowered or "lora_name" in lowered:
        return (
            "ComfyUI validation failed: LoRA not found. "
            "Please check the LoRA directory in Settings and re-scan."
        )

    return (
        "ComfyUI validation failed. Please verify your base model and LoRA settings in Settings."
    )

router = APIRouter(prefix="/api/battles", tags=["battles"])


@router.post("/new", response_model=NewBattleResponse)
async def create_new_battle(
    request: NewBattleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new battle between two LoRA checkpoints.
    """
    try:
        # Check if we have enough checkpoints
        active_count = await checkpoint_service.get_active_count(db)
        if active_count < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 2 active checkpoints for a battle. Currently have {active_count}."
            )

        battle = await battle_service.initialize_battle(db, request)

        # If it's already completed (from cache), don't trigger background task
        if battle.status == "pending":
            background_tasks.add_task(battle_service.process_battle_generation, battle.id)

        return NewBattleResponse(
            battle_id=battle.id,
            status=battle.status,
            left_image_url=battle.left_image_path,
            right_image_url=battle.right_image_path,
            prompt=battle.prompt,
            negative_prompt=battle.negative_prompt,
            seed=battle.seed,
            width=battle.width,
            height=battle.height,
            steps=battle.steps,
            cfg_scale=battle.cfg_scale,
            error_message=battle.error_message
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        parsed = _parse_comfyui_validation_error(e)
        if parsed:
            raise HTTPException(status_code=400, detail=parsed)
        raise HTTPException(status_code=500, detail=f"Failed to create battle: {str(e)}")


@router.post("/{battle_id}/vote", response_model=VoteResponse)
async def submit_vote(
    battle_id: int,
    request: VoteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a vote for a battle.

    This will:
    1. Record the vote result
    2. Calculate and update ELO ratings
    3. Return the revealed checkpoint information
    """
    try:
        battle, elo_changes = await battle_service.submit_vote(db, battle_id, request)

        # Get checkpoint details
        left_checkpoint = await checkpoint_service.get_checkpoint(db, battle.left_checkpoint_id)
        right_checkpoint = await checkpoint_service.get_checkpoint(db, battle.right_checkpoint_id)

        return VoteResponse(
            success=True,
            left_checkpoint=CheckpointResponse(
                id=left_checkpoint.id,
                name=left_checkpoint.name,
                filename=left_checkpoint.filename,
                file_path=left_checkpoint.file_path,
                description=left_checkpoint.description,
                trigger_words=left_checkpoint.trigger_words or [],
                tags=left_checkpoint.tags or [],
                elo_rating=left_checkpoint.elo_rating,
                total_battles=left_checkpoint.total_battles,
                wins=left_checkpoint.wins,
                losses=left_checkpoint.losses,
                ties=left_checkpoint.ties,
                win_rate=left_checkpoint.win_rate,
                is_active=left_checkpoint.is_active,
                created_at=left_checkpoint.created_at,
                updated_at=left_checkpoint.updated_at,
            ),
            right_checkpoint=CheckpointResponse(
                id=right_checkpoint.id,
                name=right_checkpoint.name,
                filename=right_checkpoint.filename,
                file_path=right_checkpoint.file_path,
                description=right_checkpoint.description,
                trigger_words=right_checkpoint.trigger_words or [],
                tags=right_checkpoint.tags or [],
                elo_rating=right_checkpoint.elo_rating,
                total_battles=right_checkpoint.total_battles,
                wins=right_checkpoint.wins,
                losses=right_checkpoint.losses,
                ties=right_checkpoint.ties,
                win_rate=right_checkpoint.win_rate,
                is_active=right_checkpoint.is_active,
                created_at=right_checkpoint.created_at,
                updated_at=right_checkpoint.updated_at,
            ),
            winner=battle.result if battle.result != "skip" else None,
            elo_changes=elo_changes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit vote: {str(e)}")


@router.get("/{battle_id}", response_model=NewBattleResponse)
async def get_battle(
    battle_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get battle details by ID"""
    battle = await battle_service.get_battle(db, battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    return NewBattleResponse(
        battle_id=battle.id,
        status=battle.status,
        left_image_url=battle.left_image_path,
        right_image_url=battle.right_image_path,
        prompt=battle.prompt,
        negative_prompt=battle.negative_prompt or "",
        seed=battle.seed,
        width=battle.width,
        height=battle.height,
        steps=battle.steps,
        cfg_scale=battle.cfg_scale,
        error_message=battle.error_message,
    )


@router.get("/history/list", response_model=BattleHistoryResponse)
async def get_battle_history(
    page: int = 1,
    limit: int = 20,
    checkpoint_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """Get paginated battle history"""
    battles, total = await battle_service.get_battle_history(
        db, page, limit, checkpoint_id
    )

    items = []
    for battle in battles:
        left = await checkpoint_service.get_checkpoint(db, battle.left_checkpoint_id)
        right = await checkpoint_service.get_checkpoint(db, battle.right_checkpoint_id)

        items.append(BattleHistoryItem(
            id=battle.id,
            left_checkpoint_name=left.name if left else "Unknown",
            right_checkpoint_name=right.name if right else "Unknown",
            result=battle.result,
            prompt=battle.prompt,
            seed=battle.seed,
            left_image_url=battle.left_image_path,
            right_image_url=battle.right_image_path,
            created_at=battle.created_at,
            voted_at=battle.voted_at,
        ))

    return BattleHistoryResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )
