"""Контент и оформление каналов Handler (Components v2)."""

from __future__ import annotations

import disnake

import config
from bot.services.channel_panels import (
    ACCENT_GOLD,
    ACCENT_OLIVE,
    ACCENT_STEEL,
    clear_bot_messages,
    panel_kwargs,
)
from bot.services.channel_style import ensure_styled_names, find_text_channel


PLAY_AS_SELECT_ID = "wardogs:play_as"

CHANNEL_TOPICS: dict[str, str] = {
    config.CHANNEL_RULES: "Правила стаи Handler · War Dogs · WARDOGS",
    config.CHANNEL_ANNOUNCEMENTS: "Официальные анонсы Handler",
    config.CHANNEL_ROLES_INFO: "Роли клана и выбор класса",
    config.CHANNEL_APPLY: "Подача заявки в Handler",
    config.CHANNEL_MOD_APPS: "Модерация заявок · только штаб",
    config.CHANNEL_GENERAL: "Общий чат стаи",
    config.CHANNEL_TACTICS: "Тактики Control Zone · FOB · фланг",
    config.CHANNEL_LOOT: "Лут · шаринг · FOB",
    config.CHANNEL_MEMES: "Мемы стаи",
    config.CHANNEL_STAFF: "Штаб офицеров",
}


def rules_text() -> str:
    return (
        f"## Правила стаи · {config.CLAN_NAME}\n"
        "Handler держит порядок, чтобы в бою было спокойно и по делу.\n\n"
        "### 01 · Уважение\n"
        "• Без токсичности, оскорблений и токсичного фарма тиммейтов.\n"
        "• Ошибка → фикс → дальше. Не раздуваем срачи в общем чате.\n\n"
        "### 02 · Игра и связь\n"
        "• Играем **WARDOGS**: координируемся в войсе, короткие коллы.\n"
        "• Лут делится по договорённости — подробности в канале лута.\n\n"
        "### 03 · Конфиденциальность\n"
        "• Не сливай тактику, скрины штаба и внутренние договорённости наружу.\n\n"
        "### 04 · Споры\n"
        "• Конфликты — к офицерам / в штаб, не токсиком в общем чате.\n\n"
        "### 05 · Набор\n"
        "• В заявке нужна ссылка на профиль [wardogs.tools](https://wardogs.tools/) — "
        "по ней бот и офицеры видят твои классы и уровень Wardog.\n"
        f"• После принятия получишь роль **{config.ROLE_MEMBER}** и доступ к каналам стаи.\n\n"
        f"— **{config.CLAN_NAME}** · Handler на связи"
    )


def tactics_text() -> str:
    return (
        "## Тактики Handler\n"
        "Рабочие схемы для **Control Zone / WARDOGS**. "
        "Ориентиры стаи — адаптируй под карту и состав.\n\n"
        "### 1 · FOB First\n"
        "**Суть:** ранняя логистика важнее лишних киллов.\n"
        "• **Support** тянет материалы и ставит FOB ближе к зоне\n"
        "• **Driver** возит по короткому маршруту, без героизма\n"
        "• **Assault / Medic** держат периметр стройки\n"
        "• Когда FOB стоит — давите зону с респауном и патронами\n"
        "*Когда:* старт матча, слабый опыт, дальние точки\n\n"
        "### 2 · Anchor + Flank\n"
        "**Суть:** один отряд держит фронт, второй заходит с фланга.\n"
        "• **Якорь:** Assault + Medic + Support\n"
        "• **Фланг:** Recon + Assault — споты, срез логистики\n"
        "• Не оба отряда в одно узкое место\n"
        "• Голос: «давим» / «зашли» — синхрон важнее килла\n"
        "*Когда:* середина матча, равный файт за зону\n\n"
        "### 3 · Logi Deny\n"
        "**Суть:** режем ресапплай и технику, не только пехоту на точке.\n"
        "• **Recon** спотит дороги и вертолётные подходы\n"
        "• **Driver / Pilot** — удар по колонне и отход\n"
        "• Минимум один **Medic** на рейде\n"
        "• После успеха сразу к зоне: килл логистики ≠ удержание\n"
        "*Когда:* враг сидит на FOB и таскает ящики\n\n"
        "### 4 · Air / Armor Window\n"
        "**Суть:** техника работает окном, не соло до конца жизни.\n"
        "• Заход, когда пехота давит или спотнула ПВО/AT\n"
        "• Support держит патроны/ремки на ближайшем FOB\n"
        "• Один голос: «окно открыто / закрыто»\n"
        "• Не чините танк под прицелом\n\n"
        "### Связь стаи\n"
        "• Коротко: **где** · **что вижу** · **что нужно**\n"
        "• В бою приоритет войса; канал тактики — если голоса нет\n"
        "• Лут и FOB — в канале лута"
    )


