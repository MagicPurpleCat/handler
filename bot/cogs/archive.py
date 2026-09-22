"""Авто-архив неактивных — кандидат в паузу + подтверждение офицера."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands, tasks

import config
from bot.services.channel_style import find_text_channel
from bot.services.clan_ranks import (
    has_clan_rank,
    is_staff,
    resolve_channel,
    resolve_role,
)
from bot.services.roles_sync import find_role

log = logging.getLogger("handler.archive")

PAUSE_CONFIRM = "wardogs:pause:yes:"
PAUSE_KEEP = "wardogs:pause:no:"


class ArchiveCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.check_inactive.start()

    def cog_unload(self) -> None:
        self.check_inactive.cancel()

    async def _candidate_ids(self, guild: disnake.Guild) -> list[int]:
        db = self.bot.db  # type: ignore[attr-defined]
        member_role = find_role(guild, config.ROLE_MEMBER)
        if not member_role:
            return []

        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(days=config.ARCHIVE_INACTIVE_DAYS)
        ).timestamp()
        out: list[int] = []

        for member in member_role.members:
            if member.bot:
                continue
            if has_clan_rank(
                member, config.ROLE_OFFICER, config.ROLE_COMMANDER, config.ROLE_PAUSE
            ):
                continue
            row = await db.get_member(member.id)
            if row and row.get("paused_at"):
                continue
            if row and row.get("pause_warned_at"):
                # уже предупреждали — не спамим чаще раза в период
                warned = float(row["pause_warned_at"])
                if time.time() - warned < config.ARCHIVE_INACTIVE_DAYS * 86400:
                    continue

            last = await db.last_activity_ts(member.id)
            joined = (row or {}).get("joined_clan_at")
            # если никогда не было войса — смотрим дату вступления
            ref = last
            if ref is None and joined:
                ref = float(joined)
            if ref is None:
                continue
            if ref < cutoff:
                out.append(member.id)
        return out

    async def _post_candidate(
        self, guild: disnake.Guild, user_id: int
    ) -> None:
        db = self.bot.db  # type: ignore[attr-defined]
        gcfg = await db.get_guild_config(guild.id)
        staff_ch = resolve_channel(guild, gcfg, "staff")
        if staff_ch is None:
            staff_ch = find_text_channel(guild, config.CHANNEL_STAFF)
        if not isinstance(staff_ch, disnake.TextChannel):
            return

        member = guild.get_member(user_id)
        who = member.mention if member else f"<@{user_id}>"
        days = config.ARCHIVE_INACTIVE_DAYS
        embed = disnake.Embed(
            title="Кандидат на паузу",
            description=(
                f"{who} не был в войсах стаи **{days}+** дней.\n"
                "Можно поставить роль Пауза (сквады закрываются) или оставить как есть."
            ),
            color=0x6B6B6B,
        )
        row = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    style=disnake.ButtonStyle.danger,
                    label="В паузу",
                    custom_id=f"{PAUSE_CONFIRM}{user_id}",
                ),
                disnake.ui.Button(
                    style=disnake.ButtonStyle.secondary,
                    label="Оставить",
                    custom_id=f"{PAUSE_KEEP}{user_id}",
                ),
            )
        ]
        try:
            await staff_ch.send(embed=embed, components=row)
        except disnake.HTTPException:
            return

        await db.update_member(user_id, pause_warned_at=time.time())

        # ЛС участнику
        if member:
            try:
                await member.send(
                    f"В **{config.CLAN_NAME}** давно не было тебя в войсах. "
                    f"Штаб смотрит, не поставить ли паузу. "
                    f"Если на связи — зайди в лобби или напиши офицеру."
                )
            except disnake.HTTPException:
                pass

    @tasks.loop(hours=config.ARCHIVE_CHECK_HOURS)
    async def check_inactive(self) -> None:
        for guild in self.bot.guilds:
            try:
                ids = await self._candidate_ids(guild)
                for uid in ids[:10]:  # не заспамить штаб
                    await self._post_candidate(guild, uid)
            except Exception:  # noqa: BLE001
                log.exception("Archive check failed for %s", guild.id)

    @check_inactive.before_loop
    async def before_archive(self) -> None:
        await self.bot.wait_until_ready()
        import asyncio

        await asyncio.sleep(300)

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction) -> None:
        cid = inter.component.custom_id if inter.component else ""
        if not (cid.startswith(PAUSE_CONFIRM) or cid.startswith(PAUSE_KEEP)):
            return
        if not isinstance(inter.author, disnake.Member) or not inter.guild:
            await inter.response.send_message("Только на сервере.", ephemeral=True)
            return
        if not is_staff(inter.author):
            await inter.response.send_message(
                "Только офицеры.", ephemeral=True
            )
            return

        confirm = cid.startswith(PAUSE_CONFIRM)
        try:
            user_id = int(cid.split(":")[-1])
        except ValueError:
            await inter.response.send_message("Битая кнопка.", ephemeral=True)
            return

        db = self.bot.db  # type: ignore[attr-defined]
        gcfg = await db.get_guild_config(inter.guild.id)

        if confirm:
            pause = resolve_role(inter.guild, gcfg, "pause", config.ROLE_PAUSE)
            if pause is None:
                try:
                    pause = await inter.guild.create_role(
                        name=config.ROLE_PAUSE,
                        colour=disnake.Colour(config.ROLE_COLORS[config.ROLE_PAUSE]),
                        reason="Handler: роль Пауза",
                    )
                    if gcfg:
                        roles = dict(gcfg.get("roles") or {})
                        roles["pause"] = pause.id
                        await db.patch_guild_config(inter.guild.id, roles=roles)
                except disnake.HTTPException:
                    pause = None
            target = inter.guild.get_member(user_id)
            if pause and target:
                try:
                    await target.add_roles(
                        pause, reason=f"Пауза · {inter.author}"
                    )
                except disnake.HTTPException:
                    pass
            await db.update_member(user_id, paused_at=time.time())
            text = f"Пауза для <@{user_id}> — поставил {inter.author.mention}."
        else:
            await db.update_member(
                user_id, pause_warned_at=time.time(), paused_at=None
            )
            text = f"<@{user_id}> оставляем в строю · {inter.author.mention}."

        try:
            await inter.response.edit_message(
                content=text,
                embed=None,
                components=[],
            )
        except disnake.HTTPException:
            await inter.response.send_message(text, ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ArchiveCog(bot))
