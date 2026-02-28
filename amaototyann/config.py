"""アプリケーション設定."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """環境変数ベースのアプリケーション設定."""

    discord_bot_token: str | None = None
    server_url: str | None = None
    is_render_server: bool = False
    google_service_account_json: str | None = None
    google_spreadsheet_id: str | None = None
    admin_password: str | None = None
    # 後方互換性のため ADMIN_TOKEN も受け付ける (ADMIN_PASSWORD が優先)
    admin_token: str | None = None

    @model_validator(mode="after")
    def _apply_admin_token_fallback(self) -> "Settings":
        """ADMIN_PASSWORD 未設定時に ADMIN_TOKEN の値をフォールバックとして使用する."""
        if self.admin_password is None and self.admin_token is not None:
            self.admin_password = self.admin_token
        return self

    @property
    def is_debug(self) -> bool:
        return not self.is_render_server

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを返す."""
    return Settings()
