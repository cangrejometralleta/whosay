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


def main(argv=None):
    """Main Parses the Args,
       Resolves the Character and Portrait,
       then Prints the whosay Panel."""
    args = parse_whosay_args(argv)

    if args.list_characters:
        return print_character_roster()

    try:
        character = resolve_character_choice(args)
        size = pick_size(args.size)
        portrait = load_character_art(character, size, pick_mode(args.mode))
    except CharacterNotFound as e:
        print("whosay: {}".format(e), file=sys.stderr)
        return 1

    if args.plain:
        print("\n".join(portrait))
        return 0

    print_character_bubble(portrait, size, args)
    return 0


def parse_whosay_args(argv):
    """ParseWhosayArgs Builds the Cli parser,
       then Returns the parsed Args."""
    parser = argparse.ArgumentParser(
        prog="whosay",
        description="Like cowsay, but with a cast of characters.",
        epilog="example:\n"
               "  whosay -C ozzy 'bloody hell'\n"
               "  echo 'what a scorcher' | whosay -C carmen_gloria -a -b\n"
               "  whosay --random -t 'is this thing on?'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="*", help="text to speak (reads stdin if omitted)")
    chars = list_characters()
    parser.add_argument("-C", "--character", default=DEFAULT_CHARACTER, choices=chars or None,
                         help="which character to draw (default: {})".format(DEFAULT_CHARACTER))
    parser.add_argument("--list-characters", action="store_true",
                         help="list the available characters and exit")
    parser.add_argument("--random", action="store_true",
                         help="pick a random character")
    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument("-s", "--small", action="store_const", const="small", dest="size",
                             help="20-column portrait (default)")
    size_group.add_argument("-m", "--medium", action="store_const", const="medium", dest="size",
                             help="40-column portrait")
    size_group.add_argument("-b", "--big", action="store_const", const="big", dest="size",
                             help="60-column portrait")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-c", "--color", action="store_const", const="block", dest="mode",
                             help="truecolor with block chars (photo-like)")
    mode_group.add_argument("-a", "--ansi", action="store_const", const="ansi", dest="mode",
                             help="truecolor with ASCII chars")
    mode_group.add_argument("-n", "--no-color", action="store_const", const="mono", dest="mode",
                             help="monochrome, classic ASCII")
    parser.add_argument("-t", "--think", action="store_true", help="thought bubble")
    parser.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH, help="text width")
    parser.add_argument("--plain", action="store_true", help="portrait only")
    parser.add_argument("--version", action="version", version="whosay " + __version__)
    return parser.parse_args(argv)


def print_character_roster():
    """PrintCharacterRoster Lists every known Character,
       or Reports there are none."""
    chars = list_characters()
    if not chars:
        print("whosay: no characters found in characters/", file=sys.stderr)
        return 1
    print("\n".join(chars))
    return 0


def resolve_character_choice(args):
    """ResolveCharacterChoice Returns the requested Character,
       or a random one when args.random is set."""
    if not args.random:
        return args.character
    chars = list_characters()
    if not chars:
        raise CharacterNotFound("no characters found in characters/")
    character = random.choice(chars)
    print("whosay: character: {}".format(character), file=sys.stderr)
    return character


def pick_size(flag):
    """PickSize Returns flag if given,
       else the default portrait Size."""
    return flag or DEFAULT_SIZE


_art_cache = {}


def load_character_art(character, size, mode):
    """LoadCharacterArt Returns the cached ascii Frame for this character/size/mode,
       decoding the Blob once.

    mode: 'mono' | 'block' | 'ansi'
    """
    if character not in _art_cache:
        path = os.path.join(_resolve_characters_dir(), character, "art.blob")
        try:
            with open(path, encoding="ascii") as f:
                blob = f.read()
        except OSError:
            available = ", ".join(list_characters()) or "none found"
            raise CharacterNotFound(
                "unknown character '{}' (available: {})".format(character, available))
        _art_cache[character] = json.loads(zlib.decompress(base64.b64decode(blob)))
    return _art_cache[character][size][mode]


def pick_mode(flag):
    """PickMode Returns flag if given,
       else auto-detects mono/block from the terminal Environment."""
    if flag:
        return flag
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return "mono"
    if os.environ.get("TERM", "") in ("", "dumb"):
        return "mono"
    return "block"


def print_character_bubble(portrait, size, args):
    """PrintCharacterBubble Prints the speech Bubble for args.text (or stdin) above the character Portrait."""
    text = " ".join(args.text) if args.text else sys.stdin.read().rstrip("\n")
    if not text.strip():
        text = "..."

    indent = INDENT[size]
    pad = " " * indent
    for line in render_speech_bubble(text, args.width, args.think):
        print(pad + line)
    print("\n".join(render_bubble_tail(args.think, indent)))
    print("\n".join(portrait))


# ------------------------------------------------------------------ character


def list_characters():
    """ListCharacters Returns every character Name that has an art.blob, sorted."""
    base = _resolve_characters_dir()
    try:
        return sorted(
            name for name in os.listdir(base)
            if os.path.isfile(os.path.join(base, name, "art.blob"))
        )
    except OSError:
        return []


def _resolve_characters_dir():
    """ResolveCharactersDir Returns the characters/ Directory, inside the frozen Bundle or beside the script."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "characters")


# ----------------------------------------------------------------- bubble


def render_speech_bubble(text, width=DEFAULT_WIDTH, think=False):
    """RenderSpeechBubble Wraps text to width,
       then Returns the cowsay-style Lines of a speech/thought bubble."""
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


def render_bubble_tail(think, indent):
    """RenderBubbleTail Returns the two-line Tail connecting a speech or thought bubble to the Portrait."""
    pad = " " * indent
    if think:
        return [pad + "   o", pad + "    o"]
    return [pad + "   \\", pad + "    \\"]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BrokenPipeError, KeyboardInterrupt):
        pass
