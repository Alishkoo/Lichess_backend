from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int | None = None


class LichessUserResponse(BaseModel):
    id: str
    username: str


class UserResponse(BaseModel):
    id: int
    lichess_id: str
    username: str

    class Config:
        from_attributes = True
