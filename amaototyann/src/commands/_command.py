from logging import getLogger, config
from datetime import datetime, timezone, timedelta
import json
from typing import Optional
import requests
import discord
from amaototyann.src import GAS_URL, messages
from amaototyann.src.utils.ui import ProgressButton, ProgressStatus
from amaototyann.src.utils.commands import Command, CommandRegistry, WebhookResponse, MessageSender

# loggerの設定
with open("amaototyann/src/log_config.json", "r", encoding="utf-8") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")


class Commands(MessageSender, metaclass=CommandRegistry):
    """コマンドの処理を格納するクラス"""

    def __init__(
        self,
        interaction: Optional[discord.Interaction] = None,
        webhook: Optional[discord.Webhook] = None,
        bot: Optional[discord.Client] = None,
        broadcast_webhook_msg: bool = False
    ):
        """_summary_

        Args:
            interaction (Optional[discord.Interaction], optional): discordのメッセージイベントで取得されるinteraction. Defaults to None.
            webhook (Optional[discord.Webhook], optional): discordのWebhookオブジェクト. Defaults to None.
            bot (Optional[discord.Client], optional): discord botのクライアントオブジェクト. Defaults to None.
            broadcast_webhook_msg (bool, optional): メッセージを全サーバーに送信する。`bot`が必要. Defaults to False.
        """
        super().__init__(
            interaction=interaction,
            webhook=webhook,
            bot=bot,
            broadcast_webhook_msg=broadcast_webhook_msg
        )
    HELP = Command(
        text="help",
        description="ヘルプコマンド",
        process=lambda self: self._help()  # pylint: disable=W0212
    )

    REMINDER = Command(
        text="reminder",
        description="リマインダーを送信するコマンド",
        process=lambda self: self._reminder()  # pylint: disable=W0212
    )
    PRACTICE = Command(
        text="practice",
        description="練習があるか送信するコマンド。事前にGASで練習予定を登録しておく必要がある。",
        process=lambda self: self._practice()  # pylint: disable=W0212
    )
    PLACE = Command(
        text="place",
        description="場所を送信するコマンド（未実装）",
        process=lambda self: self._place()  # pylint: disable=W0212
    )
    HANDOVER = Command(
        text="handover",
        description="引き継ぎ資料のURLを送信するコマンド",
        process=lambda self: self.send_message(messages.HANDOVER)
    )
    HELLO = Command(
        text="hello",
        description="say hello to the world!",
        process=lambda self: self.send_message("Hello, World!")
    )
    FINISH = Command(
        text="finish",
        description="リマインダー通知を終了するコマンド",
        process=lambda self, e_id: self._finish_event(e_id)  # pylint: disable=W0212
    )
    YOUTUBE = Command(
        text="youtube",
        description="YouTubeのURLを送信するコマンド",
        process=lambda self: self.send_message(messages.YOUTUBE)
    )
    INSTAGRAM = Command(
        text="instagram",
        description="InstagramのURLを送信するコマンド",
        process=lambda self: self.send_message(messages.INSTAGRAM)
    )
    TWITTER = Command(
        text="twitter",
        description="TwitterのURLを送信するコマンド",
        process=lambda self: self.send_message(messages.TWITTER)
    )
    HOMEPAGE = Command(
        text="homepage",
        description="ホームページのURLを送信するコマンド",
        process=lambda self: self.send_message(messages.HOMEPAGE)
    )

    async def send_single_remind_msg(self, event: dict, target_webhooks: Optional[list[discord.Webhook]]):
        """単一のリマインドメッセージを送信する関数"""
        # embedメッセージの作成
        embed = discord.Embed(colour=0x00b0f4)
        embed.add_field(
            name=f"{event['job']} - 締め切りまで残り**{event['last_days']}**日",
            value=f"{event['memo']}<@{event['person']}>",
            inline=False
        )
        embed.add_field(
            name=ProgressStatus.WAITING, value="", inline=False
        )

        # Webhookでメッセージを送信
        res = await self.send_message(
            embed=embed,
            force_sendWithWebhook=True,
            target_webhooks_on_broadcast=target_webhooks
        )

        if isinstance(res, discord.WebhookMessage):
            responses = [WebhookResponse(webhook=self.webhook, msg=res)]  # type: ignore
        elif isinstance(res, list) and all(isinstance(r, WebhookResponse) for r in res):
            responses = res
        else:
            logger.error("Unexpected response type: %s", type(res))
            return

        # メッセージに対して進捗報告ボタンを追加
        # viewの初期化にmsg.idが必要なため、一旦送信後に編集
        for response in responses:
            webhook = response.webhook
            msg = response.msg

            target_role = discord.utils.get(webhook.guild.roles, name="テスト") if webhook.guild else None
            view = ProgressButton(
                allow_role=target_role,
                webhook=webhook,
                message_id=msg.id
            )

            await webhook.edit_message(msg.id, embed=embed, view=view)

    async def _reminder(self, day_left: Optional[str] = None):

        try:
            await self.defer_response(ephemeral=True)
            response = requests.post(
                GAS_URL,
                json={"cmd": "reminder"},
                timeout=60
            )
            events = response.json()
            # リマインダー対象のイベントを取得
            result_events = []
            for event in events:
                # 終了しているものは除外
                if event["finish"] == "true":
                    continue

                # event["date"]はリマインド日の00:00:00となっているが、
                # リマインド（締切）としては23:59:59を意図しているため、約一日ずらす

                # event["date"]をdatetime型に変換し、1日加算
                event["date"] = datetime.fromisoformat(event["date"])
                event["date"] = event["date"] + timedelta(days=1) - timedelta(seconds=1)

                # 日時の差分を計算
                day_difference = self._calculate_date_difference(event["date"])
                if day_difference < 0:
                    continue

                # リマインド対象日を判定
                target_dates = []
                if day_left is not None:
                    # 指定されたday_leftのみリマインダー対象
                    target_dates.append(day_left)
                else:
                    # 差分がremindDateに含まれればリマインダー対象
                    target_dates = event["remindDate"].split(",")

                if str(day_difference) in target_dates:
                    # dateをGMT+9のMM/DD形式に変換
                    event["date"] = event["date"].astimezone(timezone(timedelta(hours=9))).strftime("%m/%d")

                    event["last_days"] = day_difference
                    result_events.append(event)

            # botとして対応
            if len(result_events) == 0 and self.broadcast_webhook_msg:
                return  # broadcastの場合は何もしない
            elif len(result_events) == 0:
                # slashコマンドの場合は応答を返す
                return await self.send_message(messages.NONE_REMIND_TASK)
            else:
                await self.send_message("リマインダーだよ！")  # 初回応答

            # メッセージを送信
            # UIの観点からWebhookでメッセージを送信
            target_webhooks = await self._get_broadcast_targets_webhooks() if self.broadcast_webhook_msg else None
            for event in result_events:
                await self.send_single_remind_msg(event, target_webhooks)

        except Exception as e:  # pylint: disable=W0718
            logger.exception(e)

    async def _finish_event(self, event_id: str):
        try:
            response = requests.post(
                GAS_URL,
                json={"cmd": "finish", "options": {"id": event_id}},
                timeout=60
            )
            task_name = response.text
            if task_name != "error":
                await self.send_message(f"{task_name}の通知を終わるよ！")
            else:
                await self.send_message("エラーで通知を終われなかったよ！ごめんね！")
        except Exception as e:  # pylint: disable=W0718
            logger.exception(e)

    def _calculate_date_difference(self, dt: datetime):
        """指定の日時と現在の日時の差分を計算する

        Args:
            dt (datetime): datetime object

        Returns:
            _type_: 日数の差分
        """
        assert isinstance(dt, datetime), f"dt must be datetime object, but got {type(dt)}"
        dt = dt.replace(tzinfo=timezone.utc)

        # 現在の日付時刻をutcで取得
        today = datetime.now(timezone.utc)

        # 日数の差分を計算
        # ここで時間以下は切り捨てられる
        day_difference = (dt - today).days

        return day_difference

    async def _practice(self):
        try:

            await self.defer_response()
            response = requests.post(
                GAS_URL,
                json={"cmd": "practice"},
                timeout=60
            )
            logger.info("response: %s", response)
            events = response.json()
            logger.info("events: %s", events)
            try:
                events = list(map(
                    lambda x: messages.PRACTICE.format(x["place"], x["start"].split()[3][:-3], x["end"].split()[3][:-3], "\n" + x["memo"] if x["memo"] else ""),
                    events
                ))

            # GASのタイム表記の移行に伴う例外処理
            except Exception:  # pylint: disable=W0718
                events = list(map(
                    lambda x: messages.PRACTICE.format(x["place"], x["start"], x["end"], "\n" + x["memo"] if x["memo"] else ""),
                    events
                ))
            logger.info("events: %s", events)
            if len(events) > 0:
                await self.send_message("\n\n".join(events))
            else:
                await self.send_message(messages.NO_PRACTICE)
        except Exception as e:  # pylint: disable=W0718
            logger.exception(e)

    async def _place(self):
        # msg = "あまおとがとっている場所は{0}だよ！"
        # 実装するには、練習日以外の活動場所を記録するシステムの構築が必要
        # 作成する場合はヘルプコマンドも修正すること
        await self.send_message(messages.PLACE)

    async def _help(self):
        text = "利用可能なコマンド一覧だよ！\n"
        for cmd in Commands.registry:
            text += f"`/{cmd.text}` : {cmd.description}\n"
        await self.send_message(text)


if __name__ == "__main__":
    cmd = Commands()
    for cmd in Commands.registry:

        print(cmd)
