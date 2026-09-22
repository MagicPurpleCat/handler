"""Роли классов WARDOGS: создание и выдача по статистике заявки."""

from __future__ import annotations

import json
from typing import Any

import disnake

import config
from bot.services.roles_sync import find_role


def class_role_name(class_name: str) -> str:
    """Имя Discord-роли класса — на русском."""
    return config.class_label_ru(class_name)


def member_play_as_classes(member: disnake.Member) -> list[str]:
    """EN-ключи классов, которые висят на участнике (порядок CLASSES)."""
    names = {r.name for r in member.roles}
    out: list[str] = []
    for key in config.CLASSES:
        ru = class_role_name(key)
        if ru in names or key in names:
            out.append(key)
    return out


async def ensure_class_roles(guild: disnake.Guild) -> dict[str, disnake.Role]:
    """Создаёт/переименовывает роли классов. Возвращает {Assault: Role, ...}."""
    out: dict[str, disnake.Role] = {}
    for name in config.CLASSES:
        ru_name = class_role_name(name)
        role = find_role(guild, ru_name)
        if role is None:
            legacy = find_role(guild, name)
            if legacy is not None:
                try:
                    await legacy.edit(
                        name=ru_name,
                        reason="Handler: роль класса на русском",
                    )
                    role = legacy
                except disnake.HTTPException:
                    role = legacy
        if role is None:
            role = await guild.create_role(
                name=ru_name,
                colour=disnake.Colour(config.CLASS_ROLE_COLORS.get(name, 0x4A5D23)),
                hoist=False,
                mentionable=True,
                reason="Handler: роли классов WARDOGS",
            )
        out[name] = role
    return out


def _normalize_stats_roles(raw: dict[str, Any] | None) -> dict[str, int]:
    if not raw:
        return {}
    mapped: dict[str, int] = {}
    for key, val in raw.items():
        resolved = config.resolve_class_key(str(key))
        if resolved is None:
            for cls in config.CLASSES:
                if str(key).upper() == cls.upper():
                    resolved = cls
                    break
        if resolved is None:
            continue
        try:
            mapped[resolved] = int(val)
        except (TypeError, ValueError):
            pass
    return mapped


def classes_from_application(app: dict[str, Any]) -> list[str]:
    """
    Классы для выдачи после одобрения:
    - заявленный в форме класс;
    - класс с максимальным уровнем в статистике wardogs.tools.
    При ничьей по уровню — берём первый в порядке CLASSES.
    """
    chosen: list[str] = []
    declared = app.get("class")
    if declared in config.CLASSES:
        chosen.append(declared)
    elif isinstance(declared, str):
        resolved = config.resolve_class_key(declared)
        if resolved:
            chosen.append(resolved)

    stats_roles: dict[str, int] = {}
    raw = app.get("stats_json")
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            stats_roles = _normalize_stats_roles(data.get("roles"))
        except (json.JSONDecodeError, TypeError, AttributeError):
            stats_roles = {}

    if stats_roles:
        top_level = max(stats_roles.values())
        tops = [c for c in config.CLASSES if stats_roles.get(c) == top_level]
        primary = tops[0]
        if primary not in chosen:
            chosen.append(primary)

    return chosen


async def assign_class_roles(
    member: disnake.Member,
    class_names: list[str],
    *,
    reason: str = "Handler: класс по заявке",
) -> list[str]:
    """Выдаёт указанные класс-роли. Возвращает EN-ключи выданных."""
    roles_map = await ensure_class_roles(member.guild)
    given: list[str] = []
    to_add = []
    for name in class_names:
        role = roles_map.get(name)
        if role and role not in member.roles:
            to_add.append(role)
            given.append(name)
        elif role and role in member.roles:
            given.append(name)
    if to_add:
        try:
            await member.add_roles(*to_add, reason=reason)
        except disnake.HTTPException:
            for role in to_add:
                try:
                    await member.add_roles(role, reason=reason)
                except disnake.HTTPException:
                    key = next((k for k, r in roles_map.items() if r == role), None)
                    if key and key in given:
                        given.remove(key)
    return given


async def sync_play_as_roles(
    member: disnake.Member,
    selected: list[str],
) -> None:
    """Выставляет self-select роли «кем играю»: selected = список EN CLASSES."""
    roles_map = await ensure_class_roles(member.guild)
    wanted = {c for c in selected if c in config.CLASSES}
    to_add = []
    to_remove = []
    for name, role in roles_map.items():
        has = role in member.roles
        if name in wanted and not has:
            to_add.append(role)
        elif name not in wanted and has:
            to_remove.append(role)
    if to_remove:
        try:
            await member.remove_roles(*to_remove, reason="Handler: self-select классов")
        except disnake.HTTPException:
            pass
    if to_add:
        try:
            await member.add_roles(*to_add, reason="Handler: self-select классов")
        except disnake.HTTPException:
            pass
