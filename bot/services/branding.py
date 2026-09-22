"""Брендированные баннеры Handler — тёмный dashboard-стиль."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import config
from bot.services import ui_style as ui

LOGO_PATH = config.ASSETS_DIR / "handler-avatar.png"
BANNERS_DIR = config.ASSETS_DIR / "banners"
STYLE_MARK = BANNERS_DIR / f".style_v{ui.STYLE_VERSION}"

BANNER_COPY: dict[str, tuple[str, str]] = {
    "rules": ("ПРАВИЛА СТАИ", "Handler · War Dogs · WARDOGS"),
    "roles": ("РОЛИ КЛАНА", "Доступ · набор · штаб"),
    "apply": ("НАБОР В HANDLER", "Подай заявку в стаю"),
    "application_new": ("НОВАЯ ЗАЯВКА", "Офицеры · модерация"),
    "application_approved": ("ЗАЯВКА ОДОБРЕНА", "Добро пожаловать в стаю"),
    "application_rejected": ("ЗАЯВКА ОТКЛОНЕНА", "Можно подать снова позже"),
    "server_ready": ("СЕРВЕР ПОДНЯТ", "Инфраструктура Handler готова"),
    "welcome_dm": ("ТЫ В СТАЕ", "Каналы клана открыты"),
    "rejected_dm": ("ЗАЯВКА ОТКЛОНЕНА", "Handler · War Dogs"),
    "profile": ("ДОГТАГ", "Профиль бойца стаи"),
    "tactics": ("ТАКТИКИ СТАИ", "FOB · фланг · логистика"),
    "loot": ("ЛУТ-ИНФО", "Приоритеты · шаринг · FOB"),
    "link": ("ПРОФИЛЬ ПРИВЯЗАН", "Статистика wardogs.tools"),
}

WIDTH, HEIGHT = 960, 340


def _make_banner(title: str, subtitle: str) -> Image.Image:
    base = ui.canvas(WIDTH, HEIGHT)
    draw = ImageDraw.Draw(base)

    # основная карточка
    ui.round_rect(base, (24, 24, WIDTH - 24, HEIGHT - 24), radius=24)

    logo = ui.load_logo(LOGO_PATH, 180)
    # лого в карточке слева
    ui.round_rect(base, (48, 52, 248, HEIGHT - 52), fill=ui.CARD_ALT, radius=20)
    base.paste(logo, (58, (HEIGHT - logo.height) // 2), logo)

    draw.text((280, 78), "HANDLER", font=ui.font(14, bold=True), fill=ui.GOLD)
    draw.text((280, 108), title, font=ui.font(36, bold=True), fill=ui.WHITE)
    draw.text((280, 168), subtitle, font=ui.font(18), fill=ui.MUTED)

    # нижняя полоска-акцент
    ui.round_rect(base, (280, HEIGHT - 88, WIDTH - 56, HEIGHT - 56), fill=ui.CARD_ALT, radius=12)
    draw.text(
        (300, HEIGHT - 80),
        "Хендлер  ·  клан Handler  ·  WARDOGS",
        font=ui.font(14),
        fill=ui.MUTED,
    )
    return base.convert("RGB")


def banner_path(key: str, *, force: bool = False) -> Path:
    if key not in BANNER_COPY:
        raise KeyError(f"Unknown banner key: {key}")
    BANNERS_DIR.mkdir(parents=True, exist_ok=True)
    path = BANNERS_DIR / f"{key}.png"
    need = force or not path.exists() or not STYLE_MARK.exists()
    if need:
        title, subtitle = BANNER_COPY[key]
        _make_banner(title, subtitle).save(path, "PNG", optimize=True)
    return path


def ensure_all_banners(*, force: bool = False) -> None:
    BANNERS_DIR.mkdir(parents=True, exist_ok=True)
    stale = not STYLE_MARK.exists()
    for key in BANNER_COPY:
        banner_path(key, force=force or stale)
    STYLE_MARK.write_text(str(ui.STYLE_VERSION), encoding="utf-8")
    # убрать старые маркеры
    for old in BANNERS_DIR.glob(".style_v*"):
        if old.name != STYLE_MARK.name:
            try:
                old.unlink()
            except OSError:
                pass


def banner_bytes(key: str) -> bytes:
    return banner_path(key).read_bytes()


def banner_filename(key: str) -> str:
    return f"banner_{key}.png"


def open_banner_file(key: str):
    import disnake

    path = banner_path(key)
    return disnake.File(path, filename=banner_filename(key))


def attach_banner_to_embed(embed, key: str):
    fname = banner_filename(key)
    embed.set_image(url=f"attachment://{fname}")
    return embed, open_banner_file(key)


def logo_thumb_file():
    import disnake

    return disnake.File(LOGO_PATH, filename="handler-avatar.png")
