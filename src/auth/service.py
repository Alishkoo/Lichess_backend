import httpx
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import LICHESS_TOKEN_URL, LICHESS_ACCOUNT_URL
from src.auth.schemas import TokenResponse, LichessUserResponse
from src.auth.models import User, OAuthToken
from src.config import settings


async def get_lichess_token(code: str, verifier: str, redirect_uri: str) -> TokenResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LICHESS_TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "client_id": settings.lichess_client_id,
                "code": code,
                "code_verifier": verifier,
            },
        )
        response.raise_for_status()
        return TokenResponse(**response.json())


async def get_lichess_user(access_token: str) -> LichessUserResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LICHESS_ACCOUNT_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return LichessUserResponse(**response.json())


async def create_or_update_user(
    db: AsyncSession,
    lichess_id: str,
    username: str,
) -> User:
    result = await db.execute(
        select(User).where(User.lichess_id == lichess_id)
    )
    user = result.scalar_one_or_none()

    if user:
        user.username = username
        user.updated_at = datetime.utcnow()
    else:
        user = User(lichess_id=lichess_id, username=username)
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


async def save_oauth_token(
    db: AsyncSession,
    user_id: int,
    access_token: str,
    expires_in: int | None = None,
) -> OAuthToken:
    result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user_id)
    )
    token = result.scalar_one_or_none()

    expires_at = None
    if expires_in:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    if token:
        token.access_token = access_token
        if expires_at:
            token.expires_at = expires_at
    else:
        token = OAuthToken(
            user_id=user_id,
            access_token=access_token,
            expires_at=expires_at,
        )
        db.add(token)

    await db.commit()
    await db.refresh(token)
    return token
