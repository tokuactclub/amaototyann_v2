"""ユーザーインターフェース関連のユーティリティモジュール"""


import dataclasses
from typing import Union, Callable, Any
import discord


@dataclasses.dataclass
class ProgressStatus:
    """進捗報告のステータス定義クラス"""
    GOOD: str = "🟢 : 順調です！"
    BAD: str = "🟡 : 進捗ダメです！"
    DONE: str = "🔵 : 終わりました！"
    WAITING: str = "🔴 : 進捗報告待ち"


class ProgressButton(discord.ui.View):
    """進捗報告用のボタンビュークラス"""

    def __init__(
        self,
        allow_user: Union[discord.User, None] = None,
        allow_role: Union[discord.Role, None] = None,
        webhook: Union[discord.Webhook, None] = None,
        message_id: Union[int, None] = None,
        on_done: Union[Callable[[discord.Interaction, discord.ui.Button], Any], None] = None,
        on_good: Union[Callable[[discord.Interaction, discord.ui.Button], Any], None] = None,
        on_bad: Union[Callable[[discord.Interaction, discord.ui.Button], Any], None] = None
    ):
        super().__init__(timeout=None)
        self.allow_user_id = allow_user.id if allow_user else None
        self.allow_role_id = allow_role.id if allow_role else None
        # コメント: Webhookメッセージ編集のために保持
        self.webhook = webhook
        self.message_id = message_id
        self.on_done = on_done
        self.on_good = on_good
        self.on_bad = on_bad

    # コメント: 押したユーザーが許可されているか確認
    def _is_allowed(self, user: Union[discord.Member, discord.User]) -> bool:
        if self.allow_user_id and user.id == self.allow_user_id:
            return True
        if self.allow_role_id and isinstance(user, discord.Member):
            return any(r.id == self.allow_role_id for r in user.roles)
        if not self.allow_user_id and not self.allow_role_id:  # どちらも指定されていない場合は全員許可
            return True
        return False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:  # pylint: disable=w0221
        if self._is_allowed(interaction.user):
            return True
        await interaction.response.send_message("あなたにはこの操作権限がありません。", ephemeral=True)
        return False

    # ===== ボタンごとの処理 =====
    @discord.ui.button(label="順調です！", style=discord.ButtonStyle.primary)
    async def good(self, interaction: discord.Interaction, button: discord.ui.Button):  # pylint: disable=unused-argument, missing-function-docstring
        if self.on_good:
            await self.on_good(interaction, button)
        await self.update_status(interaction, ProgressStatus.GOOD)

    @discord.ui.button(label="進捗ダメです！", style=discord.ButtonStyle.secondary)
    async def bad(self, interaction: discord.Interaction, button: discord.ui.Button):  # pylint: disable=unused-argument, missing-function-docstring
        if self.on_bad:
            await self.on_bad(interaction, button)
        await self.update_status(interaction, ProgressStatus.BAD)

    @discord.ui.button(label="終わりました！", style=discord.ButtonStyle.success)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):  # pylint: disable=unused-argument, missing-function-docstring
        if self.on_done:
            await self.on_done(interaction, button)
        await self.update_status(interaction, ProgressStatus.DONE)

    async def update_status(self, interaction: discord.Interaction, status: str):
        """本文にステータスを反映"""
        # コメント: interaction.message はWebhookメッセージのコピーなので、直接編集すると403になる
        # コメント: 代わりにWebhooks APIを使って編集する
        if not self.webhook or not self.message_id:
            await interaction.response.send_message("Webhook情報が見つかりません。", ephemeral=True)
            return

        message = interaction.message
        if not message or not message.embeds:
            return

        # --- Embedの内容更新 ---
        original_embed = message.embeds[0]
        new_embed = discord.Embed.from_dict(original_embed.to_dict())

        status_field_idx = 1
        if len(new_embed.fields) > status_field_idx:
            new_embed.set_field_at(
                status_field_idx,
                name=status,
                value=new_embed.fields[status_field_idx].value,
                inline=new_embed.fields[status_field_idx].inline
            )
        else:
            new_embed.add_field(name=status, value="", inline=False)

        # --- Webhookを使ってメッセージを編集 ---
        await self.webhook.edit_message(self.message_id, embed=new_embed, view=self)

        # コメント: Interaction成功応答（UIエラー回避）
        await interaction.response.defer()
