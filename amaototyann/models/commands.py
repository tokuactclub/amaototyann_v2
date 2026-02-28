"""コマンド処理結果モデル."""

from pydantic import BaseModel


class CommandResult(BaseModel):
    """コマンド処理結果."""

    text: str | None = None
    events: list[dict] | None = None
    error: str | None = None
    is_empty: bool = False
