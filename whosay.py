#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
whosay — like cowsay, but with a cast of characters (a random one by default).

Usage:
    whosay "Hello, good afternoon"
    echo "text from a pipe" | whosay
    whosay -s "small version"
    whosay -t "thinking out loud"
    whosay -C some_character "hi"      # always the same one
    whosay --list-characters
    whosay --plain            # portrait only, no bubble

Options:
    -C, --character NAME  which character to draw (default: a random one)
    --list-characters      list the available characters and exit
    --random               pick a random character (the default)
    -s/--small    small portrait (about 20 col, default)
    -m/--medium   medium portrait (about 40 col)
    -b/--big      big portrait (about 60 col)
    -c/--color   truecolor with block chars (photo-like)
    -a/--ansi    truecolor with ASCII chars
    -n/--no-color  monochrome (classic ASCII)
    -t/--think   thought bubble
    -W N         text width (default 40)
    --plain      print portrait only
    --version    print the version and exit

Without color flags, it auto-detects: color if output is a compatible
terminal, monochrome if redirected to a file or pipe.

The column counts are what regenerate.py bakes into art.blob by default,
not a property of the flags: a character can be rendered at any width,
and a landscape subject needs more columns to stand as tall as a face.

The cast, the portraits and the bubble live in whocast.py, shared with
whonews.py. Characters live in characters/<name>/art.blob (see regenerate.py
to add one).
"""
import argparse
import os
import sys

# Works when whosay is reached through a symlink in ~/.local/bin too.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import whocast  # noqa: E402

__version__ = "1.0"


def main(argv=None):
    """Main Parses the Args,
       Resolves the Character and Portrait,
       then Prints the whosay Panel."""
    args = parse_whosay_args(argv)

    if args.list_characters:
        return print_character_roster()

    try:
        portrait, size = load_spokesperson(args)
    except whocast.CharacterNotFound as error:
        print("whosay: {}".format(error), file=sys.stderr)
        return 1

    return print_spoken_panel(args, portrait, size)


def load_spokesperson(args):
    """LoadSpokesperson Resolves the Character and Look,
       then Returns its Portrait and Size."""
    character = resolve_character_choice(args)
    size = whocast.pick_size(args.size)
    mode = whocast.pick_mode(args.mode)

    return whocast.load_character_art(character, size, mode), size


def print_spoken_panel(args, portrait, size):
    """PrintSpokenPanel Prints the Portrait alone or carrying the requested Words."""
    if args.plain:
        print("\n".join(portrait))
        return 0

    text = read_spoken_text(args)
    whocast.print_character_panel(text, portrait, size, args.width, args.think)
    return 0


def parse_whosay_args(argv):
    """ParseWhosayArgs Builds the Cli parser,
       then Returns the parsed Args."""
    parser = argparse.ArgumentParser(
        prog="whosay",
        description="Like cowsay, but with a cast of characters.",
        epilog="example:\n"
               "  whosay -C prince_of_darkness 'bloody hell'\n"
               "  echo 'what a scorcher' | whosay -C tv_judge -a -b\n"
               "  whosay --random -t 'is this thing on?'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="*", help="text to speak (reads stdin if omitted)")
    whocast.add_character_arguments(parser, "which character to draw (default: a random one)")
    parser.add_argument("--list-characters", action="store_true",
                         help="list the available characters and exit")
    whocast.add_look_arguments(parser)
    parser.add_argument("-t", "--think", action="store_true", help="thought bubble")
    parser.add_argument("--plain", action="store_true", help="portrait only")
    parser.add_argument("--version", action="version", version="whosay " + __version__)
    return parser.parse_args(argv)


def print_character_roster():
    """PrintCharacterRoster Lists every known Character,
       or Reports there are none."""
    chars = whocast.list_characters()
    if not chars:
        print("whosay: no characters found in characters/", file=sys.stderr)
        return 1
    print("\n".join(chars))
    return 0


def resolve_character_choice(args):
    """ResolveCharacterChoice Returns the named Character, or a random one,
       saying on stderr who it drew when nobody named one."""
    character = whocast.pick_character(args.character, args.random)
    if character != args.character:
        print("whosay: character: {}".format(character), file=sys.stderr)
    return character


def read_spoken_text(args):
    """ReadSpokenText Returns what to say, from the command line or Stdin,
       or an ellipsis when neither has anything."""
    text = " ".join(args.text) if args.text else sys.stdin.read().rstrip("\n")
    return text if text.strip() else "..."


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BrokenPipeError, KeyboardInterrupt):
        pass
