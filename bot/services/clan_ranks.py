"""Проверки рангов клана."""

from __future__ import annotations

import disnake

import config
from bot.services.roles_sync import find_role


def is_staff(member: disnake.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    names = {r.name for r in member.roles}
    return config.ROLE_OFFICER in names or config.ROLE_COMMANDER in names


def has_clan_rank(member: disnake.Member, *role_names: str) -> bool:
    names = {r.name for r in member.roles}
    return any(n in names for n in role_names)


def resolve_role(
    guild: disnake.Guild,
    gcfg: dict | None,
    key: str,
    fallback_name: str,
) -> disnake.Role | None:
    if gcfg:
        rid = (gcfg.get("roles") or {}).get(key)
        if rid:
            role = guild.get_role(int(rid))
            if role:
                return role
    return find_role(guild, fallback_name)


def resolve_channel(
    guild: disnake.Guild,
    gcfg: dict | None,
    key: str,
) -> disnake.abc.GuildChannel | None:
    if not gcfg:
        return None
    cid = (gcfg.get("channels") or {}).get(key)
    if not cid:
        return None
    return guild.get_channel(int(cid))
