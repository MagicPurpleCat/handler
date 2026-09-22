"""Автообновление статистики wardogs.tools каждые N минут."""

from __future__ import annotations

import asyncio
import json
import logging

import aiohttp
from disnake.ext import commands, tasks

import config
from bot.services.wardogs_stats import WardogsStatsError, fetch_player_stats

log = logging.getLogger("handler.stats_sync")


class StatsSyncCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.refresh_linked_stats.start()

    def cog_unload(self) -> None:
        self.refresh_linked_stats.cancel()

    @tasks.loop(minutes=config.STATS_REFRESH_MINUTES)
    async def refresh_linked_stats(self) -> None:
        db = self.bot.db  # type: ignore[attr-defined]
        members = await db.members_with_profile()
        if not members:
            return

        ok = 0
        fail = 0
        headers = {
            "User-Agent": "HandlerBot/1.0 (+War Dogs clan; discord)",
            "Accept": "text/html,application/xhtml+xml",
        }
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for row in members:
                url = row.get("profile_url")
                if not url:
                    continue
                try:
                    stats = await fetch_player_stats(url, session=session)
                    await db.update_member(
                        int(row["discord_id"]),
                        profile_url=stats.profile_url,
                        game_stats_json=json.dumps(stats.to_dict(), ensure_ascii=False),
                        game_nick=stats.display_name,
                    )
                    ok += 1
                except WardogsStatsError as exc:
                    fail += 1
                    log.warning(
                        "Stats refresh failed for %s: %s",
                        row.get("discord_id"),
                        exc,
                    )
                except Exception:  # noqa: BLE001
                    fail += 1
                    log.exception(
                        "Stats refresh error for %s", row.get("discord_id")
                    )
                await asyncio.sleep(config.STATS_REFRESH_DELAY_SEC)

        log.debug(
            "Stats refresh done: %s ok, %s fail, %s total",
            ok,
            fail,
            len(members),
        )
        if fail:
            log.warning("Stats refresh: %s ok, %s fail", ok, fail)
        showcase = self.bot.get_cog("ShowcaseCog")
        if showcase and hasattr(showcase, "publish_for_guild"):
            for guild in self.bot.guilds:
                try:
                    await showcase.publish_for_guild(guild)  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    log.exception("Showcase after stats failed for %s", guild.id)

    @refresh_linked_stats.before_loop
    async def before_refresh(self) -> None:
        await self.bot.wait_until_ready()
        # небольшая пауза после старта, чтобы не бить API сразу при boot
        await asyncio.sleep(30)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(StatsSyncCog(bot))
