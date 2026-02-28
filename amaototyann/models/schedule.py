"""スケジュール関連の入力モデル."""

from pydantic import BaseModel, Field


class PracticeCreate(BaseModel):
    """練習予定の作成リクエスト."""

    date: str = Field(description="YYYY-MM-DD")
    place: str = Field(min_length=1)
    start_time: str = Field(description="HH:MM")
    end_time: str = Field(description="HH:MM")
    memo: str = ""


class ReminderCreate(BaseModel):
    """リマインダーの作成リクエスト."""

    deadline: str = Field(description="YYYY-MM-DD")
    role: str = Field(min_length=1)
    person: str = ""
    task: str = Field(min_length=1)
    memo: str = ""
    remind_date: str = "7,3,1"
