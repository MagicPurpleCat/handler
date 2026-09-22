"""Онбординг после принятия в клан."""

from __future__ import annotations

import disnake

import config
from bot.db import Database
from bot.services.branding import attach_banner_to_embed
from bot.services.channel_style import find_text_channel
from bot.services.clan_ranks import resolve_channel

ONBOARD_PREFIX = "wardogs:onboard:"
STEP_LABELS = {
    "link": "Привязать wardogs.tools (`/привязка`) — стату на догтаг",
    "class": "Выбрать класс в #роли",
    "lobby": "Зайти в голосовое лобби",
    "tactics": "Прочитать #тактика",
}


def onboarding_embed(steps: dict[str, bool]) -> disnake.Embed:
    lines = []
    for step in config.ONBOARDING_STEPS:
        mark = "✅" if steps.get(step) else "⬜"
        lines.append(f"{mark} {STEP_LABELS.get(step, step)}")
    done = all(steps.get(s) for s in config.ONBOARDING_STEPS)
    footer = "Всё отмечено — добро пожаловать в стаю." if done else "Жми кнопки, когда сделаешь шаг."
    embed = disnake.Embed(
        title="Первые шаги в Handler",
        description=(
            f"Тебя приняли в **{config.CLAN_NAME}**. Короткий чеклист:\n\n"
            + "\n".join(lines)
            + "\n\n"
            "Ссылка [wardogs.tools](https://wardogs.tools/) нужна, чтобы догтаг "
            "и витрина стаи показывали твои уровни — не скринами, а живой статой."
        ),
        color=0x4A5D23 if done else 0xC4A35A,
    )
    embed.set_footer(text=footer)
    return embed


def onboarding_components(steps: dict[str, bool]) -> list[disnake.ui.ActionRow]:
    buttons = []
    for step in config.ONBOARDING_STEPS:
        done = bool(steps.get(step))
        label = {
            "link": "Привязка",
            "class": "Класс",
            "lobby": "Лобби",
            "tactics": "Тактика",
        }.get(step, step)
        buttons.append(
            disnake.ui.Button(
                style=disnake.ButtonStyle.success if done else disnake.ButtonStyle.secondary,
                label=f"{'✓ ' if done else ''}{label}",
                custom_id=f"{ONBOARD_PREFIX}{step}",
                disabled=done,
            )
        )
    # Discord: max 5 buttons per row
    return [disnake.ui.ActionRow(*buttons)]


async def send_onboarding_dm(
    user: disnake.abc.User,
    db: Database,
    discord_id: int,
) -> bool:
    steps = await db.init_onboarding(discord_id)
    embed = onboarding_embed(steps)
    embed, banner = attach_banner_to_embed(embed, "welcome_dm")
    try:
        await user.send(
            embed=embed,
            file=banner,
            components=onboarding_components(steps),
        )
        return True
    except disnake.HTTPException:
        return False


async def send_onboarding_fallback(
    guild: disnake.Guild,
    member: disnake.Member,
    db: Database,
) -> None:
    gcfg = await db.get_guild_config(guild.id)
    channel = resolve_channel(guild, gcfg, "general")
    if channel is None:
        channel = find_text_channel(guild, config.CHANNEL_GENERAL)
    if not isinstance(channel, disnake.TextChannel):
        return
    row = await db.get_member(member.id)
    if not row or not row.get("onboarding_json"):
        steps = await db.init_onboarding(member.id)
    else:
        steps = db.parse_onboarding(row)
    embed = onboarding_embed(steps)
    try:
        await channel.send(
            content=f"{member.mention} — ЛС закрыты, чеклист здесь:",
            embed=embed,
            components=onboarding_components(steps),
        )
    except disnake.HTTPException:
        pass
