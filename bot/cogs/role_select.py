"""Self-select классов «за кого играю»."""

from __future__ import annotations

import json

import disnake
from disnake.ext import commands

import config
from bot.services.channel_content import PLAY_AS_SELECT_ID
from bot.services.class_roles import sync_play_as_roles
from bot.services.roles_sync import find_role


class RoleSelectCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.Cog.listener("on_dropdown")
    async def on_play_as_select(self, inter: disnake.MessageInteraction) -> None:
        if inter.component.custom_id != PLAY_AS_SELECT_ID:
            return
        if not inter.guild or not isinstance(inter.author, disnake.Member):
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return

        member_role = find_role(inter.guild, config.ROLE_MEMBER)
        if member_role and member_role not in inter.author.roles:
            if not inter.author.guild_permissions.administrator:
                await inter.response.send_message(
                    f"Сначала вступи в клан (роль **{config.ROLE_MEMBER}**).",
                    ephemeral=True,
                )
                return

        selected = [v for v in inter.values if v in config.CLASSES]
        await inter.response.defer(ephemeral=True)
        await sync_play_as_roles(inter.author, selected)

        db = self.bot.db  # type: ignore[attr-defined]
        fields: dict = {
            "classes_json": json.dumps(selected, ensure_ascii=False),
        }
        if selected:
            fields["class"] = selected[0]
            await db.update_member(inter.author.id, **fields)
            from bot.cogs.onboarding import mark_onboarding_if_needed

            await mark_onboarding_if_needed(self.bot, inter.author.id, "class")
            labels = ", ".join(config.class_label_ru(c) for c in selected)
            await inter.followup.send(
                f"Классы обновлены: **{labels}**",
                ephemeral=True,
            )
        else:
            fields["class"] = None
            await db.update_member(inter.author.id, **fields)
            await inter.followup.send(
                "Все класс-роли сняты. Можешь выбрать снова в любое время.",
                ephemeral=True,
            )


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(RoleSelectCog(bot))
