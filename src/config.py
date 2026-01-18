from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    redis_url: str

    lichess_client_id: str
    lichess_redirect_uri: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7


    frontend_url: str
    environment: str = "development"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
