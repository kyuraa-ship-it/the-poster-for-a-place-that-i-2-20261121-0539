#!/usr/bin/env python3
"""AURELIA — The Floating Isles.

A vintage travel poster for a place that does not exist: a chain of islands
that float above a sea of clouds, their waterfalls pouring down into the sky.

Draws everything procedurally with Pillow (no network, no downloaded assets
at runtime). The bundled DejaVu Serif Bold font lives in assets/ so the
sandbox render matches the local one exactly.

Writes one 1024x1024 PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

W = 1024
S = 2  # supersample factor; everything is drawn at 2048 and downscaled
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
OUT_PATH = os.path.join(OUT_DIR, "entry.png")

# --- palette (limited, vintage travel-poster) -------------------------------
NAVY = (16, 32, 58)        # name band / deep shadow
INDIGO = (27, 42, 82)      # sky top
STEEL = (46, 90, 136)      # sky mid
PEACH = (242, 166, 90)     # horizon glow
GOLD = (245, 184, 29)      # sun
SUN_CORE = (252, 214, 92)
CREAM = (247, 238, 221)    # clouds / lettering
CLOUD_SHADE = (238, 220, 196)
TEAL_DARK = (23, 77, 66)   # island grass, far
TEAL = (31, 92, 77)        # island grass
CLIFF = (178, 101, 47)     # island rock, warm amber
CLIFF_DARK = (138, 72, 34)
WATER = (214, 233, 228)    # waterfall
RED = (192, 57, 43)        # balloon / tower roof
WHITE = (250, 246, 236)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sc(v):
    """Scale a 1024-space coordinate to the supersampled canvas."""
    return v * S


def pts(points):
    return [(sc(x), sc(y)) for x, y in points]


def vertical_gradient(img, top_color, mid_color, bottom_color, y0=0, y1=W):
    """Paint a smooth top -> mid -> bottom vertical gradient."""
    h = (y1 - y0) * S
    band = Image.new("RGB", (1, h))
    px = band.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        if t < 0.55:
            c = lerp(top_color, mid_color, t / 0.55)
        else:
            c = lerp(mid_color, bottom_color, (t - 0.55) / 0.45)
        px[0, y] = c
    band = band.resize((W * S, h))
    img.paste(band, (0, y0 * S))


def ellipse(draw, box, fill):
    draw.ellipse([sc(box[0]), sc(box[1]), sc(box[2]), sc(box[3])], fill=fill)


def cloud(draw, cx, cy, scale, base=CREAM, shade=CLOUD_SHADE):
    """One soft cloud: a row of overlapping ellipses with a shaded base."""
    puffs = [(-1.6, 0.10, 1.05), (-0.8, -0.25, 1.25), (0.0, -0.35, 1.45),
             (0.8, -0.20, 1.20), (1.6, 0.10, 0.95)]
    for dx, dy, r in puffs:
        ellipse(draw, (cx + dx * 46 * scale, cy + dy * 30 * scale - 14 * scale,
                       cx + dx * 46 * scale + 92 * scale * r,
                       cy + dy * 30 * scale + 56 * scale * r), base)
    # shaded underside, kept low and subtle so it reads as shadow, not a shape
    ellipse(draw, (cx - 130 * scale, cy + 26 * scale,
                   cx + 130 * scale, cy + 46 * scale), shade)
    # cover the shade's hard top edge with base puffs again, lower
    for dx, dy, r in puffs:
        ellipse(draw, (cx + dx * 46 * scale, cy + dy * 30 * scale - 6 * scale,
                       cx + dx * 46 * scale + 92 * scale * r,
                       cy + dy * 30 * scale + 40 * scale * r), base)


def island(draw, x0, x1, top_y, point_y, dome=16, grass=TEAL, cliff=CLIFF,
           cliff_dark=CLIFF_DARK, cap=22):
    """A floating island: domed grassy cap, tapering rock underside."""
    n = 24
    top = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = top_y - dome * math.sin(math.pi * t)
        top.append((x, y))
    mid_x = (x0 + x1) / 2
    # rock body: top arc -> right side -> bottom point -> left side
    body = top + [(x1, top_y + 6),
                  (mid_x + (x1 - mid_x) * 0.45, point_y - (point_y - top_y) * 0.45),
                  (mid_x, point_y),
                  (mid_x - (mid_x - x0) * 0.45, point_y - (point_y - top_y) * 0.45),
                  (x0, top_y + 6)]
    draw.polygon(pts(body), fill=cliff)
    # shadow on the right half of the rock
    shadow = [(mid_x, top_y + 2), (x1, top_y + 6),
              (mid_x + (x1 - mid_x) * 0.45, point_y - (point_y - top_y) * 0.45),
              (mid_x, point_y)]
    draw.polygon(pts(shadow), fill=cliff_dark)
    # grass cap: thin band following the dome
    cap_poly = top + [(x1, top[-1][1] + cap), (x0, top[0][1] + cap)]
    draw.polygon(pts(cap_poly), fill=grass)
    return mid_x, top_y


def pine(draw, x, y, h, color=TEAL_DARK):
    """A tiny pine tree standing on an island cap."""
    w = h * 0.42
    draw.polygon(pts([(x - w, y), (x + w, y), (x, y - h)]), fill=color)
    draw.polygon(pts([(x - w * 0.7, y - h * 0.45), (x + w * 0.7, y - h * 0.45),
                      (x, y - h * 1.25)]), fill=color)
    draw.rectangle([sc(x - 2), sc(y), sc(x + 2), sc(y + 8)], fill=CLIFF_DARK)


def tower(draw, x, y, h):
    """A slender white lighthouse tower with a red cap and a lit lamp."""
    w = h * 0.16
    draw.polygon(pts([(x - w, y), (x + w, y), (x + w * 0.7, y - h),
                      (x - w * 0.7, y - h)]), fill=WHITE)
    draw.rectangle([sc(x - w * 1.1), sc(y - h - 10), sc(x + w * 1.1),
                    sc(y - h)], fill=NAVY)
    draw.polygon(pts([(x - w * 1.3, y - h - 10), (x + w * 1.3, y - h - 10),
                      (x, y - h - 26)]), fill=RED)
    ellipse(draw, (x - 5, y - h - 8, x + 5, y - h + 2), GOLD)


def waterfall(draw, x, y_top, y_bot, width):
    """A waterfall pouring off an island edge into the clouds."""
    draw.polygon(pts([(x - width, y_top), (x + width, y_top),
                      (x + width * 0.55, y_bot), (x - width * 0.55, y_bot)]),
                 fill=WATER)
    for i, f in enumerate((-0.45, 0.0, 0.45)):
        draw.line(pts([(x + f * width, y_top + 4),
                       (x + f * width * 0.6, y_bot - 6)]),
                  fill=WHITE, width=2 * S)


def bird(draw, x, y, size, color=NAVY):
    draw.arc([sc(x - size), sc(y - size // 2), sc(x), sc(y + size // 2)],
             200, 340, fill=color, width=2 * S)
    draw.arc([sc(x), sc(y - size // 2), sc(x + size), sc(y + size // 2)],
             200, 340, fill=color, width=2 * S)


def main():
    img = Image.new("RGB", (W * S, W * S), INDIGO)
    draw = ImageDraw.Draw(img, "RGBA")

    # --- sky ----------------------------------------------------------------
    vertical_gradient(img, INDIGO, STEEL, PEACH, 0, 880)

    # stars in the upper sky
    rng = random.Random(20261121)
    for _ in range(70):
        x = rng.uniform(20, 1000)
        y = rng.uniform(20, 300)
        r = rng.uniform(1.2, 3.0)
        a = rng.randint(90, 200)
        ellipse(draw, (x - r, y - r, x + r, y + r), (255, 244, 214))
    # a few brighter four-point stars
    for (x, y, r) in [(150, 90, 7), (880, 70, 6), (520, 55, 5), (320, 170, 5)]:
        draw.polygon(pts([(x, y - r), (x + 1.6, y - 1.6), (x + r, y),
                          (x + 1.6, y + 1.6), (x, y + r), (x - 1.6, y + 1.6),
                          (x - r, y), (x - 1.6, y - 1.6)]), fill=(255, 244, 214))

    # --- sun with halo -------------------------------------------------------
    sun_cx, sun_cy, sun_r = 690, 330, 150
    # smooth halo: many faint concentric discs, no visible banding
    halo = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    steps = 12
    for i in range(steps, 0, -1):
        r = sun_r + (275 - sun_r) * i / steps
        a = int(8 + 62 * (1 - i / steps))
        hd.ellipse([sc(sun_cx - r), sc(sun_cy - r),
                    sc(sun_cx + r), sc(sun_cy + r)], fill=GOLD + (a,))
    img = Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    ellipse(draw, (sun_cx - sun_r, sun_cy - sun_r,
                   sun_cx + sun_r, sun_cy + sun_r), SUN_CORE)
    ellipse(draw, (sun_cx - sun_r + 14, sun_cy - sun_r + 14,
                   sun_cx + sun_r - 14, sun_cy + sun_r - 14), GOLD)

    # --- distant small island, high in the empty upper-left sky ---------------
    island(draw, 170, 300, 300, 400, dome=8, grass=TEAL_DARK,
           cliff=CLIFF_DARK, cliff_dark=(110, 55, 26), cap=12)
    pine(draw, 225, 293, 22)

    # --- red balloon drifting past the sun -----------------------------------
    bx, by = 830, 165
    ellipse(draw, (bx - 46, by - 52, bx + 46, by + 52), RED)
    draw.arc([sc(bx - 46), sc(by - 52), sc(bx + 46), sc(by + 52)],
             250, 290, fill=(140, 30, 22), width=3 * S)
    draw.arc([sc(bx - 46), sc(by - 52), sc(bx + 46), sc(by + 52)],
             70, 110, fill=(140, 30, 22), width=3 * S)
    draw.line(pts([(bx - 18, by + 50), (bx - 10, by + 78),
                   (bx + 10, by + 78), (bx + 18, by + 50)]), fill=NAVY, width=2 * S)
    draw.rectangle([sc(bx - 12), sc(by + 78), sc(bx + 12), sc(by + 96)],
                   fill=NAVY)

    # birds
    bird(draw, 250, 210, 16)
    bird(draw, 300, 240, 12)
    bird(draw, 180, 260, 11)
    bird(draw, 760, 250, 13)

    # --- main island (left), with the lighthouse -----------------------------
    island(draw, 90, 510, 470, 730, dome=20, cap=24)
    pine(draw, 170, 452, 34)
    pine(draw, 215, 448, 42)
    pine(draw, 255, 452, 28)
    tower(draw, 380, 446, 78)
    pine(draw, 440, 452, 30)
    waterfall(draw, 500, 480, 800, 16)

    # --- second island (right), smaller, with a cottage ----------------------
    island(draw, 620, 950, 545, 790, dome=14, cap=20)
    pine(draw, 700, 532, 30)
    pine(draw, 745, 530, 36)
    # tiny cottage: white walls, red roof
    draw.rectangle([sc(800), sc(505), sc(860), sc(538)], fill=WHITE)
    draw.polygon(pts([(792, 506), (868, 506), (830, 478)]), fill=RED)
    draw.rectangle([sc(824), sc(520), sc(836), sc(538)], fill=NAVY)
    waterfall(draw, 640, 556, 800, 12)

    # --- sea of clouds ---------------------------------------------------------
    for (cx, cy, s) in [(120, 800, 1.5), (330, 830, 1.8), (560, 805, 1.6),
                        (780, 835, 1.9), (950, 800, 1.4), (60, 860, 1.3),
                        (900, 865, 1.3)]:
        cloud(draw, cx, cy, s)
    # fill the very bottom of the scene with cloud so no sky shows through
    draw.rectangle([0, sc(872), sc(W), sc(880)], fill=CREAM)

    # --- name band -------------------------------------------------------------
    draw.rectangle([0, sc(880), sc(W), sc(W)], fill=NAVY)
    draw.rectangle([0, sc(880), sc(W), sc(886)], fill=GOLD)
    draw.rectangle([0, sc(1004), sc(W), sc(1010)], fill=GOLD)

    # place name, letterspaced, centred — the only copy on the poster
    here = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(here, "assets", "DejaVuSerif-Bold.ttf")
    name = "AURELIA"
    size = 200  # supersampled points; tuned below to fit
    font = ImageFont.truetype(font_path, size)
    tracking = 26
    while True:
        widths = [font.getlength(ch) for ch in name]
        total = sum(widths) + tracking * (len(name) - 1)
        if total <= 860 * S or size <= 60:
            break
        size -= 6
        font = ImageFont.truetype(font_path, size)
    x = (W * S - total) / 2
    y = 880 * S + (144 * S - size) / 2 - size * 0.08
    for ch, w in zip(name, widths):
        draw.text((x, y), ch, font=font, fill=CREAM)
        x += w + tracking
    # small gold diamonds flanking the name
    for dx in (-1, 1):
        cx = W * S / 2 + dx * (total / 2 + 52 * S / 2)
        cy = 880 * S + 72 * S
        r = 7 * S
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                     fill=GOLD)

    # --- thin vintage frame ----------------------------------------------------
    draw.rectangle([sc(14), sc(14), sc(W - 14), sc(W - 14)],
                   outline=CREAM, width=3 * S)
    draw.rectangle([sc(24), sc(24), sc(W - 24), sc(W - 24)],
                   outline=GOLD, width=1 * S)

    # --- downscale, save -------------------------------------------------------
    img = img.resize((W, W), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    img.save(OUT_PATH, "PNG", optimize=True)
    print(f"wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)} bytes)")


if __name__ == "__main__":
    sys.exit(main())
