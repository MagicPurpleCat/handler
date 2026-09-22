"""Загрузка статистики игрока с wardogs.tools по ссылке на профиль."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html import unescape
from typing import Any

import aiohttp

PLAYER_URL_RE = re.compile(
    r"^https?://(?:www\.)?wardogs\.tools"
    r"(?:/[a-z]{2,5})?"  # опциональная локаль: /ru, /en, …
    r"/player/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?"
    r"(?:\?.*)?$",
    re.IGNORECASE,
)

ROLE_BLOCK_RE = re.compile(
    r">(ASSAULT|MEDIC|RECON|SUPPORT|DRIVER|PILOT|WARDOG)</p>"
    r'<p class="text-2xl[^"]*">(\d+)<span[^>]*>\s*/\s*(\d+)</span></p>',
    re.IGNORECASE,
)


@dataclass
class WardogsPlayerStats:
    profile_url: str
    player_id: str
    display_name: str
    rank: int | None
    wardog_level: int | None
    cash: str | None
    xp_total: str | None
    season: str | None
    roles: dict[str, int]
    description: str | None
    og_image: str | None
    role_caps: dict[str, int] | None = None
    wardog_cap: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def embed_block(self) -> str:
        lines = [
            f"**{self.display_name}**"
            + (f" · Rank #{self.rank}" if self.rank else ""),
        ]
        if self.wardog_level is not None:
            if self.wardog_cap:
                lines.append(f"Wardog: **{self.wardog_level}/{self.wardog_cap}**")
            else:
                lines.append(f"Wardog: **{self.wardog_level}**")
        if self.cash:
            lines.append(f"Cash: **{self.cash}**")
        if self.xp_total:
            lines.append(f"XP: **{self.xp_total}**")
        if self.roles:
            role_bits = " · ".join(
                f"{name.title()} {lvl}" for name, lvl in self.roles.items() if name != "WARDOG"
            )
            if role_bits:
                lines.append(role_bits)
        if self.season:
            lines.append(f"Сезон: {self.season}")
        lines.append(f"[Открыть профиль]({self.profile_url})")
        return "\n".join(lines)


class WardogsStatsError(Exception):
    """Ошибка разбора или загрузки профиля."""


def normalize_profile_url(raw: str) -> tuple[str, str]:
    """Возвращает (canonical_url, player_uuid)."""
    text = raw.strip()
    # если кинули только uuid
    if re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        text,
        re.I,
    ):
        text = f"https://wardogs.tools/player/{text}"
    match = PLAYER_URL_RE.match(text)
    if not match:
        raise WardogsStatsError(
            "Нужна ссылка вида https://wardogs.tools/player/<uuid> "
            "(или с языком: /ru/player/…)"
        )
    player_id = match.group(1).lower()
    return f"https://wardogs.tools/player/{player_id}", player_id


def parse_player_html(html: str, profile_url: str, player_id: str) -> WardogsPlayerStats:
    title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    title = unescape(title_m.group(1)).strip() if title_m else ""
    # "G#7423 — Rank 1" / "G#7423 - Rank 1"
    display_name = title.split("—")[0].split("-")[0].strip() or "Игрок"
    rank = None
    rank_m = re.search(r"Rank\s+(\d+)", title, re.I)
    if rank_m:
        rank = int(rank_m.group(1))

    desc_m = re.search(
        r'<meta\s+name="description"\s+content="(.*?)"', html, re.I | re.S
    )
    description = unescape(desc_m.group(1)).strip() if desc_m else None

    og_m = re.search(
        r'<meta\s+property="og:image"\s+content="(.*?)"', html, re.I | re.S
    )
    og_image = unescape(og_m.group(1)).strip() if og_m else f"{profile_url}/og"

    wardog_level = None
    cash = None
    season = None
    if description:
        wl = re.search(r"Wardog level\s+(\d+)", description, re.I)
        if wl:
            wardog_level = int(wl.group(1))
        cash_m = re.search(r"(\$[\d,]+)", description)
        if cash_m:
            cash = cash_m.group(1)
        season_m = re.search(r"(Season\s+\d+)", description, re.I)
        if season_m:
            season = season_m.group(1)

    roles: dict[str, int] = {}
    role_caps: dict[str, int] = {}
    wardog_cap: int | None = None
    for name, level, cap in ROLE_BLOCK_RE.findall(html):
        key = name.upper()
        lvl_i, cap_i = int(level), int(cap)
        roles[key] = lvl_i
        if key == "WARDOG":
            if wardog_level is None:
                wardog_level = lvl_i
            wardog_cap = cap_i
        else:
            role_caps[key] = cap_i

    xp_m = re.search(r"([\d,]+)\s*XP total", html, re.I)
    xp_total = xp_m.group(1) if xp_m else None

    if wardog_level is None and not roles:
        raise WardogsStatsError(
            "Не удалось прочитать статистику. Проверь, что профиль публичный и ссылка верная."
        )

    class_roles = {k: v for k, v in roles.items() if k != "WARDOG"}
    return WardogsPlayerStats(
        profile_url=profile_url,
        player_id=player_id,
        display_name=display_name,
        rank=rank,
        wardog_level=wardog_level,
        cash=cash,
        xp_total=xp_total,
        season=season,
        roles=class_roles,
        description=description,
        og_image=og_image,
        role_caps=role_caps,
        wardog_cap=wardog_cap,
    )


async def fetch_player_stats(
    raw_url: str,
    *,
    session: aiohttp.ClientSession | None = None,
) -> WardogsPlayerStats:
    profile_url, player_id = normalize_profile_url(raw_url)
    headers = {
        "User-Agent": "HandlerBot/1.0 (+War Dogs clan; discord)",
        "Accept": "text/html,application/xhtml+xml",
    }
    timeout = aiohttp.ClientTimeout(total=20)

    async def _get(sess: aiohttp.ClientSession) -> str:
        async with sess.get(profile_url) as resp:
            if resp.status == 404:
                raise WardogsStatsError("Профиль не найден (404).")
            if resp.status >= 400:
                raise WardogsStatsError(f"Сайт вернул ошибку HTTP {resp.status}.")
            return await resp.text()

    if session is not None:
        html = await _get(session)
    else:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as sess:
            html = await _get(sess)
    return parse_player_html(html, profile_url, player_id)


def is_profile_url(raw: str) -> bool:
    try:
        normalize_profile_url(raw)
        return True
    except WardogsStatsError:
        return False
