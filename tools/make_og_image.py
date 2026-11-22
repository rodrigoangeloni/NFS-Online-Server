#!/usr/bin/env python3
"""Render the NFS Online social preview image (1200x630).

The image is an artifact: it lives outside the repository, in
``NFS-Online-Artifacts/downloads/og-image.jpg``, and the web serves it from
``/og-image.jpg``. The generator uses the same palette and Bahnschrift family
as the landing page.

Requires Pillow on the operator's Windows machine (the web container does not
need it; it only serves the generated JPEG).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent / "NFS-Online-Artifacts"
DEFAULT_OUTPUT = ARTIFACTS / "downloads" / "og-image.jpg"
DEFAULT_PREVIEW = ARTIFACTS / "web" / "og-image-preview.png"

W, H = 1200, 630
MARGIN = 72
BG = (7, 9, 7)
INK = (241, 245, 233)
MUTED = (152, 161, 143)
ACID = (201, 245, 59)
HOT = (255, 59, 47)
CYAN = (98, 217, 255)

BAHNSCHRIFT = Path(r"C:\Windows\Fonts\bahnschrift.ttf")
CASCADIA_MONO = Path(r"C:\Windows\Fonts\CascadiaMono.ttf")
FALLBACK_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def load_font(size: int, variation: str = "Bold SemiCondensed") -> ImageFont.FreeTypeFont:
    if BAHNSCHRIFT.is_file():
        font = ImageFont.truetype(str(BAHNSCHRIFT), size)
        try:
            font.set_variation_by_name(variation)
        except (OSError, ValueError):
            pass
        return font
    if FALLBACK_BOLD.is_file():
        return ImageFont.truetype(str(FALLBACK_BOLD), size)
    raise SystemExit("Bahnschrift or Arial Bold is required to render the image")


def add_glow(
    base: Image.Image,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    alpha: int,
) -> Image.Image:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(*color, alpha),
    )
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.6))
    return Image.alpha_composite(base, layer)


def spaced_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    spacing: float,
) -> float:
    if not text:
        return 0.0
    return sum(draw.textlength(char, font=font) for char in text) + spacing * (len(text) - 1)


def draw_spaced(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    spacing: float,
) -> None:
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, anchor="ls")
        x += draw.textlength(char, font=font) + spacing


def render() -> Image.Image:
    img = Image.new("RGBA", (W, H), (*BG, 255))

    # Atmosphere: the same acid/hot/cyan glows as the landing page.
    img = add_glow(img, (120, 30), 380, ACID, 48)
    img = add_glow(img, (1080, 0), 320, HOT, 32)
    img = add_glow(img, (620, 700), 430, CYAN, 24)

    # Road perspective and speed streaks.
    road = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(road)
    rd.polygon(
        [(690, 390), (960, 390), (1380, H), (250, H)],
        fill=(9, 12, 9, 95),
    )
    for x in (-400, 50, 500, 950, 1400, 1850):
        rd.line((825, 390, x, H), fill=(*CYAN, 16), width=1)
    for y in (410, 445, 490, 545, 600, 630):
        rd.line((0, y, W, y), fill=(*INK, 8), width=1)
    rd.line((0, 390, W, 390), fill=(*ACID, 38), width=2)
    for index in range(14):
        y = 55 + index * 40
        rd.line((W, y, W - 320 - index * 18, y + 120), fill=(*ACID, 7), width=1)
    img = Image.alpha_composite(img, road)

    # Grid, like the page atmosphere.
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W, 60):
        gd.line((x, 0, x, H), fill=(*INK, 7), width=1)
    for y in range(0, H, 60):
        gd.line((0, y, W, y), fill=(*INK, 7), width=1)
    img = Image.alpha_composite(img, grid)

    # Keep the left column dark for legibility.
    mask = Image.new("L", (W, 1))
    for x in range(W):
        if x <= 560:
            value = 240
        elif x >= 820:
            value = 0
        else:
            value = int(240 * (820 - x) / 260)
        mask.putpixel((x, 0), value)
    mask = mask.resize((W, H))
    shade = Image.new("RGBA", (W, H), (*BG, 255))
    shade.putalpha(mask)
    img = Image.alpha_composite(img, shade)

    # A soft halo makes the gauge pop without lighting the left column.
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse((760, 80, 1260, 580), fill=(*ACID, 30))
    halo = halo.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img, halo)

    # Speedometer, cropped by the right edge.
    gauge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(gauge)
    cx, cy, radius = 1010, 330, 225
    g.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(10, 13, 10, 210),
        outline=(*ACID, 55),
        width=2,
    )
    bbox = (cx - radius + 18, cy - radius + 18, cx + radius - 18, cy + radius - 18)
    g.arc(bbox, 135, 300, fill=(*ACID, 220), width=10)
    g.arc(bbox, 300, 360, fill=(*HOT, 220), width=10)
    g.arc(bbox, 0, 45, fill=(*HOT, 220), width=10)
    for angle in range(135, 406, 15):
        radians = math.radians(angle)
        inner = radius - 68 if (angle - 135) % 45 == 0 else radius - 50
        outer = radius - 28
        g.line(
            (
                cx + math.cos(radians) * inner,
                cy + math.sin(radians) * inner,
                cx + math.cos(radians) * outer,
                cy + math.sin(radians) * outer,
            ),
            fill=(*INK, 110),
            width=2,
        )
    radians = math.radians(330)
    g.line(
        (
            cx,
            cy,
            cx + math.cos(radians) * (radius - 85),
            cy + math.sin(radians) * (radius - 85),
        ),
        fill=(*HOT, 240),
        width=7,
    )
    g.ellipse(
        (cx - 66, cy - 66, cx + 66, cy + 66),
        fill=(10, 13, 10, 250),
        outline=(*ACID, 35),
        width=1,
    )
    g.text(
        (cx, cy - 8),
        "NFS",
        font=load_font(40),
        fill=(*ACID, 255),
        anchor="mm",
    )
    g.text(
        (cx, cy + 34),
        "ONLINE",
        font=load_font(14),
        fill=(*MUTED, 255),
        anchor="mm",
    )
    img = Image.alpha_composite(img, gauge)

    # Typography.
    draw = ImageDraw.Draw(img)
    draw_spaced(
        draw,
        (MARGIN, 80),
        "SERVIDOR COMUNITARIO · TEMPORADA 01",
        load_font(18),
        (*ACID, 255),
        3.2,
    )

    draw.rounded_rectangle(
        (MARGIN, 98, MARGIN + 88, 154),
        radius=2,
        fill=(*ACID, 255),
    )
    draw.text(
        (MARGIN + 44, 126),
        "NFS",
        font=load_font(34),
        fill=(*BG, 255),
        anchor="mm",
    )
    draw.text(
        (MARGIN + 102, 152),
        "ONLINE",
        font=load_font(54),
        fill=(*INK, 255),
        anchor="ls",
    )

    headline = load_font(64)
    draw.text((MARGIN, 252), "UNDERGROUND", font=headline, fill=(*INK, 255), anchor="ls")
    x = MARGIN + draw.textlength("UNDERGROUND", font=headline) + 10
    draw.text((x, 252), "2", font=headline, fill=(*ACID, 255), anchor="ls")
    draw.text(
        (MARGIN, 324),
        "+",
        font=load_font(52),
        fill=(*ACID, 255),
        anchor="ls",
    )
    draw.text(
        (MARGIN + 44, 324),
        "MOST WANTED",
        font=headline,
        fill=(*INK, 255),
        anchor="ls",
    )

    subline = load_font(20, "SemiBold SemiCondensed")
    draw_spaced(
        draw,
        (MARGIN, 398),
        "CREÁ TU CUENTA · DESCARGÁ EL PACK",
        subline,
        (*INK, 215),
        1.4,
    )
    draw_spaced(
        draw,
        (MARGIN, 426),
        "ENTRÁ A LA SALA Y JUGÁ ONLINE CON AMIGOS",
        subline,
        (*INK, 215),
        1.4,
    )

    draw.line((MARGIN, 500, 620, 500), fill=(*ACID, 110), width=2)
    draw.rectangle((620, 496, 628, 504), fill=(*ACID, 220))

    if CASCADIA_MONO.is_file():
        domain_font = ImageFont.truetype(str(CASCADIA_MONO), 30)
    else:
        domain_font = load_font(30)
    draw.text(
        (MARGIN, 558),
        "nfs-fps.duckdns.org",
        font=domain_font,
        fill=(*ACID, 255),
        anchor="ls",
    )

    chip = (430, 532, 608, 564)
    draw.rounded_rectangle(chip, radius=2, fill=(*ACID, 255))
    draw.ellipse((442, 542, 450, 550), fill=(*BG, 255))
    chip_font = load_font(14)
    chip_text = "REGISTRO ABIERTO"
    chip_width = spaced_width(draw, chip_text, chip_font, 1.2)
    draw_spaced(
        draw,
        (chip[0] + (chip[2] - chip[0] - chip_width) / 2 + 6, 552),
        chip_text,
        chip_font,
        (*BG, 255),
        1.2,
    )

    # Grain and vignette.
    noise = Image.effect_noise((W, H), 22).convert("L")
    noise_layer = Image.new("RGBA", (W, H), (*INK, 0))
    noise_layer.putalpha(noise.point(lambda value: int(value * 0.05)))
    img = Image.alpha_composite(img, noise_layer)

    vignette = Image.radial_gradient("L").resize((W, H))
    vignette = vignette.point(lambda value: int(value * 0.28))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(vignette)
    img = Image.alpha_composite(img, shade)

    draw = ImageDraw.Draw(img)
    draw.line((0, 0, W, 0), fill=(*ACID, 50), width=1)
    draw.line((0, H - 1, W, H - 1), fill=(*ACID, 35), width=1)
    return img


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preview", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args()

    image = render()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(
        args.output,
        "JPEG",
        quality=86,
        optimize=True,
        progressive=True,
    )
    print(f"{args.output}  {args.output.stat().st_size} bytes")
    if not args.no_preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(args.preview, "PNG", optimize=True)
        print(f"{args.preview}  {args.preview.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
