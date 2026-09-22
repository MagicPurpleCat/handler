"""Общие Components v2-панели для оформления каналов Handler."""

from __future__ import annotations

import disnake
from disnake.ui.media_gallery import MediaGalleryItem

from bot.services.branding import banner_filename, banner_path

# Акценты панелей
ACCENT_OLIVE = 0x4A5D23
ACCENT_GOLD = 0xC4A35A
ACCENT_STEEL = 0x5B7C99
ACCENT_RUST = 0xB85C38
ACCENT_SKY = 0x6B8E9F


def panel_kwargs(
    banner_key: str,
    text: str,
    *,
    accent: int = ACCENT_OLIVE,
    extra_rows: list | None = None,
) -> dict:
    """Сборка сообщения: баннер + текст (+ опциональные ActionRow)."""
    fname = banner_filename(banner_key)
    children: list = [
        disnake.ui.MediaGallery(MediaGalleryItem(f"attachment://{fname}")),
        disnake.ui.TextDisplay(text),
    ]
    if extra_rows:
        children.append(disnake.ui.Separator())
        children.extend(extra_rows)

    return {
        "components": [
            disnake.ui.Container(
                *children,
                accent_colour=disnake.Colour(accent),
            )
        ],
        "file": disnake.File(banner_path(banner_key), filename=fname),
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def section(title: str, body: str) -> str:
    return f"### {title}\n{body}"


def bullet(*lines: str) -> str:
    return "\n".join(f"• {line}" for line in lines)


async def clear_bot_messages(
    channel: disnake.TextChannel,
    me: disnake.ClientUser | disnake.Member,
    *,
    limit: int = 40,
) -> int:
    """Удаляет сообщения бота в канале (для переоформления)."""
    deleted = 0
    async for msg in channel.history(limit=limit):
        if msg.author.id != me.id:
            continue
        try:
            await msg.delete()
            deleted += 1
        except disnake.HTTPException:
            continue
    return deleted
