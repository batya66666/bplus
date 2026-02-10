from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str

    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 14

    login_max_attempts: int = 5
    login_lock_minutes: int = 15


settings = Settings()
