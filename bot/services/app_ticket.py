"""Приватный канал-тикет для заявки в клан."""

from __future__ import annotations

import re

import disnake

import config
from bot.services.channel_style import find_category
from bot.services.roles_sync import find_role


def _safe_channel_name(app_id: int, game_nick: str) -> str:
    nick = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9\-]+", "-", game_nick.strip().lower())
    nick = nick.strip("-")[:24] or "boets"
    return f"заявка-{app_id}-{nick}"[:100]


async def create_application_channel(
    guild: disnake.Guild,
    *,
    applicant: disnake.Member,
    app_id: int,
    game_nick: str,
    category: disnake.CategoryChannel | None = None,
) -> disnake.TextChannel:
    everyone = guild.default_role
    commander = find_role(guild, config.ROLE_COMMANDER)
    officer = find_role(guild, config.ROLE_OFFICER)

    overwrites: dict[disnake.Role | disnake.Member, disnake.PermissionOverwrite] = {
        everyone: disnake.PermissionOverwrite(view_channel=False),
        applicant: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        guild.me: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
        ),
    }

    staff_ow = disnake.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        manage_messages=True,
        attach_files=True,
        embed_links=True,
    )
    if commander:
        overwrites[commander] = staff_ow
    if officer:
        overwrites[officer] = staff_ow
    hidden = disnake.PermissionOverwrite(view_channel=False)
    for role_name in (
        config.ROLE_GUEST,
        config.ROLE_RECRUIT,
        config.ROLE_MEMBER,
        config.ROLE_PAUSE,
    ):
        role = find_role(guild, role_name)
        if role:
            overwrites[role] = hidden

    if category is None:
        category = find_category(guild, config.CATEGORY_RECRUIT)

    return await guild.create_text_channel(
        name=_safe_channel_name(app_id, game_nick),
        overwrites=overwrites,
        category=category,
        topic=f"Заявка #{app_id} · {applicant.display_name} · {game_nick}",
        reason=f"Handler: заявка #{app_id}",
    )


async def delete_application_channel(
    channel: disnake.abc.GuildChannel | None,
    *,
    app_id: int,
    approved: bool,
) -> None:
    if not isinstance(channel, disnake.TextChannel):
        return
    status = "одобрена" if approved else "отклонена"
    try:
        await channel.delete(reason=f"Handler: заявка #{app_id} {status}")
    except disnake.HTTPException:
        pass