def loot_text() -> str:
    return (
        "## Лут-инфо Handler\n"
        "Меньше конфликтов — больше пользы скваду.\n\n"
        "### Приоритеты подбора\n"
        "1. **Выживание сквада** — мед, патроны, плиты тому, кто в бою\n"
        "2. **Роль** — медику сумка, саппорту строй и ящики, разведке оптика, "
        "пилоту/водителю ремки\n"
        "3. **Прокачка / анлок** — отдай, если тебе «просто лежит»\n"
        "4. **Личный комфорт** — косметика и дубликаты в конце\n\n"
        "### Правила шаринга\n"
        "• Совместный выход — делёж по договорённости до рейда "
        "(или по роли и нужде)\n"
        "• Редкий соло-лут можно оставить, но скажи скваду, если это AT / ПВО / дефиб\n"
        "• Не нинзи общие ящики FOB без спроса\n"
        "• Споры — в штаб, не токсиком в общий\n\n"
        "### Что тащить по ролям\n"
        "• **Medic** — сумки, дефиб, батареи\n"
        "• **Support** — строй, supply crates, патроны\n"
        "• **Assault** — броня, основной ствол\n"
        "• **Recon** — оптика, спот-кит\n"
        "• **Driver / Pilot** — ремонт, топливо, вооружение\n\n"
        "### FOB и склад\n"
        "• Ящики на FOB — ресурс **стаи на матч**, не личный склад\n"
        "• Перед опустошением крейта — спроси в войсе\n"
        "• После фарма можно кратко написать сюда, что привезли\n\n"
        "Сверяй анлоки с [wardogs.tools](https://wardogs.tools/) — патчи меняют мету."
    )


def roles_text() -> str:
    classes = " · ".join(f"**{config.class_label_ru(c)}**" for c in config.CLASSES)
    return (
        "## Роли клана Handler\n"
        "Кто ты в стае и за кого играешь в WARDOGS.\n\n"
        "### Доступ\n"
        f"• **{config.ROLE_MEMBER}** — клановые каналы и голос\n"
        f"• **{config.ROLE_RECRUIT}** — заявка на рассмотрении\n"
        f"• **{config.ROLE_OFFICER}** / **{config.ROLE_COMMANDER}** — набор и штаб\n\n"
        "### За кого играешь\n"
        "Выбери **один или несколько** классов ниже. "
        "Можно менять в любой момент — селект заново выставит роли.\n\n"
        f"{classes}"
    )


def play_as_select() -> disnake.ui.StringSelect:
    colors_desc = {
        "Assault": "Штурм · фронт",
        "Medic": "Лечение · дефиб",
        "Support": "FOB · ящики",
        "Recon": "Спот · фланг",
        "Driver": "Техника · логистика",
        "Pilot": "Воздух · удар",
    }
    options = [
        disnake.SelectOption(
            label=config.class_label_ru(name),
            value=name,
            description=colors_desc.get(name, f"Играю как {config.class_label_ru(name)}")[:100],
        )
        for name in config.CLASSES
    ]
    return disnake.ui.StringSelect(
        custom_id=PLAY_AS_SELECT_ID,
        placeholder="За кого играешь — можно несколько",
        min_values=0,
        max_values=len(config.CLASSES),
        options=options,
    )


async def _publish(
    channel: disnake.TextChannel,
    kwargs: dict,
    *,
    force: bool = False,
    me: disnake.ClientUser | disnake.Member | None = None,
) -> bool:
    if force and me is not None:
        await clear_bot_messages(channel, me)
    elif not force and await _has_bot_content(channel):
        return False
    await channel.send(**kwargs)
    return True


