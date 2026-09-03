#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whocast — the cast, the portraits and the bubble, shared by whosay and whonews.

Neither script is the other's library: both import this one. It holds what
they would otherwise each keep a copy of — where characters live, how a
portrait is decoded, how a speech bubble is drawn, and the look flags
(-C/--random, -s/-m/-b, -c/-a/--no-color, -W) they both accept.

A character is a folder under characters/<name>/ (see regenerate.py to add
one):
    art.blob        the ASCII portrait, every size and every color mode
    character.json  display_name, persona, joke_prompt, fallback, signature

Nothing here prints an error or exits: a missing character raises
CharacterNotFound, and each script says it in its own voice.
"""
import base64
import json
import os
import random
import sys
import textwrap
import zlib

__version__ = "1.0"

# ------------------------------------------------------------------ defaults
DEFAULT_SIZE = "small"   # the narrowest of the three portraits in the blob
DEFAULT_WIDTH = 40       # text width inside the bubble
INDENT = {"small": 1, "medium": 2, "big": 4}  # how far the bubble sits from the left


class CharacterNotFound(Exception):
    pass


# ------------------------------------------------------------------ character


def list_characters():
    """ListCharacters Returns every character Name that has an art.blob, sorted."""
    base = resolve_characters_dir()
    try:
        return sorted(
            name for name in os.listdir(base)
            if os.path.isfile(os.path.join(base, name, "art.blob"))
        )
    except OSError:
        return []


def pick_character(name=None, force_random=False):
    """PickCharacter Returns the named Character,
       or a random one when nobody named it (or --random asked for one)."""
    if name and not force_random:
        return name
    chars = list_characters()
    if not chars:
        raise CharacterNotFound("no characters found in characters/")
    return random.choice(chars)


def load_character(name):
    """LoadCharacter Reads characters/<name>/character.json,
       then Returns it as a dict."""
    path = os.path.join(resolve_characters_dir(), name, "character.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        raise CharacterNotFound(describe_unknown_character(name))


_art_cache = {}


def load_character_art(character, size, mode):
    """LoadCharacterArt Returns the cached ascii Frame for this character/size/mode,
       decoding the Blob once.

    mode: 'mono' | 'block' | 'ansi'
    """
    if character not in _art_cache:
        _art_cache[character] = decode_character_art(character)
    return _art_cache[character][size][mode]


def decode_character_art(character):
    """DecodeCharacterArt Reads and Decodes one Character's portrait Bundle."""
    path = os.path.join(resolve_characters_dir(), character, "art.blob")
    try:
        with open(path, encoding="ascii") as stream:
            blob = stream.read()
    except OSError:
        raise CharacterNotFound(describe_unknown_character(character))

    return json.loads(zlib.decompress(base64.b64decode(blob)))


def describe_unknown_character(name):
    """DescribeUnknownCharacter Returns the "no such character" Message, with the ones there are."""
    available = ", ".join(list_characters()) or "none found"
    return "unknown character '{}' (available: {})".format(name, available)


def resolve_characters_dir():
    """ResolveCharactersDir Returns the characters/ Directory,
       inside the frozen Bundle or beside this file.

    realpath, not abspath: reached through a symlink in ~/.local/bin, the
    characters live next to the checkout, not next to the link.
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(base, "characters")


# ------------------------------------------------------------------ look


def pick_size(flag):
    """PickSize Returns flag if given,
       else the default portrait Size."""
    return flag or DEFAULT_SIZE


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


# ------------------------------------------------------------------ bubble


def print_character_panel(text, portrait, size, width=DEFAULT_WIDTH, think=False):
    """PrintCharacterPanel Prints one Panel: the speech Bubble, its Tail, then the Portrait."""
    indent = INDENT[size]
    for line in render_speech_bubble(text, width, think):
        print(" " * indent + line)
    print("\n".join(render_bubble_tail(think, indent)))
    print("\n".join(portrait))


def render_speech_bubble(text, width=DEFAULT_WIDTH, think=False):
    """RenderSpeechBubble Wraps text to width,
       then Returns the cowsay-style Lines of a speech/thought bubble."""
    lines = wrap_bubble_text(text, width)
    span = max(len(line) for line in lines)

    body = render_bubble_body(lines, span, think)
    return [" " + "_" * (span + 2), *body, " " + "-" * (span + 2)]


def wrap_bubble_text(text, width):
    """WrapBubbleText Wraps every Paragraph while Preserving empty Lines."""
    lines = []
    for paragraph in text.expandtabs().split("\n"):
        wrapped = textwrap.wrap(paragraph, width) if paragraph.strip() else [""]
        lines.extend(wrapped)

    return lines or [""]


def render_bubble_body(lines, span, think):
    """RenderBubbleBody Frames wrapped Lines as Speech or Thought."""
    if think:
        return ["( {} )".format(line.ljust(span)) for line in lines]
    if len(lines) == 1:
        return ["< {} >".format(lines[0].ljust(span))]

    return [frame_bubble_line(line, index, len(lines), span)
            for index, line in enumerate(lines)]


def frame_bubble_line(line, index, count, span):
    """FrameBubbleLine Chooses Borders for one Line in a multiline Bubble."""
    borders = ("/", "\\") if index == 0 else ("|", "|")
    if index == count - 1:
        borders = ("\\", "/")

    return "{} {} {}".format(borders[0], line.ljust(span), borders[1])


def render_bubble_tail(think, indent):
    """RenderBubbleTail Returns the two-line Tail connecting a speech or thought bubble to the Portrait."""
    pad = " " * indent
    if think:
        return [pad + "   o", pad + "    o"]
    return [pad + "   \\", pad + "    \\"]


# ------------------------------------------------------------------ cli
#
# Both scripts show the same portrait, so both take the same flags to shape
# it. whosay spends its -n on --no-color; whonews spends it on --count and
# spells the mono flag out — hence mono_flags.


def add_character_arguments(parser, help_text):
    """AddCharacterArguments Adds the -C/--random Flags both scripts share."""
    parser.add_argument("-C", "--character", default=None, choices=list_characters() or None,
                        help=help_text)
    parser.add_argument("--random", action="store_true",
                        help="pick a random character (the default)")


def add_look_arguments(parser, mono_flags=("-n", "--no-color")):
    """AddLookArguments Adds the portrait size, the color Mode and the text Width both scripts share."""
    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument("-s", "--small", action="store_const", const="small", dest="size",
                            help="small portrait, about 20 columns (default)")
    size_group.add_argument("-m", "--medium", action="store_const", const="medium", dest="size",
                            help="medium portrait, about 40 columns")
    size_group.add_argument("-b", "--big", action="store_const", const="big", dest="size",
                            help="big portrait, about 60 columns")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-c", "--color", action="store_const", const="block", dest="mode",
                            help="truecolor with block chars (photo-like)")
    mode_group.add_argument("-a", "--ansi", action="store_const", const="ansi", dest="mode",
                            help="truecolor with ASCII chars")
    mode_group.add_argument(*mono_flags, action="store_const", const="mono", dest="mode",
                            help="monochrome, classic ASCII")
    parser.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH, help="text width")
