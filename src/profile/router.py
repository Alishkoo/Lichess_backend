from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
import time

from src.database import get_db
from src.auth.models import User
from src.auth.dependencies import get_current_user
from src.profile.schemas import ProfileResponse, PerfRating
from src.profile.service import fetch_user_profile
from src.profile.dependencies import get_lichess_token
from src.cache import get_profile_cache, set_profile_cache


router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    response: Response,
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_lichess_token),
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()
    
    cached_profile = await get_profile_cache(current_user.id)
    
    if cached_profile:
        elapsed = time.time() - start_time
        response.headers["X-Cache-Status"] = "HIT"
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
        return ProfileResponse(**cached_profile)
    
    lichess_data = await fetch_user_profile(access_token)
    
    perfs = lichess_data.get("perfs", {})
    ratings = {}
    
    for perf_type, perf_data in perfs.items():
        if isinstance(perf_data, dict) and "rating" in perf_data and "games" in perf_data:
            ratings[perf_type] = PerfRating(
                rating=perf_data.get("rating", 0),
                games=perf_data.get("games", 0),
                rd=perf_data.get("rd"),
                prog=perf_data.get("prog"),
                prov=perf_data.get("prov")
            )
    
    profile_response = ProfileResponse(
        username=lichess_data.get("username"),
        avatar=None,
        url=lichess_data.get("url"),
        ratings=ratings,
        createdAt=lichess_data.get("createdAt"),
        seenAt=lichess_data.get("seenAt")
    )
    
    profile_dict = profile_response.model_dump()
    await set_profile_cache(current_user.id, profile_dict)
    
    current_user.profile_data = lichess_data
    await db.commit()
    
    elapsed = time.time() - start_time
    response.headers["X-Cache-Status"] = "MISS"
    response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
    
    return profile_response
