from urllib.parse import urlencode
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from src.config import settings
from src.database import get_db
from src.auth.constants import LICHESS_OAUTH_URL, LICHESS_TOKEN_URL, LICHESS_ACCOUNT_URL
from src.auth.utils import create_verifier, create_challenge, create_state
from src.auth.models import User, OAuthToken
from src.auth.dependencies import create_access_token, get_current_user
from src.auth.schemas import UserResponse


router = APIRouter(prefix="/auth", tags=["auth"])

oauth_sessions = {}


@router.get("/login")
async def login(request: Request, response: Response):
    verifier = create_verifier()
    challenge = create_challenge(verifier)
    state = create_state()

    oauth_sessions[state] = {
        "verifier": verifier,
        "challenge": challenge,
    }

    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/callback"

    params = {
        "response_type": "code",
        "client_id": settings.lichess_client_id,
        "redirect_uri": redirect_uri,
        "scope": "preference:read",
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
    }

    auth_url = f"{LICHESS_OAUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def callback(
    request: Request,
    state: str,
    code: str = None,
    error: str = None,
    error_description: str = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        return JSONResponse(
            status_code=400,
            content={
                "error": error,
                "message": error_description or "Authorization failed",
                "detail": "User cancelled authorization" if error == "access_denied" else error_description
            }
        )
    
    if not code:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_code", "message": "Authorization code is required"}
        )
    
    session = oauth_sessions.get(state)
    
    if not session:
        return {"error": "Invalid or expired state parameter"}
    
    code_verifier = session["verifier"]
    del oauth_sessions[state]

    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/callback"

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            LICHESS_TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "client_id": settings.lichess_client_id,
                "code": code,
                "code_verifier": code_verifier,
            },
        )
        token_data = token_response.json()

    if "access_token" not in token_data:
        return {"error": "Failed getting token", "details": token_data}

    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            LICHESS_ACCOUNT_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        user_data = user_response.json()

    lichess_id = user_data.get("id")
    username = user_data.get("username")

    result = await db.execute(select(User).where(User.lichess_id == lichess_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            lichess_id=lichess_id,
            username=username,
            profile_data=user_data,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.username = username
        user.profile_data = user_data
        await db.commit()
        await db.refresh(user)

    result = await db.execute(select(OAuthToken).where(OAuthToken.user_id == user.id))
    existing_token = result.scalar_one_or_none()
    
    if existing_token:
        existing_token.access_token = token_data["access_token"]
        if token_data.get("expires_in"):
            existing_token.expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        await db.commit()
    else:
        oauth_token = OAuthToken(
            user_id=user.id,
            access_token=token_data["access_token"],
            expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 31536000)) if token_data.get("expires_in") else None,
        )
        db.add(oauth_token)
        await db.commit()

    jwt_token = create_access_token({"user_id": user.id})
    
    response = RedirectResponse(url=settings.frontend_url, status_code=302)
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        lichess_id=current_user.lichess_id,
        username=current_user.username,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token")
    return response
