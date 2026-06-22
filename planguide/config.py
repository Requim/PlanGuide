"""应用配置。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./planguide.db"
    plan_invite_code: str = "change-me"
    plan_session_days: int = 30
    plan_cookie_secure: bool = False
    upload_max_bytes: int = 5 * 1024 * 1024
    excel_max_rows: int = 1000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
