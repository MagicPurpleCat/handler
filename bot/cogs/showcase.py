"""Витрина клана — топ по Wardog level в #общий."""

from __future__ import annotations

import logging
from typing import Any

import disnake
from disnake.ext import commands, tasks

import config
from bot.services.channel_style import find_text_channel
from bot.services.clan_ladder import ranked_members, wardog_level
from bot.services.clan_ranks import resolve_channel

log = logging.getLogger("handler.showcase")


def build_showcase_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            "### Стая Handler\n"
            "Пока мало привязанных профилей.\n"
            "Привяжи свой: `/привязка установить`"
        )
    lines = ["### Стая Handler · топ по Wardog", ""]
    for i, row in enumerate(rows, 1):
        nick = row.get("game_nick") or "боец"
        cls_key = row.get("class")
        cls = config.class_label_ru(cls_key) if cls_key else "—"
        lvl = wardog_level(row)
        uid = int(row["discord_id"])
        lines.append(
            f"**{i}.** <@{uid}> · **{nick}** · {cls} · Wardog **{lvl}**"
        )
    lines.append("")
    lines.append("_Обновляется вместе со статой · `/профиль`_")
    return "\n".join(lines)


class ShowcaseCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.refresh_showcase.start()

    def cog_unload(self) -> None:
        self.refresh_showcase.cancel()

    async def publish_for_guild(self, guild: disnake.Guild) -> None:
        db = self.bot.db  # type: ignore[attr-defined]
        gcfg = await db.get_guild_config(guild.id)
        if not gcfg:
            return

        members = await db.members_with_profile()
        ranked = ranked_members(members)[: config.SHOWCASE_TOP_N]
        text = build_showcase_text(ranked)

        channel = resolve_channel(guild, gcfg, "general")
        if channel is None:
            channel = find_text_channel(guild, config.CHANNEL_GENERAL)
        if not isinstance(channel, disnake.TextChannel):
            return

        msg_id = gcfg.get("showcase_message_id")
        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(text),
                accent_colour=disnake.Colour(0x4A5D23),
            )
        ]
        flags = disnake.MessageFlags(is_components_v2=True)

        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
                await msg.edit(components=components, flags=flags)
                return
            except (disnake.HTTPException, disnake.NotFound):
                pass

        try:
            msg = await channel.send(components=components, flags=flags)
            await db.patch_guild_config(guild.id, showcase_message_id=msg.id)
            try:
                await msg.pin(reason="Витрина клана Handler")
            except disnake.HTTPException:
                pass
        except disnake.HTTPException as exc:
            log.warning("Showcase publish failed: %s", exc)

    @tasks.loop(hours=1)
    async def refresh_showcase(self) -> None:
        for guild in self.bot.guilds:
            try:
                await self.publish_for_guild(guild)
            except Exception:  # noqa: BLE001
                log.exception("Showcase refresh error for guild %s", guild.id)

    @refresh_showcase.before_loop
    async def before_showcase(self) -> None:
        await self.bot.wait_until_ready()

    @commands.slash_command(
        name="витрина",
        description="Обновить витрину клана в #общий (офицеры)",
    )
    async def showcase_now(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> None:
        from bot.services.clan_ranks import is_staff

        if not isinstance(inter.author, disnake.Member) or not inter.guild:
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        if not is_staff(inter.author) and not inter.author.guild_permissions.administrator:
            await inter.response.send_message(
                "Обновлять витрину могут офицеры.", ephemeral=True
            )
            return
        await inter.response.defer(ephemeral=True)
        await self.publish_for_guild(inter.guild)
        await inter.followup.send("Витрину обновил.", ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ShowcaseCog(bot))
