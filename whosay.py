#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whosay — like cowsay, but with a cast of characters (Carmen Gloria by default).

Usage:
    whosay "Hello, good afternoon"
    echo "text from a pipe" | whosay
    whosay -s "small version"
    whosay -t "thinking out loud"
    whosay -C some_character "hi"
    whosay --list-characters
    whosay --random "surprise me"
    whosay --plain            # portrait only, no bubble

Options:
    -C, --character NAME  which character to draw (default: carmen_gloria)
    --list-characters      list the available characters and exit
    --random               pick a random character
    -s/--small    small portrait (20 col, default)
    -m/--medium   medium portrait (40 col)
    -b/--big      big portrait (60 col)
    -c/--color   truecolor with block chars (photo-like)
    -a/--ansi    truecolor with ASCII chars
    -n/--no-color  monochrome (classic ASCII)
    -t/--think   thought bubble
    -W N         text width (default 40)
    --plain      print portrait only

Without color flags, it auto-detects: color if output is a compatible
terminal, monochrome if redirected to a file or pipe.

Characters live in characters/<name>/art.blob (see regenerate.py to add one).
"""
import argparse
import base64
import json
import os
import random
import sys
import textwrap
import zlib

__version__ = "1.0"

# ------------------------------------------------------------------ defaults
DEFAULT_CHARACTER = "carmen_gloria"
DEFAULT_SIZE = "small"  # 20 columns
DEFAULT_WIDTH = 40
INDENT = {"small": 1, "medium": 2, "big": 4}


class CharacterNotFound(Exception):
    pass


def _characters_dir():
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "characters")


def list_characters():
    base = _characters_dir()
    try:
        return sorted(
            name for name in os.listdir(base)
            if os.path.isfile(os.path.join(base, name, "art.blob"))
        )
    except OSError:
        return []


_art_cache = {}


def art(character, size, mode):
    """mode: 'mono' | 'block' | 'ansi'"""
    if character not in _art_cache:
        path = os.path.join(_characters_dir(), character, "art.blob")
        try:
            with open(path, encoding="ascii") as f:
                blob = f.read()
        except OSError:
            available = ", ".join(list_characters()) or "none found"
            raise CharacterNotFound(
                "unknown character '{}' (available: {})".format(character, available))
        _art_cache[character] = json.loads(zlib.decompress(base64.b64decode(blob)))
    return _art_cache[character][size][mode]


# ----------------------------------------------------------------- bubble


def bubble(text, width=DEFAULT_WIDTH, think=False):
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
    return flag or DEFAULT_SIZE


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="whosay",
        description="Like cowsay, but with a cast of characters.",
        epilog="example:\n"
               "  whosay -C ozzy 'bloody hell'\n"
               "  echo 'what a scorcher' | whosay -C carmen_gloria -a -b\n"
               "  whosay --random -t 'is this thing on?'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("text", nargs="*", help="text to speak (reads stdin if omitted)")
    chars = list_characters()
    p.add_argument("-C", "--character", default=DEFAULT_CHARACTER, choices=chars or None,
                   help="which character to draw (default: {})".format(DEFAULT_CHARACTER))
    p.add_argument("--list-characters", action="store_true",
                   help="list the available characters and exit")
    p.add_argument("--random", action="store_true",
                   help="pick a random character")
    g = p.add_mutually_exclusive_group()
    g.add_argument("-s", "--small", action="store_const", const="small", dest="size",
                   help="20-column portrait (default)")
    g.add_argument("-m", "--medium", action="store_const", const="medium", dest="size",
                   help="40-column portrait")
    g.add_argument("-b", "--big", action="store_const", const="big", dest="size",
                   help="60-column portrait")
    c = p.add_mutually_exclusive_group()
    c.add_argument("-c", "--color", action="store_const", const="block", dest="mode",
                   help="truecolor with block chars (photo-like)")
    c.add_argument("-a", "--ansi", action="store_const", const="ansi", dest="mode",
                   help="truecolor with ASCII chars")
    c.add_argument("-n", "--no-color", action="store_const", const="mono", dest="mode",
                   help="monochrome, classic ASCII")
    p.add_argument("-t", "--think", action="store_true", help="thought bubble")
    p.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH, help="text width")
    p.add_argument("--plain", action="store_true", help="portrait only")
    p.add_argument("--version", action="version", version="whosay " + __version__)
    a = p.parse_args(argv)

    if a.list_characters:
        chars = list_characters()
        if not chars:
            print("whosay: no characters found in characters/", file=sys.stderr)
            return 1
        print("\n".join(chars))
        return 0

    character = a.character
    if a.random:
        chars = list_characters()
        if not chars:
            print("whosay: no characters found in characters/", file=sys.stderr)
            return 1
        character = random.choice(chars)
        print("whosay: character: {}".format(character), file=sys.stderr)

    size = pick_size(a.size)
    try:
        portrait = art(character, size, pick_mode(a.mode))
    except CharacterNotFound as e:
        print("whosay: {}".format(e), file=sys.stderr)
        return 1

    if a.plain:
        print("\n".join(portrait))
        return 0

    text = " ".join(a.text) if a.text else sys.stdin.read().rstrip("\n")
    if not text.strip():
        text = "..."

    indent = INDENT[size]
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
