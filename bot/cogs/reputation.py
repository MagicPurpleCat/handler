"""Репутация «собака стаи» — ручные плюсы от офицеров."""

from __future__ import annotations

import disnake
from disnake.ext import commands

import config
from bot.services.clan_ranks import is_staff


class ReputationCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.slash_command(
        name="плюс",
        description="Отметить вклад бойца (только офицеры)",
    )
    async def plus(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = commands.Param(name="участник"),
        причина: str = commands.Param(name="причина", max_length=120),
    ) -> None:
        if not isinstance(inter.author, disnake.Member) or not inter.guild:
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        if not is_staff(inter.author):
            await inter.response.send_message(
                "Плюсы ставят только офицеры и командир.", ephemeral=True
            )
            return
        if участник.id == inter.author.id:
            await inter.response.send_message(
                "Себе плюс не ставится.", ephemeral=True
            )
            return
        if участник.bot:
            await inter.response.send_message("Ботам плюсы не нужны.", ephemeral=True)
            return

        reason = причина.strip()
        if len(reason) < 3:
            await inter.response.send_message(
                "Напиши нормальную причину — хотя бы пару слов.",
                ephemeral=True,
            )
            return

        db = self.bot.db  # type: ignore[attr-defined]
        given = await db.reputation_given_today(inter.author.id, inter.guild.id)
        if given >= config.REPUTATION_DAILY_LIMIT:
            await inter.response.send_message(
                f"Лимит на сегодня: {config.REPUTATION_DAILY_LIMIT}. Завтра снова можно.",
                ephemeral=True,
            )
            return

        await db.add_reputation(
            inter.guild.id, inter.author.id, участник.id, reason
        )
        total = await db.reputation_total(участник.id, inter.guild.id)
        await inter.response.send_message(
            f"**+1** {участник.mention} — {reason}\n"
            f"Всего отметок: **{total}** · от {inter.author.mention}"
        )


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ReputationCog(bot))
