"""Процедурные иконки для догтага — без emoji-шрифтов."""

from __future__ import annotations

from PIL import Image, ImageDraw

from bot.services import ui_style as ui


def _icon_canvas(size: int) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def draw_icon(
    base: Image.Image,
    xy: tuple[int, int],
    size: int,
    key: str,
    *,
    accent: tuple[int, int, int] | None = None,
) -> None:
    x, y = xy
    ui.round_rect(
        base,
        (x, y, x + size, y + size),
        fill=(36, 32, 22),
        outline=accent or ui.GOLD_DIM,
        radius=12,
    )
    icon = _render_glyph(key, size - 12, accent or ui.GOLD)
    base.alpha_composite(icon, (x + 6, y + 6))


def _render_glyph(key: str, size: int, color: tuple[int, int, int]) -> Image.Image:
    img = _icon_canvas(size)
    d = ImageDraw.Draw(img)
    m = size // 2
    s = max(2, size // 10)

    if key == "nick":
        d.rounded_rectangle((2, 2, size - 2, size - 2), radius=4, outline=color, width=s)
        d.line((m, m - 4, m, m + 2), fill=color, width=s)
        d.ellipse((m - 5, m - 12, m + 5, m - 2), outline=color, width=s)
    elif key == "class":
        d.polygon([(m, 2), (size - 2, size - 2), (2, size - 2)], outline=color, width=s)
    elif key == "cash":
        d.ellipse((2, 2, size - 2, size - 2), outline=color, width=s)
        d.text((m - 4, m - 8), "$", fill=color, font=ui.font(max(10, size // 2), bold=True))
    elif key == "joined":
        d.rectangle((4, m - 2, size - 4, size - 4), outline=color, width=s)
        d.line((4, m + 2, size - 4, m + 2), fill=color, width=s)
        for i in range(3):
            d.line((8 + i * 6, m - 6, 8 + i * 6, m + 2), fill=color, width=1)
    elif key == "activity":
        d.line((4, size - 4, m, m), fill=color, width=s)
        d.line((m, m, size - 4, 6), fill=color, width=s)
        d.ellipse((m - 3, m - 3, m + 3, m + 3), fill=color)
    elif key == "rep":
        d.polygon(
            [(m, 2), (m + 6, m - 2), (m + 4, m + 6), (m - 4, m + 6), (m - 6, m - 2)],
            outline=color,
            width=s,
        )
    elif key == "wardog":
        d.ellipse((4, 4, size - 4, size - 4), outline=color, width=s)
        d.line((m, m - 5, m, m + 5), fill=color, width=s)
        d.line((m - 5, m, m + 5, m), fill=color, width=s)
    elif key == "clan":
        d.polygon([(m, 3), (size - 3, m), (m, size - 3), (3, m)], outline=color, width=s)
    elif key == "site_rank":
        d.line((4, size - 4, size - 4, size - 4), fill=color, width=s)
        d.line((6, size - 8, 10, size - 14), fill=color, width=s)
        d.line((10, size - 14, 14, size - 6), fill=color, width=s)
    elif key in ("Assault", "Medic", "Support", "Recon", "Driver", "Pilot"):
        _class_glyph(d, key, size, color, s)
    else:
        d.ellipse((4, 4, size - 4, size - 4), outline=color, width=s)

    return img


def _class_glyph(
    d: ImageDraw.ImageDraw,
    key: str,
    size: int,
    color: tuple[int, int, int],
    s: int,
) -> None:
    m = size // 2
    if key == "Assault":
        d.line((m, 4, m, size - 4), fill=color, width=s + 1)
        d.polygon([(m, 4), (m + 8, 10), (m, 16)], fill=color)
    elif key == "Medic":
        d.rectangle((m - 8, m - 3, m + 8, m + 3), fill=color)
        d.rectangle((m - 3, m - 8, m + 3, m + 8), fill=color)
    elif key == "Support":
        d.rounded_rectangle((4, m - 4, size - 4, size - 4), radius=3, outline=color, width=s)
        d.line((8, m - 8, size - 8, m - 8), fill=color, width=s)
    elif key == "Recon":
        d.ellipse((6, 6, size - 6, size - 6), outline=color, width=s)
        d.ellipse((m - 3, m - 3, m + 3, m + 3), fill=color)
    elif key == "Driver":
        d.rounded_rectangle((3, m, size - 3, size - 4), radius=4, outline=color, width=s)
        d.ellipse((7, size - 8, 11, size - 4), fill=color)
        d.ellipse((size - 11, size - 8, size - 7, size - 4), fill=color)
    elif key == "Pilot":
        d.line((4, m + 2, size - 4, m + 2), fill=color, width=s)
        d.polygon([(m, 4), (size - 4, m + 2), (m, m + 6)], outline=color, width=s)
