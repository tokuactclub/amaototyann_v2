"""アプリケーション設定."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """環境変数ベースのアプリケーション設定."""

    gas_url: str
    discord_bot_token: str | None = None
    server_url: str | None = None
    is_render_server: bool = False
    admin_token: str | None = None

    @property
    def is_debug(self) -> bool:
        return not self.is_render_server

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを返す."""
    return Settings()
