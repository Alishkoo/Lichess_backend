import httpx
from src.auth.constants import LICHESS_ACCOUNT_URL


async def fetch_user_profile(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LICHESS_ACCOUNT_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()
