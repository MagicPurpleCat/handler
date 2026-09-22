"""Bootstrap Discord-сервера War Dogs с нуля."""

from __future__ import annotations

from typing import Any

import disnake

import config
from bot.db import Database
from bot.services.channel_content import (
    apply_channel_topics,
    publish_apply,
    publish_loot,
    publish_role_select,
    publish_rules,
    publish_tactics,
)
from bot.services.channel_style import (
    find_category,
    find_text_channel,
    find_voice_channel,
)
from bot.services.class_roles import ensure_class_roles


async def _get_or_create_role(
    guild: disnake.Guild,
    name: str,
    *,
    color: int = 0,
    permissions: disnake.Permissions | None = None,
    hoist: bool = False,
    mentionable: bool = False,
) -> disnake.Role:
    existing = disnake.utils.get(guild.roles, name=name)
    if existing:
        return existing
    return await guild.create_role(
        name=name,
        colour=disnake.Colour(color),
        permissions=permissions or disnake.Permissions.none(),
        hoist=hoist,
        mentionable=mentionable,
        reason="Bootstrap War Dogs / Хендлер",
    )


async def _get_or_create_category(
    guild: disnake.Guild,
    name: str,
    overwrites: dict | None = None,
) -> disnake.CategoryChannel:
    existing = find_category(guild, name)
    if existing:
        if existing.name != name:
            try:
                await existing.edit(name=name, reason="Handler: стиль категорий")
            except disnake.HTTPException:
                pass
        if overwrites:
            try:
                await existing.edit(overwrites=overwrites, reason="Bootstrap overwrites")
            except disnake.HTTPException:
                pass
        return existing
    return await guild.create_category(
        name,
        overwrites=overwrites or {},
        reason="Bootstrap War Dogs / Хендлер",
    )


async def _get_or_create_text(
    category: disnake.CategoryChannel,
    name: str,
    overwrites: dict | None = None,
) -> disnake.TextChannel:
    guild = category.guild
    existing = find_text_channel(guild, name)
    if existing:
        changes: dict = {}
        if existing.name != name:
            changes["name"] = name
        if existing.category_id != category.id:
            changes["category"] = category
        if overwrites is not None:
            changes["overwrites"] = overwrites
        if changes:
            try:
                await existing.edit(**changes, reason="Handler: стиль каналов")
            except disnake.HTTPException:
                pass
        return existing
    return await guild.create_text_channel(
        name,
        category=category,
        overwrites=overwrites or {},
        reason="Bootstrap War Dogs / Хендлер",
    )


async def _get_or_create_voice(
    category: disnake.CategoryChannel,
    name: str,
    overwrites: dict | None = None,
) -> disnake.VoiceChannel:
    guild = category.guild
    existing = find_voice_channel(guild, name)
    if existing:
        changes: dict = {}
        if existing.name != name:
            changes["name"] = name
        if existing.category_id != category.id:
            changes["category"] = category
        if overwrites is not None:
            changes["overwrites"] = overwrites
        if changes:
            try:
                await existing.edit(**changes, reason="Handler: стиль войсов")
            except disnake.HTTPException:
                pass
        return existing
    return await guild.create_voice_channel(
        name,
        category=category,
        overwrites=overwrites or {},
        reason="Bootstrap War Dogs / Хендлер",
    )


