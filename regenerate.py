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

RAMP = "@%#*+=-:. "      # dark -> light (ink on paper: monochrome mode)
RAMP_INV = " .:-=+*#%@"  # light -> dense (ansi mode, for dark terminals)
CHAR_AR = 0.46           # terminal cell aspect ratio (height/width)

RESAMPLE_FILTERS = {
    "lanczos": Image.LANCZOS,
    "bilinear": Image.BILINEAR,
    "box": Image.BOX,
}

SIZE_CONTRAST = {"big": 1.65, "medium": 1.85, "small": 2.0}

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


def main():
    """Main Resolves the Args and art Target, Renders every portrait Size, and Writes the Blob."""
    args = parse_regenerate_args()
    resample = RESAMPLE_FILTERS[args.resample]
    target, char_dir = resolve_art_target(args)
    os.makedirs(char_dir, exist_ok=True)
    ensure_gitignore(char_dir)

    rgb, alpha = load_character_photo(args.imagen, None if args.no_crop else args.crop)
    art = render_character_sizes(rgb, alpha, args, resample)

    write_art_blob(art, target)


def parse_regenerate_args():
    """ParseRegenerateArgs Builds the Cli parser, then Returns the parsed Args."""
    parser = argparse.ArgumentParser(
        description="Regenerate a whosay character's art",
        epilog="example:\n"
               "  python3 regenerate.py photo.png --character carmen_gloria "
               "--crop 545 60 880 560\n"
               "  python3 regenerate.py photo.png --character ozzy --no-crop "
               "--resample bilinear",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("imagen", help="source PNG (ideally with transparent background)")
    parser.add_argument("--character", default="carmen_gloria",
                         help="character folder under characters/ (default carmen_gloria)")
    parser.add_argument("--crop", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                         default=[545, 60, 880, 560], help="crop region; use --no-crop to skip")
    parser.add_argument("--no-crop", action="store_true",
                         help="use the full image instead of --crop")
    parser.add_argument("--big", type=int, default=60, help="columns for big portrait")
    parser.add_argument("--medium", type=int, default=40, help="columns for medium portrait")
    parser.add_argument("--small", type=int, default=20, help="columns for small portrait")
    parser.add_argument("--target", default=None,
                         help="override the blob path (default: characters/<character>/art.blob)")
    parser.add_argument("--resample", choices=("lanczos", "bilinear", "box"), default="lanczos",
                         help="resize filter (default lanczos; try bilinear/box if you see "
                              "false-background holes near hard edges like hairlines)")
    return parser.parse_args()


def resolve_art_target(args):
    """ResolveArtTarget Returns the Blob path and its parent character Directory."""
    target = args.target or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "characters", args.character, "art.blob")
    return target, os.path.dirname(target)


def ensure_gitignore(char_dir):
    """EnsureGitignore Writes the shared image-exclusion Rules into char_dir if missing."""
    path = os.path.join(char_dir, ".gitignore")
    if not os.path.exists(path):
        open(path, "w", encoding="utf-8").write(IMAGE_GITIGNORE)


def load_character_photo(src, crop_box=None, sharpen=True):
    """LoadCharacterPhoto Reads the source Image, composites transparency on White, and Returns (rgb, alpha)."""
    image = Image.open(src).convert("RGBA")
    if crop_box:
        image = image.crop(tuple(crop_box))
    alpha = image.getchannel("A")

    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    rgb = background.convert("RGB")
    if sharpen:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=110))

    return rgb, alpha


def render_character_sizes(rgb, alpha, args, resample):
    """RenderCharacterSizes Returns the big, medium and small portrait Art, and Reports their row Counts."""
    cols_by_size = {"big": args.big, "medium": args.medium, "small": args.small}

    art = {}
    for name, contrast in SIZE_CONTRAST.items():
        cols = cols_by_size[name]
        art[name] = render_size_variants(rgb, alpha, cols, contrast, resample)
        print("%-6s %d cols x %d rows" % (name, cols, len(art[name]["mono"])))
    return art


