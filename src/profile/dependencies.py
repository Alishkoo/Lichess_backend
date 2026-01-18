from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.auth.models import User, OAuthToken
from src.auth.dependencies import get_current_user


async def get_lichess_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> str:
    result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == current_user.id)
    )
    oauth_token = result.scalar_one_or_none()
    
    if not oauth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Lichess token not found"
        )
    
    return oauth_token.access_token
