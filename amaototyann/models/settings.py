"""設定関連のモデル."""

from pydantic import BaseModel, Field


class PracticeDefault(BaseModel):
    """月間の練習デフォルト設定."""

    month: int = Field(..., ge=1, le=12, description="月 (1-12)")
    enabled: bool = True
    place: str = ""
    start_time: str = "14:00"
    end_time: str = "17:00"