async def publish_rules(
    channel: disnake.TextChannel,
    *,
    force: bool = False,
    me: disnake.ClientUser | disnake.Member | None = None,
) -> bool:
    return await _publish(
        channel,
        panel_kwargs("rules", rules_text(), accent=ACCENT_OLIVE),
        force=force,
        me=me,
    )


async def publish_tactics(
    channel: disnake.TextChannel,
    *,
    force: bool = False,
    me: disnake.ClientUser | disnake.Member | None = None,
) -> bool:
    return await _publish(
        channel,
        panel_kwargs("tactics", tactics_text(), accent=ACCENT_STEEL),
        force=force,
        me=me,
    )


async def publish_loot(
    channel: disnake.TextChannel,
    *,
    force: bool = False,
    me: disnake.ClientUser | disnake.Member | None = None,
) -> bool:
    return await _publish(
        channel,
        panel_kwargs("loot", loot_text(), accent=ACCENT_GOLD),
        force=force,
        me=me,
    )


async def publish_role_select(
    channel: disnake.TextChannel,
    *,
    force: bool = False,
    me: disnake.ClientUser | disnake.Member | None = None,
) -> bool:
    row = disnake.ui.ActionRow(play_as_select())
    return await _publish(
        channel,
        panel_kwargs(
            "roles",
            roles_text(),
            accent=ACCENT_GOLD,
            extra_rows=[row],
        ),
        force=force,
        me=me,
    )


async def publish_apply(
    channel: disnake.TextChannel,
    *,
    force: bool = False,
    me: disnake.ClientUser | disnake.Member | None = None,
) -> bool:
    from bot.services.apply_panel import apply_panel_kwargs

    return await _publish(
        channel,
        apply_panel_kwargs(),
        force=force,
        me=me,
    )


async def apply_channel_topics(guild: disnake.Guild) -> int:
    """Ставит описания (topic) каналам по словарю."""
    updated = 0
    for name, topic in CHANNEL_TOPICS.items():
        ch = find_text_channel(guild, name)
        if not isinstance(ch, disnake.TextChannel):
            continue
        if ch.topic == topic:
            continue
        try:
            await ch.edit(topic=topic, reason="Handler: оформление каналов")
            updated += 1
        except disnake.HTTPException:
            continue
    return updated


async def republish_all(
    guild: disnake.Guild,
    me: disnake.ClientUser | disnake.Member,
    db_cfg: dict | None = None,
) -> dict[str, bool]:
    """Переоформляет ключевые каналы (удаляет старые посты бота)."""

    await ensure_styled_names(guild)

    def _ch(key: str, fallback_name: str) -> disnake.TextChannel | None:
        if db_cfg:
            cid = db_cfg.get("channels", {}).get(key)
            if cid:
                ch = guild.get_channel(cid)
                if isinstance(ch, disnake.TextChannel):
                    return ch
        return find_text_channel(guild, fallback_name)

    await apply_channel_topics(guild)
    results = {
        "rules": await publish_rules(
            _ch("rules", config.CHANNEL_RULES), force=True, me=me  # type: ignore[arg-type]
        )
        if _ch("rules", config.CHANNEL_RULES)
        else False,
        "apply": await publish_apply(
            _ch("apply", config.CHANNEL_APPLY), force=True, me=me  # type: ignore[arg-type]
        )
        if _ch("apply", config.CHANNEL_APPLY)
        else False,
        "roles": await publish_role_select(
            _ch("roles_info", config.CHANNEL_ROLES_INFO), force=True, me=me  # type: ignore[arg-type]
        )
        if _ch("roles_info", config.CHANNEL_ROLES_INFO)
        else False,
        "tactics": await publish_tactics(
            _ch("tactics", config.CHANNEL_TACTICS), force=True, me=me  # type: ignore[arg-type]
        )
        if _ch("tactics", config.CHANNEL_TACTICS)
        else False,
        "loot": await publish_loot(
            _ch("loot", config.CHANNEL_LOOT), force=True, me=me  # type: ignore[arg-type]
        )
        if _ch("loot", config.CHANNEL_LOOT)
        else False,
    }
    return results


async def _has_bot_content(channel: disnake.TextChannel) -> bool:
    async for msg in channel.history(limit=15):
        if msg.author.bot and (
            msg.embeds or msg.components or getattr(msg.flags, "is_components_v2", False)
        ):
            return True
    return False
