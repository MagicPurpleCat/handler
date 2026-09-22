"""Components v2-панель подачи заявки в клан."""

from __future__ import annotations

import disnake

import config
from bot.services.channel_panels import ACCENT_OLIVE, panel_kwargs

APPLY_BUTTON_ID = "wardogs:apply"

APPLY_PANEL_TEXT = (
    "## Набор в Handler\n"
    f"Готов вступить в стаю **{config.CLAN_NAME}**?\n\n"
    "### Что указать в форме\n"
    "• игровой ник в WARDOGS\n"
    "• основной класс — Assault / Medic / Support / Recon / Driver / Pilot\n"
    "• ссылку на профиль [wardogs.tools](https://wardogs.tools/) — "
    "офицер смотрит уровни классов и Wardog, без скринов\n"
    "• коротко — почему хочешь в клан\n\n"
    "### Зачем ссылка на wardogs.tools\n"
    "Это твой игровой профиль: ранги классов, уровень Wardog, кэш. "
    "Бот подтягивает стату в заявку и на догтаг — штаб видит, "
    "кем ты играешь, без переписки «скинь скрин».\n"
    "Скопируй адрес из браузера, даже с `/ru/` — подойдёт.\n\n"
    "### Что дальше\n"
    "Создастся личный канал заявки. Офицеры увидят твою стату и "
    "обсудят с тобой набор. После принятия откроется доступ к каналам "
    f"(роль **{config.ROLE_MEMBER}**).\n\n"
    "Новичков учим азам и помогаем во всём — главное желание играть вместе.\n\n"
    "Нажми кнопку ниже ↓"
)


def build_apply_panel_components() -> list:
    """Совместимость: компоненты без файла (редко нужно)."""
    return apply_panel_kwargs()["components"]


def apply_panel_kwargs() -> dict:
    row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Подать заявку",
            style=disnake.ButtonStyle.success,
            custom_id=APPLY_BUTTON_ID,
            emoji="🐕",
        )
    )
    return panel_kwargs(
        "apply",
        APPLY_PANEL_TEXT,
        accent=ACCENT_OLIVE,
        extra_rows=[row],
    )