async def bootstrap_guild(
    guild: disnake.Guild,
    db: Database,
    *,
    actor: disnake.Member | None = None,
) -> dict[str, Any]:
    """Создаёт роли, категории, каналы, базовые эмбеды. Идемпотентно."""

    everyone = guild.default_role

    guest = await _get_or_create_role(
        guild, config.ROLE_GUEST, color=config.ROLE_COLORS[config.ROLE_GUEST]
    )
    recruit = await _get_or_create_role(
        guild,
        config.ROLE_RECRUIT,
        color=config.ROLE_COLORS[config.ROLE_RECRUIT],
        hoist=True,
    )
    member_role = await _get_or_create_role(
        guild,
        config.ROLE_MEMBER,
        color=config.ROLE_COLORS[config.ROLE_MEMBER],
        hoist=True,
        mentionable=True,
    )
    officer = await _get_or_create_role(
        guild,
        config.ROLE_OFFICER,
        color=config.ROLE_COLORS[config.ROLE_OFFICER],
        permissions=disnake.Permissions(
            manage_messages=True,
            kick_members=True,
            moderate_members=True,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
        hoist=True,
    )
    commander = await _get_or_create_role(
        guild,
        config.ROLE_COMMANDER,
        color=config.ROLE_COLORS[config.ROLE_COMMANDER],
        permissions=disnake.Permissions(administrator=True),
        hoist=True,
    )

    pause = await _get_or_create_role(
        guild, config.ROLE_PAUSE, color=config.ROLE_COLORS[config.ROLE_PAUSE]
    )

    class_roles = await ensure_class_roles(guild)

    if actor and commander not in actor.roles:
        try:
            await actor.add_roles(commander, reason="Bootstrap: инициатор — Командир")
        except disnake.HTTPException:
            pass

    public_read = {
        everyone: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=True,
            read_message_history=True,
        ),
        officer: disnake.PermissionOverwrite(send_messages=True, manage_messages=True),
        commander: disnake.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    apply_ow = {
        everyone: disnake.PermissionOverwrite(
            view_channel=True, send_messages=False, read_message_history=True
        ),
        officer: disnake.PermissionOverwrite(send_messages=True, manage_messages=True),
    }

    mod_ow = {
        everyone: disnake.PermissionOverwrite(view_channel=False),
        officer: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            read_message_history=True,
        ),
        commander: disnake.PermissionOverwrite(view_channel=True, send_messages=True),
        member_role: disnake.PermissionOverwrite(view_channel=False),
    }

    clan_ow = {
        everyone: disnake.PermissionOverwrite(view_channel=False),
        member_role: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            connect=True,
            speak=True,
        ),
        officer: disnake.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            connect=True,
            speak=True,
        ),
        commander: disnake.PermissionOverwrite(view_channel=True, send_messages=True),
        recruit: disnake.PermissionOverwrite(view_channel=False),
        pause: disnake.PermissionOverwrite(
            connect=False,
            speak=False,
        ),
    }

    staff_ow = {
        everyone: disnake.PermissionOverwrite(view_channel=False),
        officer: disnake.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        commander: disnake.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    cat_info = await _get_or_create_category(guild, config.CATEGORY_INFO, public_read)
    cat_recruit = await _get_or_create_category(guild, config.CATEGORY_RECRUIT)
    cat_clan = await _get_or_create_category(guild, config.CATEGORY_CLAN, clan_ow)
    cat_voice = await _get_or_create_category(guild, config.CATEGORY_VOICE, clan_ow)
    cat_staff = await _get_or_create_category(guild, config.CATEGORY_STAFF, staff_ow)

    ch_rules = await _get_or_create_text(cat_info, config.CHANNEL_RULES, public_read)
    ch_announce = await _get_or_create_text(
        cat_info, config.CHANNEL_ANNOUNCEMENTS, public_read
    )
    ch_roles = await _get_or_create_text(cat_info, config.CHANNEL_ROLES_INFO, public_read)
    ch_apply = await _get_or_create_text(cat_recruit, config.CHANNEL_APPLY, apply_ow)
    ch_mod = await _get_or_create_text(cat_recruit, config.CHANNEL_MOD_APPS, mod_ow)
    ch_general = await _get_or_create_text(cat_clan, config.CHANNEL_GENERAL, clan_ow)
    ch_tactics = await _get_or_create_text(cat_clan, config.CHANNEL_TACTICS, clan_ow)
    ch_loot = await _get_or_create_text(cat_clan, config.CHANNEL_LOOT, clan_ow)
    ch_memes = await _get_or_create_text(cat_clan, config.CHANNEL_MEMES, clan_ow)
    ch_staff = await _get_or_create_text(cat_staff, config.CHANNEL_STAFF, staff_ow)

    vc_lobby = await _get_or_create_voice(cat_voice, config.VOICE_LOBBY, clan_ow)
    vc_s1 = await _get_or_create_voice(cat_voice, config.VOICE_SQUAD_1, clan_ow)
    vc_s2 = await _get_or_create_voice(cat_voice, config.VOICE_SQUAD_2, clan_ow)
    vc_s3 = await _get_or_create_voice(cat_voice, config.VOICE_SQUAD_3, clan_ow)
    vc_afk = await _get_or_create_voice(cat_voice, config.VOICE_AFK, clan_ow)

    try:
        await guild.edit(afk_channel=vc_afk, afk_timeout=300, reason="Bootstrap AFK")
    except disnake.HTTPException:
        pass

    # --- оформление каналов ---
    me = guild.me
    await apply_channel_topics(guild)
    await publish_rules(ch_rules, me=me)
    await publish_apply(ch_apply, me=me)
    await publish_tactics(ch_tactics, me=me)
    await publish_loot(ch_loot, me=me)
    await publish_role_select(ch_roles, me=me)

    cfg = {
        "roles": {
            "guest": guest.id,
            "recruit": recruit.id,
            "member": member_role.id,
            "officer": officer.id,
            "commander": commander.id,
            "pause": pause.id,
            "classes": {name: role.id for name, role in class_roles.items()},
        },
        "categories": {
            "info": cat_info.id,
            "recruit": cat_recruit.id,
            "clan": cat_clan.id,
            "voice": cat_voice.id,
            "staff": cat_staff.id,
        },
        "channels": {
            "rules": ch_rules.id,
            "announcements": ch_announce.id,
            "roles_info": ch_roles.id,
            "apply": ch_apply.id,
            "mod_apps": ch_mod.id,
            "general": ch_general.id,
            "tactics": ch_tactics.id,
            "loot": ch_loot.id,
            "memes": ch_memes.id,
            "staff": ch_staff.id,
            "voice_lobby": vc_lobby.id,
            "voice_squad_1": vc_s1.id,
            "voice_squad_2": vc_s2.id,
            "voice_squad_3": vc_s3.id,
            "voice_afk": vc_afk.id,
        },
    }
    await db.save_guild_config(guild.id, cfg)
    return cfg

