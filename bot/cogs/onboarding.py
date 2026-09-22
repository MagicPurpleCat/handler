"""Кнопки онбординга + автоотметки шагов."""

from __future__ import annotations

import disnake
from disnake.ext import commands

from bot.services.onboarding import (
    ONBOARD_PREFIX,
    onboarding_components,
    onboarding_embed,
)


class OnboardingCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction) -> None:
        cid = inter.component.custom_id if inter.component else ""
        if not cid.startswith(ONBOARD_PREFIX):
            return
        step = cid[len(ONBOARD_PREFIX) :]
        db = self.bot.db  # type: ignore[attr-defined]
        steps = await db.set_onboarding_step(inter.author.id, step, True)
        embed = onboarding_embed(steps)
        try:
            await inter.response.edit_message(
                embed=embed,
                components=onboarding_components(steps),
            )
        except disnake.HTTPException:
            await inter.response.send_message(
                "Отметил. Обнови сообщение или открой ЛС от бота.",
                ephemeral=True,
            )


async def mark_onboarding_if_needed(
    bot: commands.InteractionBot, discord_id: int, step: str
) -> None:
    db = bot.db  # type: ignore[attr-defined]
    row = await db.get_member(discord_id)
    if not row or not row.get("onboarding_json"):
        return
    steps = db.parse_onboarding(row)
    if steps.get(step):
        return
    await db.set_onboarding_step(discord_id, step, True)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(OnboardingCog(bot))
