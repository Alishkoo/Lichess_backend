from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class GameResponse(BaseModel):
    id: str
    created_at: datetime
    perf_type: str
    time_control: Optional[str]
    opponent_name: str
    opponent_rating: Optional[int]
    user_color: str
    result: str
    termination: str
    url: str

    class Config:
        from_attributes = True


class GamesListResponse(BaseModel):
    items: list[GameResponse]
    total: int
    page: int
    limit: int
    pages: int


class SyncResponse(BaseModel):
    task_id: str
    message: str


class SyncStatusResponse(BaseModel):
    task_id: str
    state: str
    current: int
    total: int
    percent: int
    message: str
    result: Optional[dict] = None
