"""Учёт активности в войсах сквадов / лобби."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

import config


class ActivityCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        # (guild_id, user_id) -> (channel_id, joined_at)
        self._sessions: dict[tuple[int, int], tuple[int, float]] = {}

    def _counted_ids(self, guild: disnake.Guild, gcfg: dict | None) -> set[int]:
        ids: set[int] = set()
        if not gcfg:
            return ids
        channels = gcfg.get("channels") or {}
        for key in config.ACTIVITY_VOICE_KEYS:
            cid = channels.get(key)
            if cid:
                ids.add(int(cid))
        return ids

    async def _flush(
        self, guild_id: int, user_id: int, *, end_ts: float | None = None
    ) -> None:
        key = (guild_id, user_id)
        sess = self._sessions.pop(key, None)
        if not sess:
            return
        _ch, joined = sess
        elapsed = int((end_ts or time.time()) - joined)
        if elapsed < config.ACTIVITY_MIN_SESSION_SEC:
            return
        db = self.bot.db  # type: ignore[attr-defined]
        await db.add_activity_seconds(user_id, elapsed)
        # онбординг: лобби
        from bot.cogs.onboarding import mark_onboarding_if_needed

        await mark_onboarding_if_needed(self.bot, user_id, "lobby")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ) -> None:
        if member.bot:
            return
        db = self.bot.db  # type: ignore[attr-defined]
        gcfg = await db.get_guild_config(member.guild.id)
        counted = self._counted_ids(member.guild, gcfg)
        if not counted:
            return

        key = (member.guild.id, member.id)
        before_id = before.channel.id if before.channel else None
        after_id = after.channel.id if after.channel else None

        was_in = before_id in counted if before_id else False
        now_in = after_id in counted if after_id else False

        if was_in and (not now_in or before_id != after_id):
            await self._flush(member.guild.id, member.id)

        if now_in and (not was_in or before_id != after_id):
            assert after_id is not None
            self._sessions[key] = (after_id, time.time())

    @commands.slash_command(
        name="активность",
        description="Кто сколько был в войсах стаи",
    )
    async def activity(
        self,
        inter: disnake.ApplicationCommandInteraction,
        дней: int = commands.Param(
            name="дней",
            description="За сколько дней",
            choices=[7, 30],
            default=7,
        ),
    ) -> None:
        since = (
            datetime.now(timezone.utc) - timedelta(days=int(дней))
        ).strftime("%Y-%m-%d")
        db = self.bot.db  # type: ignore[attr-defined]
        rows = await db.activity_top(since, limit=15)
        if not rows:
            await inter.response.send_message(
                f"Пока пусто за {дней} дн. Заходите в лобби и сквады.",
                ephemeral=True,
            )
            return

        lines = []
        for i, row in enumerate(rows, 1):
            secs = int(row["total"])
            hours = secs / 3600
            uid = int(row["discord_id"])
            lines.append(f"**{i}.** <@{uid}> — **{hours:.1f}** ч")

        embed = disnake.Embed(
            title=f"Активность · {дней} дн.",
            description="\n".join(lines),
            color=0x4A5D23,
        )
        embed.set_footer(text="Считаются лобби и сквады (от 2 мин за заход)")
        await inter.response.send_message(embed=embed)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ActivityCog(bot))
