from pydantic import BaseModel
from typing import Optional


class PerfRating(BaseModel):
    rating: int
    games: int
    rd: Optional[int] = None
    prog: Optional[int] = None
    prov: Optional[bool] = None


class ProfileResponse(BaseModel):
    username: str
    avatar: Optional[str] = None
    url: str
    ratings: dict[str, PerfRating]
    createdAt: int
    seenAt: int
