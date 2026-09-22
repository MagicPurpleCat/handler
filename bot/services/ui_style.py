"""Общий тёмный UI-стиль (карточки · золото · скругления) для Handler."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

# Палитра в духе референса
BG = (11, 11, 13)
CARD = (22, 22, 26)
CARD_ALT = (28, 28, 34)
BORDER = (42, 42, 50)
GOLD = (212, 175, 55)
GOLD_DIM = (168, 138, 50)
GOLD_SOFT = (196, 163, 90)
WHITE = (245, 245, 247)
MUTED = (140, 140, 150)
LABEL = (110, 110, 120)
GREEN = (80, 200, 120)
CYAN = (90, 170, 230)
RED = (220, 90, 90)

STYLE_VERSION = 3


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    bundled = config.ASSETS_DIR / "fonts" / (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    )
    candidates: list[str | Path] = [bundled]
    candidates.extend(
        ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")
    )
    for name in candidates:
        try:
            return ImageFont.truetype(str(name), size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    b = draw.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def canvas(width: int, height: int) -> Image.Image:
    img = Image.new("RGBA", (width, height), (*BG, 255))
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((width - 420, -180, width + 160, 320), fill=(*GOLD, 28))
    gd.ellipse((-200, height - 280, 280, height + 120), fill=(*GOLD, 14))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    return Image.alpha_composite(img, glow)


def round_rect(
    base: Image.Image,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int] = CARD,
    outline: tuple[int, int, int] | None = BORDER,
    radius: int = 18,
    width: int = 1,
) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        box,
        radius=radius,
        fill=(*fill, 255),
        outline=(*outline, 255) if outline else None,
        width=width,
    )
    base.alpha_composite(layer)


def icon_box(
    base: Image.Image,
    xy: tuple[int, int],
    size: int,
    glyph: str,
    *,
    fill: tuple[int, int, int] = (36, 32, 22),
) -> None:
    x, y = xy
    round_rect(
        base,
        (x, y, x + size, y + size),
        fill=fill,
        outline=GOLD_DIM,
        radius=12,
    )
    draw = ImageDraw.Draw(base)
    fnt = font(max(14, size // 2), bold=True)
    tw, th = text_size(draw, glyph, fnt)
    draw.text(
        (x + (size - tw) / 2, y + (size - th) / 2 - 1),
        glyph,
        font=fnt,
        fill=GOLD,
    )


def pill(
    base: Image.Image,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int] = (40, 34, 18),
    outline: tuple[int, int, int] = GOLD_DIM,
) -> int:
    draw = ImageDraw.Draw(base)
    fnt = font(12, bold=True)
    tw, th = text_size(draw, text, fnt)
    pad_x, h = 14, 26
    w = tw + pad_x * 2
    x, y = xy
    round_rect(base, (x, y, x + w, y + h), fill=fill, outline=outline, radius=h // 2)
    draw = ImageDraw.Draw(base)
    draw.text((x + pad_x, y + (h - th) / 2 - 1), text, font=fnt, fill=GOLD)
    return w + 8


def progress_bar(
    base: Image.Image,
    box: tuple[int, int, int, int],
    fraction: float,
) -> None:
    x0, y0, x1, y1 = box
    round_rect(base, box, fill=(18, 18, 22), outline=BORDER, radius=8)
    frac = max(0.0, min(1.0, fraction))
    if frac <= 0:
        return
    inner = Image.new("RGBA", base.size, (0, 0, 0, 0))
    fill_w = int((x1 - x0 - 4) * frac)
    ImageDraw.Draw(inner).rounded_rectangle(
        (x0 + 2, y0 + 2, x0 + 2 + max(8, fill_w), y1 - 2),
        radius=6,
        fill=(*GOLD, 255),
    )
    # лёгкий градиент поверх
    base.alpha_composite(inner)


def circle_avatar(
    avatar: Image.Image,
    size: int,
    *,
    ring: tuple[int, int, int] = GOLD,
    online: bool = True,
) -> Image.Image:
    avatar = avatar.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    out = size + 10
    canvas_a = Image.new("RGBA", (out, out), (0, 0, 0, 0))
    # glow
    glow = Image.new("RGBA", (out, out), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((0, 0, out - 1, out - 1), fill=(*ring, 50))
    canvas_a.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
    draw = ImageDraw.Draw(canvas_a)
    draw.ellipse((2, 2, out - 3, out - 3), outline=(*ring, 230), width=3)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    cut = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cut.paste(avatar, (0, 0), mask)
    canvas_a.paste(cut, (5, 5), cut)
    if online:
        r = 14
        cx, cy = out - 18, out - 18
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*BG, 255))
        draw.ellipse((cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3), fill=(*GREEN, 255))
    return canvas_a


def load_logo(path, size: int) -> Image.Image:
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        img = Image.new("RGBA", (size, size), (*GOLD_DIM, 255))
        return img
    logo = Image.open(p).convert("RGBA")
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    logo.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas_l = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas_l.paste(
        logo,
        ((size - logo.width) // 2, (size - logo.height) // 2),
        logo,
    )
    return canvas_l
