"""Discord UI コンポーネント."""

import dataclasses
import logging
from typing import Union, Callable, Any, Optional

import discord

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ProgressStatus:
    """進捗報告のステータス定義."""
    GOOD: str = "🟢 : 順調です！"
    BAD: str = "🟡 : 進捗ダメです！"
    DONE: str = "🔵 : 終わりました！"
    WAITING: str = "🔴 : 進捗報告待ち"


class ProgressButton(discord.ui.View):
    """進捗報告用のボタンビュー."""

    def __init__(
        self,
        allow_user: Optional[discord.User] = None,
        allow_role: Optional[discord.Role] = None,
        webhook: Optional[discord.Webhook] = None,
        message_id: Optional[int] = None,
        on_done: Optional[Callable[[discord.Interaction, discord.ui.Button], Any]] = None,
        on_good: Optional[Callable[[discord.Interaction, discord.ui.Button], Any]] = None,
        on_bad: Optional[Callable[[discord.Interaction, discord.ui.Button], Any]] = None,
    ) -> None:
        super().__init__(timeout=86400)
        self.allow_user_id = allow_user.id if allow_user else None
        self.allow_role_id = allow_role.id if allow_role else None
        self.webhook = webhook
        self.message_id = message_id
        self.on_done = on_done
        self.on_good = on_good
        self.on_bad = on_bad

    def _is_allowed(self, user: Union[discord.Member, discord.User]) -> bool:
        if self.allow_user_id and user.id == self.allow_user_id:
            return True
        if self.allow_role_id and isinstance(user, discord.Member):
            return any(r.id == self.allow_role_id for r in user.roles)
        if not self.allow_user_id and not self.allow_role_id:
            return True
        return False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self._is_allowed(interaction.user):
            return True
        await interaction.response.send_message("あなたにはこの操作権限がありません。", ephemeral=True)
        return False

    @discord.ui.button(label="順調です！", style=discord.ButtonStyle.primary)
    async def good(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.on_good:
            await self.on_good(interaction, button)
        await self._update_status(interaction, ProgressStatus.GOOD)

    @discord.ui.button(label="進捗ダメです！", style=discord.ButtonStyle.secondary)
    async def bad(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.on_bad:
            await self.on_bad(interaction, button)
        await self._update_status(interaction, ProgressStatus.BAD)

    @discord.ui.button(label="終わりました！", style=discord.ButtonStyle.success)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.on_done:
            await self.on_done(interaction, button)
        await self._update_status(interaction, ProgressStatus.DONE)

    async def _update_status(self, interaction: discord.Interaction, status: str) -> None:
        if not self.webhook or not self.message_id:
            await interaction.response.send_message("Webhook情報が見つかりません。", ephemeral=True)
            return
        message = interaction.message
        if not message or not message.embeds:
            return
        original_embed = message.embeds[0]
        new_embed = discord.Embed.from_dict(original_embed.to_dict())
        status_field_idx = 1
        if len(new_embed.fields) > status_field_idx:
            new_embed.set_field_at(
                status_field_idx,
                name=status,
                value=new_embed.fields[status_field_idx].value,
                inline=new_embed.fields[status_field_idx].inline,
            )
        else:
            new_embed.add_field(name=status, value="", inline=False)
        await self.webhook.edit_message(self.message_id, embed=new_embed, view=self)
        await interaction.response.defer()
