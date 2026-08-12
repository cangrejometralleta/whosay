#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regenerar.py — regenerates the embedded art in carmensay.py.

Use this to change the photo, crop, or conversion parameters.

    pip install pillow numpy
    python3 regenerar.py photo.png --crop 545 60 880 560

The script rewrites carmen_gloria.blob in the same directory.
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
             color=False, amin=150, white=246, boost=1.0):
    """Convert the image to a list of text lines (with ANSI if color=True)."""
    w, h = rgb.size
    rows = max(1, int(round(cols * (h / w) * CHAR_AR)))
    small = rgb.resize((cols, rows), Image.LANCZOS)
    amask = np.asarray(alpha.resize((cols, rows), Image.LANCZOS))

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
    p = argparse.ArgumentParser(description="Regenerate carmensay.py art")
    p.add_argument("imagen", help="source PNG (ideally with transparent background)")
    p.add_argument("--crop", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                   default=[545, 60, 880, 560], help="crop region; use --no-crop to skip")
    p.add_argument("--no-crop", action="store_true")
    p.add_argument("--big", type=int, default=76, help="columns for detailed portrait")
    p.add_argument("--small", type=int, default=40, help="columns for compact portrait")
    p.add_argument("--target", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    "carmen_gloria.blob"))
    a = p.parse_args()

    rgb, alpha = load(a.imagen, None if a.no_crop else a.crop)

    art = {}
    for name, cols, contrast in [("big", a.big, 1.65), ("small", a.small, 1.85), ("tiny", 20, 2.0)]:
        art[name] = {
            "mono": to_ascii(rgb, alpha, cols, RAMP, contrast),
            "block": to_ascii(rgb, alpha, cols, "█" * 6, 1.0, color=True),
            "ansi": to_ascii(rgb, alpha, cols, RAMP_INV, 1.5, color=True, boost=0.42),
        }
        print("%-6s %d cols x %d rows" % (name, cols, len(art[name]["mono"])))

    blob = base64.b64encode(
        zlib.compress(json.dumps(art, separators=(",", ":")).encode(), 9)
    ).decode()

    open(a.target, "w", encoding="ascii").write(blob)
    print("art updated in", a.target)


if __name__ == "__main__":
    main()
