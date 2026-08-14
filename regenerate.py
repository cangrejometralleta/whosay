#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regenerate.py — regenerates a whosay character's art.

Use this to change a character's photo, crop, or conversion parameters, or
to add a brand-new character.

    pip install pillow numpy
    python3 regenerate.py photo.png --character carmen_gloria --crop 545 60 880 560

The script writes characters/<character>/art.blob. For a new character, also
create characters/<character>/character.json with display_name, nationality,
topic, language, persona, joke_prompt and (optionally) a fallback line — see
characters/carmen_gloria/ for an example.
"""
import argparse
import base64
import json
import os
import zlib

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

RAMP = "@%#*+=-:. "   # dark -> light (ink on paper: monochrome mode)
RAMP_INV = " .:-=+*#%@"  # light -> dense (ansi mode, for dark terminals)
CHAR_AR = 0.46        # terminal cell aspect ratio (height/width)

# Source/likeness photos shouldn't be redistributed through git — only
# art.blob (the converted ASCII derivative) and character.json are meant to
# be tracked. Every character folder gets its own copy of this so the rule
# travels with the folder even if the root .gitignore changes.
IMAGE_GITIGNORE = """\
# Source/likeness images stay local — only art.blob (the converted ASCII
# art) and character.json are meant to be redistributed through git.
*.png
*.jpg
*.jpeg
*.gif
*.bmp
*.webp
*.tiff
*.tif
*.heic
"""


def ensure_gitignore(char_dir):
    path = os.path.join(char_dir, ".gitignore")
    if not os.path.exists(path):
        open(path, "w", encoding="utf-8").write(IMAGE_GITIGNORE)


def load(src, box=None, sharpen=True):
    """Returns (rgb, alpha). Transparent areas are composited on white."""
    im = Image.open(src).convert("RGBA")
    if box:
        im = im.crop(tuple(box))
    alpha = im.getchannel("A")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    rgb = bg.convert("RGB")
    if sharpen:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=110))
    return rgb, alpha


def to_ascii(rgb, alpha, cols, ramp=RAMP, contrast=1.65, gamma=1.0,
             color=False, amin=150, white=246, boost=1.0, resample=Image.LANCZOS):
    """Convert the image to a list of text lines (with ANSI if color=True).

    resample defaults to LANCZOS, which is sharpest but can ring near
    hard edges (e.g. hair against skin) and overshoot past the white
    cutoff, punching false background-colored holes in the subject. Pass
    Image.BILINEAR/BOX for photos where that shows up.
    """
    w, h = rgb.size
    rows = max(1, int(round(cols * (h / w) * CHAR_AR)))
    small = rgb.resize((cols, rows), resample)
    amask = np.asarray(alpha.resize((cols, rows), resample))

    g = ImageEnhance.Contrast(small.convert("L")).enhance(contrast)
    g = ImageOps.autocontrast(g, cutoff=2)
    lum = np.power(np.asarray(g).astype(float) / 255.0, gamma)

    px = np.asarray(small).astype(float)
    if boost != 1.0:  # boost midtones so colors show better in the terminal
        px = 255.0 * np.power(px / 255.0, boost)
    px = np.clip(px, 0, 255).astype(int)

    n = len(ramp) - 1
    lines = []
    for y in range(rows):
        row, prev = [], None
        for x in range(cols):
            r, gg, b = px[y, x]
            if amask[y, x] < amin or (r > white and gg > white and b > white):
                if color and prev is not None:
                    row.append("\x1b[0m")
                    prev = None
                row.append(" ")
                continue
            ch = ramp[min(n, int(lum[y, x] * n))]
            if ch == " ":
                ch = "."
            if not color:
                row.append(ch)
                continue
            key = (r // 24, gg // 24, b // 24)
            if key != prev:
                row.append("\x1b[38;2;%d;%d;%dm" % (r, gg, b))
                prev = key
            row.append(ch)
        line = "".join(row).rstrip()
        lines.append(line + "\x1b[0m" if color and prev is not None else line)
    while lines and not lines[0].replace("\x1b[0m", "").strip():
        lines.pop(0)
    while lines and not lines[-1].replace("\x1b[0m", "").strip():
        lines.pop()
    return lines


def main():
    p = argparse.ArgumentParser(
        description="Regenerate a whosay character's art",
        epilog="example:\n"
               "  python3 regenerate.py photo.png --character carmen_gloria "
               "--crop 545 60 880 560\n"
               "  python3 regenerate.py photo.png --character ozzy --no-crop "
               "--resample bilinear",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("imagen", help="source PNG (ideally with transparent background)")
    p.add_argument("--character", default="carmen_gloria",
                   help="character folder under characters/ (default carmen_gloria)")
    p.add_argument("--crop", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                   default=[545, 60, 880, 560], help="crop region; use --no-crop to skip")
    p.add_argument("--no-crop", action="store_true",
                   help="use the full image instead of --crop")
    p.add_argument("--big", type=int, default=60, help="columns for big portrait")
    p.add_argument("--medium", type=int, default=40, help="columns for medium portrait")
    p.add_argument("--small", type=int, default=20, help="columns for small portrait")
    p.add_argument("--target", default=None,
                   help="override the blob path (default: characters/<character>/art.blob)")
    p.add_argument("--resample", choices=("lanczos", "bilinear", "box"), default="lanczos",
                   help="resize filter (default lanczos; try bilinear/box if you see "
                        "false-background holes near hard edges like hairlines)")
    a = p.parse_args()
    resample = {"lanczos": Image.LANCZOS, "bilinear": Image.BILINEAR, "box": Image.BOX}[a.resample]

    target = a.target or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "characters", a.character, "art.blob")
    char_dir = os.path.dirname(target)
    os.makedirs(char_dir, exist_ok=True)
    ensure_gitignore(char_dir)

    rgb, alpha = load(a.imagen, None if a.no_crop else a.crop)

    art = {}
    for name, cols, contrast in [("big", a.big, 1.65), ("medium", a.medium, 1.85), ("small", a.small, 2.0)]:
        art[name] = {
            "mono": to_ascii(rgb, alpha, cols, RAMP, contrast, resample=resample),
            "block": to_ascii(rgb, alpha, cols, "█" * 6, 1.0, color=True, resample=resample),
            "ansi": to_ascii(rgb, alpha, cols, RAMP_INV, 1.5, color=True, boost=0.42, resample=resample),
        }
        print("%-6s %d cols x %d rows" % (name, cols, len(art[name]["mono"])))

    blob = base64.b64encode(
        zlib.compress(json.dumps(art, separators=(",", ":")).encode(), 9)
    ).decode()

    open(target, "w", encoding="ascii").write(blob)
    print("art updated in", target)


if __name__ == "__main__":
    main()
