from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from celery.result import AsyncResult
from typing import Optional

from src.database import get_db
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.games.models import Game
from src.games.schemas import (
    GameResponse,
    GamesListResponse,
    SyncResponse,
    SyncStatusResponse
)
from src.games.tasks import sync_user_games
from src.celery_app import celery_app


router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("/sync", response_model=SyncResponse)
async def trigger_games_sync(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    result = await session.execute(
        select(User)
        .options(selectinload(User.oauth_token))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.oauth_token:
        raise HTTPException(status_code=401, detail="OAuth token not found")
    
    task = sync_user_games.delay(
        user_id=user.id,
        lichess_username=user.username,
        access_token=user.oauth_token.access_token
    )
    
    return SyncResponse(
        task_id=task.id,
        message="Game synchronization started"
    )


@router.get("/sync/status/{task_id}", response_model=SyncStatusResponse)
async def get_sync_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == "PENDING":
        response = SyncStatusResponse(
            task_id=task_id,
            state="PENDING",
            current=0,
            total=0,
            percent=0,
            message="Task is waiting to start"
        )
    elif task_result.state == "PROGRESS":
        info = task_result.info or {}
        response = SyncStatusResponse(
            task_id=task_id,
            state="PROGRESS",
            current=info.get("current", 0),
            total=info.get("total", 0),
            percent=info.get("percent", 0),
            message=info.get("message", "Processing...")
        )
    elif task_result.state == "SUCCESS":
        result = task_result.result or {}
        response = SyncStatusResponse(
            task_id=task_id,
            state="SUCCESS",
            current=result.get("processed", 0),
            total=result.get("total_games", 0),
            percent=100,
            message=result.get("message", "Completed"),
            result=result
        )
    elif task_result.state == "FAILURE":
        response = SyncStatusResponse(
            task_id=task_id,
            state="FAILURE",
            current=0,
            total=0,
            percent=0,
            message=str(task_result.info)
        )
    else:
        response = SyncStatusResponse(
            task_id=task_id,
            state=task_result.state,
            current=0,
            total=0,
            percent=0,
            message="Unknown state"
        )
    
    return response


@router.get("", response_model=GamesListResponse)
async def get_games(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    perf_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    query = select(Game).where(Game.user_id == current_user.id)
    
    if perf_type:
        query = query.where(Game.perf_type == perf_type)
    
    query = query.order_by(Game.created_at.desc())
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    games = result.scalars().all()
    
    pages = (total + limit - 1) // limit
    
    return GamesListResponse(
        items=[GameResponse.model_validate(game) for game in games],
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )
