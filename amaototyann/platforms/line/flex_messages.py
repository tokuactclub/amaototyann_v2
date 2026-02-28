"""LINE Flex Message ビルダー."""

from linebot.v3.messaging.models import (
    FlexBox,
    FlexBubble,
    FlexButton,
    FlexCarousel,
    FlexMessage,
    FlexSeparator,
    FlexText,
    MessageAction,
)


class ReminderFlexBuilder:
    """リマインダー用 Flex Message を構築するクラス."""

    def __init__(self) -> None:
        self._bubbles: list[FlexBubble] = []

    def add_reminder(
        self,
        *,
        job: str,
        person: str,
        deadline: str,
        last_days: int,
        task: str,
        memo: str,
        event_id: str,
    ) -> None:
        """リマインダーバブルを追加する."""
        bubble = FlexBubble(
            size="deca",
            header=FlexBox(
                layout="vertical",
                contents=[
                    FlexText(text=f" {job} ", align="center", size="xxl", weight="bold"),
                    FlexText(text=f" {person} ", align="center"),
                ],
            ),
            body=FlexBox(
                layout="vertical",
                contents=[
                    FlexText(
                        text=f"締切{deadline}まで残り{last_days}日",
                        align="center",
                        color="#ff0000",
                    ),
                    FlexText(
                        wrap=True,
                        text=f" {task} \n{memo}",
                        align="center",
                    ),
                    FlexSeparator(margin="md"),
                    FlexBox(
                        layout="vertical",
                        margin="10px",
                        contents=[
                            FlexButton(
                                action=MessageAction(
                                    label="順調です！",
                                    text=f"{job}{task}順調です！",
                                ),
                            ),
                            FlexButton(
                                action=MessageAction(
                                    label="終わりました！",
                                    text=f"!finish {event_id}",
                                ),
                            ),
                            FlexButton(
                                action=MessageAction(
                                    label="進捗ダメです！",
                                    text=f"{job}{task}進捗ダメです！",
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )
        self._bubbles.append(bubble)

    def build(self) -> list[FlexMessage]:
        """Flex Message のリストを構築する (12件ずつカルーセル)."""
        result = []
        for i in range(0, len(self._bubbles), 12):
            chunk = self._bubbles[i : i + 12]
            result.append(
                FlexMessage(
                    alt_text="リマインダー",
                    contents=FlexCarousel(contents=chunk),
                )
            )
        self._bubbles.clear()
        return result
