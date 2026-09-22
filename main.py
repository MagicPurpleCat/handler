"""Точка входа бота Хендлер (War Dogs) — disnake."""

from __future__ import annotations

import asyncio
import logging
import sys

import disnake
from disnake.ext import commands

import config
from bot.db import Database
from bot.services.branding import ensure_all_banners

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# disnake: gateway dump, «logging in», PyNaCl (нам не нужен join в войс)
logging.getLogger("disnake").setLevel(logging.ERROR)
logging.getLogger("disnake.http").setLevel(logging.ERROR)
log = logging.getLogger("handler")

COGS = (
    "bot.cogs.setup",
    "bot.cogs.applications",
    "bot.cogs.profile",
    "bot.cogs.role_select",
    "bot.cogs.stats_sync",
    "bot.cogs.welcome",
    "bot.cogs.onboarding",
    "bot.cogs.activity",
    "bot.cogs.staff",
    "bot.cogs.reputation",
    "bot.cogs.showcase",
    "bot.cogs.archive",
)


class HandlerBot(commands.InteractionBot):
    def __init__(self) -> None:
        intents = disnake.Intents.default()
        intents.guilds = True
        intents.members = True  # privileged — включи Server Members Intent в портале
        intents.voice_states = True
        kwargs: dict = {"intents": intents}
        if config.GUILD_ID:
            kwargs["test_guilds"] = [config.GUILD_ID]
        super().__init__(**kwargs)
        self.db = Database()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (%s)", self.user, self.user and self.user.id)
        await self.change_presence(
            activity=disnake.Activity(
                type=disnake.ActivityType.watching,
                name="стаю Handler",
            )
        )

    async def close(self) -> None:
        await self.db.close()
        await super().close()


async def amain() -> None:
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "your_bot_token_here":
        print("Укажи DISCORD_TOKEN в файле .env (см. .env.example)", file=sys.stderr)
        sys.exit(1)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    bot = HandlerBot()
    await bot.db.connect()
    ensure_all_banners()
    for ext in COGS:
        bot.load_extension(ext)
    log.info("Коги: %s · старт…", len(COGS))
    await bot.start(config.DISCORD_TOKEN)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
