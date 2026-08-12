#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regenerar.py — vuelve a generar el arte embebido en carmensay.py.

Sirve para cambiar la foto, el recorte o los parametros de conversion.

    pip install pillow numpy
    python3 regenerar.py foto.png --crop 545 60 880 560

El script reescribe carmen_gloria.blob en la misma carpeta.
"""
import argparse
import base64
import json
import os
import zlib

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

RAMP = "@%#*+=-:. "   # oscuro -> claro (tinta sobre papel: modo monocromo)
RAMP_INV = " .:-=+*#%@"  # claro -> denso (modo ansi, para terminal de fondo oscuro)
CHAR_AR = 0.46        # relacion alto/ancho de una celda de terminal


def load(src, box=None, sharpen=True):
    """Devuelve (rgb, alpha). Lo transparente se compone sobre blanco."""
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
    """Convierte la imagen en una lista de lineas de texto (con ANSI si color=True)."""
    w, h = rgb.size
    rows = max(1, int(round(cols * (h / w) * CHAR_AR)))
    small = rgb.resize((cols, rows), Image.LANCZOS)
    amask = np.asarray(alpha.resize((cols, rows), Image.LANCZOS))

    g = ImageEnhance.Contrast(small.convert("L")).enhance(contrast)
    g = ImageOps.autocontrast(g, cutoff=2)
    lum = np.power(np.asarray(g).astype(float) / 255.0, gamma)

    px = np.asarray(small).astype(float)
    if boost != 1.0:  # levanta los medios tonos para que el color se vea en terminal
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
    p = argparse.ArgumentParser(description="Regenera el arte de carmensay.py")
    p.add_argument("imagen", help="PNG de origen (idealmente con fondo transparente)")
    p.add_argument("--crop", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                   default=[545, 60, 880, 560], help="recorte; usa --no-crop para omitir")
    p.add_argument("--no-crop", action="store_true")
    p.add_argument("--big", type=int, default=76, help="columnas del retrato detallado")
    p.add_argument("--small", type=int, default=40, help="columnas del retrato compacto")
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
        print("%-6s %d columnas x %d filas" % (name, cols, len(art[name]["mono"])))

    blob = base64.b64encode(
        zlib.compress(json.dumps(art, separators=(",", ":")).encode(), 9)
    ).decode()

    open(a.target, "w", encoding="ascii").write(blob)
    print("arte actualizado en", a.target)


if __name__ == "__main__":
    main()
