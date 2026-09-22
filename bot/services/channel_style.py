"""Красивые имена каналов/категорий Handler + алиасы для миграции."""

from __future__ import annotations

import disnake

import config

# Старые имена → актуальные (для переименования уже созданных каналов)
TEXT_CHANNEL_ALIASES: dict[str, tuple[str, ...]] = {
    config.CHANNEL_RULES: ("правила", "📜-правила", "📜・правила"),
    config.CHANNEL_ANNOUNCEMENTS: ("анонсы", "📢-анонсы", "📢・анонсы"),
    config.CHANNEL_ROLES_INFO: ("роли", "🎖️-роли", "🎖-роли", "🎖️・роли"),
    config.CHANNEL_APPLY: ("заявки", "🐕-заявки", "🐕・заявки"),
    config.CHANNEL_MOD_APPS: ("мод-заявки", "🛡-мод-заявки", "🛡️・мод-заявки"),
    config.CHANNEL_GENERAL: ("общий", "💬-общий", "💬・общий"),
    config.CHANNEL_TACTICS: ("тактика", "⚔-тактика", "⚔️・тактика"),
    config.CHANNEL_LOOT: ("лут-и-фов", "лут-фов", "📦-лут-и-фов", "📦・лут-фов"),
    config.CHANNEL_MEMES: ("мемы", "🎭-мемы", "🎭・мемы"),
    config.CHANNEL_STAFF: ("штаб", "🔒-штаб", "🔒・штаб"),
}

VOICE_CHANNEL_ALIASES: dict[str, tuple[str, ...]] = {
    config.VOICE_LOBBY: ("Лобби", "лобби", "🔊・лобби", "🔊 Лобби"),
    config.VOICE_SQUAD_1: ("Сквад-1", "сквад-1", "🪖・сквад-1"),
    config.VOICE_SQUAD_2: ("Сквад-2", "сквад-2", "🪖・сквад-2"),
    config.VOICE_SQUAD_3: ("Сквад-3", "сквад-3", "🪖・сквад-3"),
    config.VOICE_AFK: ("AFK", "afk", "💤・afk", "💤 AFK"),
}

CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    config.CATEGORY_INFO: ("📋 ИНФО", "ИНФО", "━━ 📋 ИНФО ━━"),
    config.CATEGORY_RECRUIT: ("📝 НАБОР", "НАБОР", "━━ 📝 НАБОР ━━"),
    config.CATEGORY_CLAN: ("🐕 КЛАН", "🐕 СТАЯ", "КЛАН", "СТАЯ", "━━ 🐕 СТАЯ ━━"),
    config.CATEGORY_VOICE: ("🔊 ГОЛОС", "ГОЛОС", "━━ 🔊 ГОЛОС ━━"),
    config.CATEGORY_STAFF: ("🛠 ШТАБ", "ШТАБ", "━━ 🛠 ШТАБ ━━"),
}


def _match_name(current: str, canonical: str, aliases: tuple[str, ...]) -> bool:
    names = {canonical.lower(), *(a.lower() for a in aliases)}
    return current.lower() in names


def find_text_channel(
    guild: disnake.Guild, canonical: str
) -> disnake.TextChannel | None:
    aliases = TEXT_CHANNEL_ALIASES.get(canonical, ())
    for ch in guild.text_channels:
        if _match_name(ch.name, canonical, aliases):
            return ch
    return None


def find_voice_channel(
    guild: disnake.Guild, canonical: str
) -> disnake.VoiceChannel | None:
    aliases = VOICE_CHANNEL_ALIASES.get(canonical, ())
    for ch in guild.voice_channels:
        if _match_name(ch.name, canonical, aliases):
            return ch
    return None


def find_category(
    guild: disnake.Guild, canonical: str
) -> disnake.CategoryChannel | None:
    aliases = CATEGORY_ALIASES.get(canonical, ())
    for cat in guild.categories:
        if _match_name(cat.name, canonical, aliases):
            return cat
    return None


async def ensure_styled_names(guild: disnake.Guild) -> dict[str, int]:
    """Переименовывает категории/каналы в актуальный стиль. Возвращает счётчики."""
    renamed = {"categories": 0, "text": 0, "voice": 0}

    for canonical, aliases in CATEGORY_ALIASES.items():
        cat = find_category(guild, canonical)
        if cat is None or cat.name == canonical:
            continue
        try:
            await cat.edit(name=canonical, reason="Handler: оформление названий")
            renamed["categories"] += 1
        except disnake.HTTPException:
            continue

    for canonical in TEXT_CHANNEL_ALIASES:
        ch = find_text_channel(guild, canonical)
        if ch is None or ch.name == canonical:
            continue
        try:
            await ch.edit(name=canonical, reason="Handler: оформление названий")
            renamed["text"] += 1
        except disnake.HTTPException:
            continue

    for canonical in VOICE_CHANNEL_ALIASES:
        ch = find_voice_channel(guild, canonical)
        if ch is None or ch.name == canonical:
            continue
        try:
            await ch.edit(name=canonical, reason="Handler: оформление названий")
            renamed["voice"] += 1
        except disnake.HTTPException:
            continue

    return renamed
