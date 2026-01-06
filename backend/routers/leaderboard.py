"""
Leaderboard API Router

Handles leaderboard and ELO history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.session import get_db
from models.database import Checkpoint, ELOHistory
from models.schemas import (
    LeaderboardEntry,
    LeaderboardResponse,
    ELOHistoryPoint,
    ELOHistoryResponse,
)
from services.checkpoint_service import checkpoint_service

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    min_battles: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the ELO leaderboard.

    Returns checkpoints ranked by ELO rating.
    """
    query = (
        select(Checkpoint)
        .where(Checkpoint.is_active == True)
        .where(Checkpoint.total_battles >= min_battles)
        .order_by(desc(Checkpoint.elo_rating))
        .limit(limit)
    )

    result = await db.execute(query)
    checkpoints = list(result.scalars().all())

    items = []
    for rank, checkpoint in enumerate(checkpoints, start=1):
        items.append(LeaderboardEntry(
            rank=rank,
            checkpoint_id=checkpoint.id,
            name=checkpoint.name,
            elo_rating=checkpoint.elo_rating,
            total_battles=checkpoint.total_battles,
            wins=checkpoint.wins,
            losses=checkpoint.losses,
            ties=checkpoint.ties,
            win_rate=checkpoint.win_rate,
        ))

    return LeaderboardResponse(
        items=items,
        total=len(items),
    )


@router.get("/{checkpoint_id}/history", response_model=ELOHistoryResponse)
async def get_elo_history(
    checkpoint_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ELO rating history for a checkpoint.

    Returns historical ELO ratings for charting.
    """
    # Get checkpoint
    checkpoint = await checkpoint_service.get_checkpoint(db, checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Get history
    query = (
        select(ELOHistory)
        .where(ELOHistory.checkpoint_id == checkpoint_id)
        .order_by(ELOHistory.recorded_at.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    history = list(result.scalars().all())

    # Add initial rating point if no history
    points = []
    if not history:
        points.append(ELOHistoryPoint(
            elo_rating=checkpoint.elo_rating,
            recorded_at=checkpoint.created_at,
            battle_id=None,
        ))
    else:
        for h in history:
            points.append(ELOHistoryPoint(
                elo_rating=h.elo_rating,
                recorded_at=h.recorded_at,
                battle_id=h.battle_id,
            ))

    return ELOHistoryResponse(
        checkpoint_id=checkpoint.id,
        checkpoint_name=checkpoint.name,
        history=points,
    )
