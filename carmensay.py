#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
carmensay — like cowsay, but with Carmen Gloria.

Usage:
    carmensay "Hello, good afternoon"
    echo "text from a pipe" | carmensay
    carmensay -b "big version"
    carmensay -t "thinking out loud"
    carmensay --plain            # portrait only, no bubble

Options:
    -T/--tiny    tiny portrait (20 col)
    -b/--big     big portrait (40 col)
    -c/--color   truecolor with block chars (photo-like)
    -a/--ansi    truecolor with ASCII chars
    -n/--no-color  monochrome (classic ASCII)
    -t/--think   thought bubble
    -W N         text width (default 40)
    --plain      print portrait only

Without color flags, it auto-detects: color if output is a compatible
terminal, monochrome if redirected to a file or pipe.
"""
import argparse
import base64
import json
import os
import shutil
import sys
import textwrap
import zlib

__version__ = "1.0"

# Art generated from carmen_gloria_transparent.png (zlib+base64)
def _blob_path():
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "carmen_gloria.blob")

_cache = {}


def art(size, mode):
    """mode: 'mono' | 'block' | 'ansi'"""
    if not _cache:
        with open(_blob_path(), encoding="ascii") as f:
            blob = f.read()
        _cache.update(json.loads(zlib.decompress(base64.b64decode(blob))))
    return _cache[size][mode]


# ----------------------------------------------------------------- bubble


def bubble(text, width=40, think=False):
    """Return the lines of a cowsay-style speech/thought bubble."""
    paras = text.expandtabs().split("\n")
    lines = []
    for p in paras:
        wrapped = textwrap.wrap(p, width) if p.strip() else [""]
        lines.extend(wrapped)
    if not lines:
        lines = [""]
    w = max(len(l) for l in lines)

    out = [" " + "_" * (w + 2)]
    if think:
        for l in lines:
            out.append("( {} )".format(l.ljust(w)))
    elif len(lines) == 1:
        out.append("< {} >".format(lines[0].ljust(w)))
    else:
        for i, l in enumerate(lines):
            if i == 0:
                a, b = "/", "\\"
            elif i == len(lines) - 1:
                a, b = "\\", "/"
            else:
                a, b = "|", "|"
            out.append("{} {} {}".format(a, l.ljust(w), b))
    out.append(" " + "-" * (w + 2))
    return out


def tail(think, indent):
    pad = " " * indent
    if think:
        return [pad + "   o", pad + "    o"]
    return [pad + "   \\", pad + "    \\"]


# ----------------------------------------------------------------- output


def pick_mode(flag):
    if flag:
        return flag
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return "mono"
    if os.environ.get("TERM", "") in ("", "dumb"):
        return "mono"
    return "block"


def pick_size(flag):
    if flag:
        return flag
    cols = shutil.get_terminal_size((80, 24)).columns
    if cols < 50:
        return "tiny"
    return "big"


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="carmensay",
        description="Like cowsay, but with Carmen Gloria.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("text", nargs="*", help="text to speak (reads stdin if omitted)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("-T", "--tiny", action="store_const", const="tiny", dest="size")
    g.add_argument("-b", "--big", action="store_const", const="big", dest="size")
    c = p.add_mutually_exclusive_group()
    c.add_argument("-c", "--color", action="store_const", const="block", dest="mode",
                   help="truecolor with block chars (photo-like)")
    c.add_argument("-a", "--ansi", action="store_const", const="ansi", dest="mode",
                   help="truecolor with ASCII chars")
    c.add_argument("-n", "--no-color", action="store_const", const="mono", dest="mode",
                   help="monochrome, classic ASCII")
    p.add_argument("-t", "--think", action="store_true", help="thought bubble")
    p.add_argument("-W", "--width", type=int, default=40, help="text width")
    p.add_argument("--plain", action="store_true", help="portrait only")
    p.add_argument("--version", action="version", version="carmensay " + __version__)
    a = p.parse_args(argv)

    size = pick_size(a.size)
    portrait = art(size, pick_mode(a.mode))

    if a.plain:
        print("\n".join(portrait))
        return 0

    text = " ".join(a.text) if a.text else sys.stdin.read().rstrip("\n")
    if not text.strip():
        text = "..."

    indent = 2 if size == "tiny" else 4
    pad = " " * indent
    for l in bubble(text, a.width, a.think):
        print(pad + l)
    print("\n".join(tail(a.think, indent)))
    print("\n".join(portrait))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BrokenPipeError, KeyboardInterrupt):
        pass
