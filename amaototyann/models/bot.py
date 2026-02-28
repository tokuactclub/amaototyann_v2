"""Bot・グループ情報モデル."""

from pydantic import BaseModel


class BotInfo(BaseModel):
    """LINE Bot 情報."""

    id: int
    bot_name: str
    channel_access_token: str
    channel_secret: str
    gpt_webhook_url: str | None = None
    in_group: bool


class GroupInfo(BaseModel):
    """グループ情報."""

    id: str
    group_name: str
