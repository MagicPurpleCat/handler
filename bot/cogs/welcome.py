"""Welcome: роль Гость при входе на сервер."""

from __future__ import annotations

import logging

import disnake
from disnake.ext import commands

import config
from bot.services.channel_style import find_text_channel
from bot.services.clan_ranks import has_clan_rank, resolve_channel, resolve_role

log = logging.getLogger("handler.welcome")


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member) -> None:
        if member.bot:
            return

        # уже в клане / штабе — не трогаем
        if has_clan_rank(
            member,
            config.ROLE_MEMBER,
            config.ROLE_OFFICER,
            config.ROLE_COMMANDER,
            config.ROLE_RECRUIT,
        ):
            return

        db = self.bot.db  # type: ignore[attr-defined]
        gcfg = await db.get_guild_config(member.guild.id)
        guest = resolve_role(member.guild, gcfg, "guest", config.ROLE_GUEST)
        if guest and guest not in member.roles:
            try:
                await member.add_roles(guest, reason="Handler: вход — Гость")
            except disnake.HTTPException:
                log.warning("Не выдал Гость %s", member.id)

        apply_ch = resolve_channel(member.guild, gcfg, "apply")
        rules_ch = resolve_channel(member.guild, gcfg, "rules")
        if apply_ch is None:
            apply_ch = find_text_channel(member.guild, config.CHANNEL_APPLY)
        if rules_ch is None:
            rules_ch = find_text_channel(member.guild, config.CHANNEL_RULES)

        apply_mention = apply_ch.mention if apply_ch else f"#{config.CHANNEL_APPLY}"
        rules_mention = rules_ch.mention if rules_ch else f"#{config.CHANNEL_RULES}"

        dm_text = (
            f"Привет, это **{config.CLAN_NAME}** (Handler).\n\n"
            f"Заявка в клан — в {apply_mention}.\n"
            f"Правила — {rules_mention}.\n\n"
            "Пока ты Гость: посмотри правила и подай заявку, когда будешь готов."
        )
        try:
            await member.send(dm_text)
        except disnake.HTTPException:
            general = resolve_channel(member.guild, gcfg, "general")
            if general is None:
                general = find_text_channel(member.guild, config.CHANNEL_GENERAL)
            if isinstance(general, disnake.TextChannel):
                try:
                    await general.send(
                        f"{member.mention} зашёл на сервер. "
                        f"Заявка: {apply_mention} · правила: {rules_mention}"
                    )
                except disnake.HTTPException:
                    pass


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(WelcomeCog(bot))