def render_size_variants(rgb, alpha, cols, contrast, resample):
    """RenderSizeVariants Returns the mono, block and Ansi Renderings for one portrait Size."""
    return {
        "mono": render_ascii_art(rgb, alpha, cols, RAMP, contrast, resample=resample),
        "block": render_ascii_art(rgb, alpha, cols, "█" * 6, 1.0, color=True, resample=resample),
        "ansi": render_ascii_art(rgb, alpha, cols, RAMP_INV, 1.5, color=True, boost=0.42, resample=resample),
    }


def render_ascii_art(rgb, alpha, cols, ramp=RAMP, contrast=1.65, gamma=1.0,
                      color=False, amin=150, white=246, boost=1.0, resample=Image.LANCZOS):
    """RenderAsciiArt Resizes the Photo to a character Grid, then Returns its ramp-mapped ascii Lines.

    resample defaults to Lanczos, which is sharpest but can ring near
    hard edges (e.g. hair against skin) and overshoot past the white
    cutoff, punching false background-colored holes in the subject. Pass
    Bilinear/Box for photos where that shows up.
    """
    amask, lum, px = resize_photo_grid(rgb, alpha, cols, contrast, gamma, boost, resample)

    n = len(ramp) - 1
    lines = [
        render_ascii_row(px[y], amask[y], lum[y], ramp, n, color, amin, white)
        for y in range(px.shape[0])
    ]
    return trim_blank_edges(lines)


def resize_photo_grid(rgb, alpha, cols, contrast, gamma, boost, resample):
    """ResizePhotoGrid Shrinks the Photo to `cols` wide, then Returns its alpha, luminance and pixel Grids."""
    width, height = rgb.size
    rows = max(1, int(round(cols * (height / width) * CHAR_AR)))
    small = rgb.resize((cols, rows), resample)
    amask = np.asarray(alpha.resize((cols, rows), resample))

    gray = ImageEnhance.Contrast(small.convert("L")).enhance(contrast)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    lum = np.power(np.asarray(gray).astype(float) / 255.0, gamma)

    px = np.asarray(small).astype(float)
    if boost != 1.0:  # boost midtones so colors show better in the terminal
        px = 255.0 * np.power(px / 255.0, boost)
    px = np.clip(px, 0, 255).astype(int)

    return amask, lum, px


def render_ascii_row(row_px, row_amask, row_lum, ramp, n, color, amin, white):
    """RenderAsciiRow Maps one pixel Row to ramp Characters, adding Ansi color codes when asked."""
    row, prev = [], None
    for x in range(len(row_px)):
        r, g, b = row_px[x]
        if row_amask[x] < amin or (r > white and g > white and b > white):
            if color and prev is not None:
                row.append("\x1b[0m")
                prev = None
            row.append(" ")
            continue
        ch = ramp[min(n, int(row_lum[x] * n))]
        if ch == " ":
            ch = "."
        if not color:
            row.append(ch)
            continue
        key = (r // 24, g // 24, b // 24)
        if key != prev:
            row.append("\x1b[38;2;%d;%d;%dm" % (r, g, b))
            prev = key
        row.append(ch)
    line = "".join(row).rstrip()
    return line + "\x1b[0m" if color and prev is not None else line


def trim_blank_edges(lines):
    """TrimBlankEdges Drops leading and trailing Lines that render blank once Ansi codes are stripped."""
    while lines and not lines[0].replace("\x1b[0m", "").strip():
        lines.pop(0)
    while lines and not lines[-1].replace("\x1b[0m", "").strip():
        lines.pop()
    return lines


def write_art_blob(art, target):
    """WriteArtBlob Compresses the Art dict into base64, then Writes it to the target Path."""
    payload = json.dumps(art, separators=(",", ":")).encode()
    blob = base64.b64encode(zlib.compress(payload, 9)).decode()

    open(target, "w", encoding="ascii").write(blob)
    print("art updated in", target)


if __name__ == "__main__":
    main()
