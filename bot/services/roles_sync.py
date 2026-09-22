"""Поиск ролей гильдии."""

from __future__ import annotations

import disnake


def find_role(guild: disnake.Guild, name: str) -> disnake.Role | None:
    return disnake.utils.get(guild.roles, name=name)
