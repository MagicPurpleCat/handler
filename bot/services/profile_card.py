"""Карточка профиля бойца — тёмный dashboard-стиль Handler."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from PIL import Image, ImageDraw

import config
from bot.services import profile_icons as pico
from bot.services import ui_style as ui


W, H = 1100, 700


def _class_color(name: str | None) -> tuple[int, int, int]:
    if name and name in config.CLASS_ROLE_COLORS:
        v = config.CLASS_ROLE_COLORS[name]
        return ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)
    return ui.GOLD_DIM


def _level_frac(level: int | None, cap: int | None) -> tuple[float, str]:
    if not isinstance(level, int) or level <= 0:
        return 0.0, "—"
    if isinstance(cap, int) and cap > 0:
        frac = min(1.0, level / cap)
        return frac, f"{level}/{cap}"
    return 0.0, str(level)


def render_profile_card(
    *,
    display_name: str,
    game_nick: str | None,
    class_name: str | None,
    clan_role: str,
    joined_clan_at: float | None,
    avatar_bytes: bytes | None,
    game_stats: dict[str, Any] | None = None,
    activity_hours: float | None = None,
    reputation: int | None = None,
    play_as_classes: list[str] | None = None,
    clan_place: int | None = None,
    clan_total: int | None = None,
) -> bytes:
    stats = game_stats or {}
    wardog = stats.get("wardog_level")
    wardog_cap = stats.get("wardog_cap")
    cash = stats.get("cash")
    site_rank = stats.get("rank")
    roles_raw = stats.get("roles") or {}
    role_caps = stats.get("role_caps") or {}
    roles = {k: v for k, v in roles_raw.items() if str(k).upper() != "WARDOG"}
    stats_name = stats.get("display_name")
    nick = game_nick or stats_name or "—"

    joined = "—"
    if joined_clan_at:
        joined = datetime.fromtimestamp(joined_clan_at, tz=timezone.utc).strftime("%d.%m.%Y")

    w_frac, w_label = _level_frac(
        wardog if isinstance(wardog, int) else None,
        wardog_cap if isinstance(wardog_cap, int) else None,
    )
    w_left = ""
    if isinstance(wardog, int) and isinstance(wardog_cap, int) and wardog_cap > wardog:
        w_left = f"До cap · {wardog_cap - wardog} ур."

    base = ui.canvas(W, H)
    draw = ImageDraw.Draw(base)

    logo = ui.load_logo(config.ASSETS_DIR / "handler-avatar.png", 48)
    base.paste(logo, (36, 28), logo)
    draw.text((96, 30), "HANDLER", font=ui.font(22, bold=True), fill=ui.WHITE)
    draw.text((96, 56), "WAR DOGS", font=ui.font(11), fill=ui.MUTED)

    draw.text((W - 280, 28), "ДОГТАГ", font=ui.font(12), fill=ui.MUTED)
    role_label = clan_role or "Гость"
    tw, _ = ui.text_size(draw, role_label, ui.font(22, bold=True))
    draw.text((W - 36 - tw, 48), role_label, font=ui.font(22, bold=True), fill=ui.GOLD)

    lx0, ly0, lx1, ly1 = 28, 90, 400, H - 28
    ui.round_rect(base, (lx0, ly0, lx1, ly1), radius=22)

    if avatar_bytes:
        av_img = Image.open(io.BytesIO(avatar_bytes))
    else:
        av_img = Image.new("RGB", (128, 128), (40, 40, 48))
    avatar = ui.circle_avatar(av_img, 92, ring=ui.GOLD)
    base.paste(avatar, (52, 118), avatar)

    name = (display_name or "Боец")[:22]
    draw.text((168, 128), name, font=ui.font(26, bold=True), fill=ui.WHITE)
    draw.text((168, 164), f"Ник · {nick}", font=ui.font(13), fill=ui.MUTED)

    play_as = [c for c in (play_as_classes or ([class_name] if class_name else [])) if c]
    px, py = 168, 192
    if play_as:
        for cls in play_as[:4]:
            label = config.class_label_ru(cls).upper()
            w = ui.pill(
                base,
                (px, py),
                label,
                fill=(40, 34, 18),
                outline=_class_color(cls),
            )
            px += w
            if px > lx1 - 100:
                px = 168
                py += 32
    else:
        ui.pill(base, (168, 192), "БЕЗ КЛАССА", fill=(40, 34, 18), outline=ui.MUTED)

    draw.text((52, 248), "Wardog", font=ui.font(13, bold=True), fill=ui.MUTED)
    pw, _ = ui.text_size(draw, w_label, ui.font(13, bold=True))
    draw.text((lx1 - 28 - pw, 248), w_label, font=ui.font(13, bold=True), fill=ui.GOLD)
    ui.progress_bar(base, (52, 272, lx1 - 28, 288), w_frac)
    hint = w_left if w_left else (
        "Привяжи профиль · /привязка" if not isinstance(wardog, int) else ""
    )
    if hint:
        draw.text((52, 296), hint, font=ui.font(12), fill=ui.MUTED)

    ui.round_rect(base, (52, 330, lx1 - 28, 418), fill=ui.CARD_ALT, radius=16)
    draw.text((68, 344), "МЕСТО В СТАЕ", font=ui.font(11, bold=True), fill=ui.MUTED)
    if clan_place is not None and clan_total:
        clan_txt = f"#{clan_place} из {clan_total}"
        draw.text((68, 372), clan_txt, font=ui.font(28, bold=True), fill=ui.GOLD)
    else:
        draw.text((68, 372), "—", font=ui.font(28, bold=True), fill=ui.LABEL)

    draw.text((220, 344), "НА САЙТЕ", font=ui.font(11, bold=True), fill=ui.MUTED)
    site_txt = f"#{site_rank}" if site_rank is not None else "—"
    draw.text((220, 372), site_txt, font=ui.font(28, bold=True), fill=ui.CYAN)

    ui.round_rect(base, (52, 432, 210, H - 48), fill=ui.CARD_ALT, radius=14)
    ui.round_rect(base, (226, 432, lx1 - 28, H - 48), fill=ui.CARD_ALT, radius=14)
    draw.text((68, 446), "В СТАЕ С", font=ui.font(11, bold=True), fill=ui.MUTED)
    draw.text((68, 472), joined, font=ui.font(20, bold=True), fill=ui.WHITE)
    draw.text((242, 446), "ДЕНЬГИ", font=ui.font(11, bold=True), fill=ui.MUTED)
    cash_s = str(cash) if cash is not None else "—"
    draw.text((242, 472), cash_s[:14], font=ui.font(20, bold=True), fill=ui.GREEN)

    rx0, ry0, rx1, ry1 = 420, 90, W - 28, H - 28
    ui.round_rect(base, (rx0, ry0, rx1, ry1), radius=22)

    draw.text((448, 112), "КЛАССЫ · ПРОГРЕСС", font=ui.font(14, bold=True), fill=ui.WHITE)
    handle = f"@{str(nick).upper()[:18]}"
    hw, _ = ui.text_size(draw, handle, ui.font(12))
    draw.text((rx1 - 28 - hw, 114), handle, font=ui.font(12), fill=ui.MUTED)

    row_h = 52
    y0 = 148
    for cls in config.CLASSES:
        key_upper = cls.upper()
        lvl = None
        for k, v in roles.items():
            if str(k).upper() == key_upper:
                lvl = int(v) if isinstance(v, (int, float)) else None
                break
        cap = None
        for k, v in role_caps.items():
            if str(k).upper() == key_upper:
                cap = int(v) if isinstance(v, (int, float)) else None
                break
        frac, num_label = _level_frac(lvl, cap)
        label_ru = config.class_label_ru(cls)
        accent = _class_color(cls)

        ui.round_rect(base, (448, y0, rx1 - 28, y0 + row_h - 6), fill=ui.CARD_ALT, radius=12)
        pico.draw_icon(base, (460, y0 + 6), 36, cls, accent=accent)
        draw.text((508, y0 + 8), label_ru, font=ui.font(13, bold=True), fill=ui.WHITE)
        nw, _ = ui.text_size(draw, num_label, ui.font(12, bold=True))
        draw.text((rx1 - 40 - nw, y0 + 10), num_label, font=ui.font(12, bold=True), fill=accent)
        ui.progress_bar(base, (508, y0 + 30, rx1 - 40, y0 + 42), frac)
        y0 += row_h

    strip_y = y0 + 4
    if activity_hours is not None or (reputation is not None and reputation > 0):
        ui.round_rect(base, (448, strip_y, rx1 - 28, strip_y + 56), fill=ui.CARD_ALT, radius=14)
        sx = 464
        if activity_hours is not None:
            pico.draw_icon(base, (sx, strip_y + 10), 36, "activity")
            draw.text((sx + 48, strip_y + 12), "Активность 30д", font=ui.font(11), fill=ui.MUTED)
            draw.text(
                (sx + 48, strip_y + 28),
                f"{activity_hours:.1f} ч",
                font=ui.font(16, bold=True),
                fill=ui.WHITE,
            )
            sx += 220
        if reputation is not None and reputation > 0:
            pico.draw_icon(base, (sx, strip_y + 10), 36, "rep")
            draw.text((sx + 48, strip_y + 12), "Отметки стаи", font=ui.font(11), fill=ui.MUTED)
            draw.text(
                (sx + 48, strip_y + 28),
                str(reputation),
                font=ui.font(16, bold=True),
                fill=ui.WHITE,
            )

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
