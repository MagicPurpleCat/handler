"""Конфигурация бота Хендлер (War Dogs)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("/data") if "AMVERA" in os.environ else BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
DB_PATH = DATA_DIR / "handler.db"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("GUILD_ID") or 0) or None

BOT_NAME = "Хендлер"
CLAN_NAME = "War Dogs"

# Автообновление статы с wardogs.tools
STATS_REFRESH_MINUTES = 10
STATS_REFRESH_DELAY_SEC = 1.5  # пауза между запросами, чтобы не долбить сайт

CLASSES = ("Assault", "Medic", "Support", "Recon", "Driver", "Pilot")

# Русские названия для UI / Discord-ролей (ключ EN — для scrape и value селекта)
CLASS_LABELS_RU = {
    "Assault": "Штурмовик",
    "Medic": "Медик",
    "Support": "Поддержка",
    "Recon": "Разведчик",
    "Driver": "Водитель",
    "Pilot": "Пилот",
}

# Discord-роли классов (имя роли = CLASS_LABELS_RU)
CLASS_ROLE_COLORS = {
    "Assault": 0xB85C38,
    "Medic": 0x2E8B57,
    "Support": 0x4A7C59,
    "Recon": 0x5B7C99,
    "Driver": 0x8B7355,
    "Pilot": 0x6B8E9F,
}


def class_label_ru(name: str | None) -> str:
    if not name:
        return "—"
    return CLASS_LABELS_RU.get(name, name)


def resolve_class_key(raw: str) -> str | None:
    """EN-ключ класса из EN/RU ввода (без учёта регистра)."""
    text = raw.strip()
    if not text:
        return None
    lower = text.lower()
    by_en = {c.lower(): c for c in CLASSES}
    if lower in by_en:
        return by_en[lower]
    by_ru = {label.lower(): key for key, label in CLASS_LABELS_RU.items()}
    if lower in by_ru:
        return by_ru[lower]
    aliases = {
        "infantry": "Assault",
        "штурм": "Assault",
        "саппорт": "Support",
        "разведка": "Recon",
    }
    return aliases.get(lower)

ROLE_GUEST = "Гость"
ROLE_RECRUIT = "Рекрут"
ROLE_MEMBER = "War Dog"
ROLE_OFFICER = "Офицер"
ROLE_COMMANDER = "Командир"
ROLE_PAUSE = "Пауза"

CATEGORY_INFO = "━━ 📋 ИНФО ━━"
CATEGORY_RECRUIT = "━━ 📝 НАБОР ━━"
CATEGORY_CLAN = "━━ 🐕 СТАЯ ━━"
CATEGORY_VOICE = "━━ 🔊 ГОЛОС ━━"
CATEGORY_STAFF = "━━ 🛠 ШТАБ ━━"

CHANNEL_RULES = "📜・правила"
CHANNEL_ANNOUNCEMENTS = "📢・анонсы"
CHANNEL_ROLES_INFO = "🎖️・роли"
CHANNEL_APPLY = "🐕・заявки"
CHANNEL_MOD_APPS = "🛡️・мод-заявки"
CHANNEL_GENERAL = "💬・общий"
CHANNEL_TACTICS = "⚔️・тактика"
CHANNEL_LOOT = "📦・лут-фов"
CHANNEL_MEMES = "🎭・мемы"
CHANNEL_STAFF = "🔒・штаб"

VOICE_LOBBY = "🔊・лобби"
VOICE_SQUAD_1 = "🪖・сквад-1"
VOICE_SQUAD_2 = "🪖・сквад-2"
VOICE_SQUAD_3 = "🪖・сквад-3"
VOICE_AFK = "💤・afk"

# Активность в войсах (без Discord XP)
ACTIVITY_MIN_SESSION_SEC = 120  # короче — не считаем
ACTIVITY_VOICE_KEYS = (
    "voice_lobby",
    "voice_squad_1",
    "voice_squad_2",
    "voice_squad_3",
)

# Репутация «собака стаи»
REPUTATION_DAILY_LIMIT = 5

# Авто-архив неактивных
ARCHIVE_INACTIVE_DAYS = 30
ARCHIVE_CHECK_HOURS = 24

# Витрина клана
SHOWCASE_TOP_N = 5

# Онбординг после approve
ONBOARDING_STEPS = ("link", "class", "lobby", "tactics")

ROLE_COLORS = {
    ROLE_GUEST: 0x8B8B7A,
    ROLE_RECRUIT: 0xC4A35A,
    ROLE_MEMBER: 0x4A5D23,
    ROLE_OFFICER: 0x3D5A80,
    ROLE_COMMANDER: 0x8B0000,
    ROLE_PAUSE: 0x6B6B6B,
}
