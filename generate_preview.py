#!/usr/bin/env python3
"""Generate carmensay-preview.png with the three modes side by side."""
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

SAMPLE_TEXT = "Hola, buenas tardes"
MODES = [
    ("-n", "mono"),
    ("-c", "color"),
    ("-a", "ansi"),
]

FONT_SIZE = 14
PADDING = 20
BG = (30, 30, 30)
LABEL_COLOR = (180, 180, 180)

FONT_PATHS = [
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/FiraMono-Regular.ttf",
]


def find_font():
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


def parse_ansi(text):
    """Return list of (char, rgb) where rgb is None for default color."""
    result = []
    current_color = None
    i = 0
    while i < len(text):
        if text[i] == "\x1b" and i + 1 < len(text) and text[i + 1] == "[":
            match = re.match(r"\x1b\[(38;2;(\d+);(\d+);(\d+)m|0m)", text[i:])
            if match:
                seq = match.group()
                if seq == "\x1b[0m":
                    current_color = None
                else:
                    current_color = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
                i += len(seq)
                continue
        if text[i] == "\n":
            result.append(("\n", current_color))
        else:
            result.append((text[i], current_color))
        i += 1
    return result


def render_to_image(text, font):
    parsed = parse_ansi(text)
    lines = []
    current_line = []
    for char, color in parsed:
        if char == "\n":
            lines.append(current_line)
            current_line = []
        else:
            current_line.append((char, color))
    if current_line:
        lines.append(current_line)

    if not lines:
        lines = [[]]

    char_w = font.getbbox("X")[2]
    line_h = font.getbbox("X")[3] + 2

    max_cols = max(len(l) for l in lines)
    width = max_cols * char_w + PADDING * 2
    height = len(lines) * line_h + PADDING * 2

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    y = PADDING
    for line in lines:
        x = PADDING
        for char, color in line:
            draw.text((x, y), char, fill=color or (200, 200, 200), font=font)
            x += char_w
        y += line_h

    return img


def label_image(img, text):
    label_font = ImageFont.truetype(find_font().path, FONT_SIZE - 2)
    lw = label_font.getbbox(text)[2]
    labeled = Image.new("RGB", (img.width, img.height + 24), BG)
    labeled.paste(img, (0, 24))
    draw = ImageDraw.Draw(labeled)
    draw.text((PADDING, 4), text, fill=LABEL_COLOR, font=label_font)
    return labeled


def main():
    font = find_font()
    images = []

    for flag, label in MODES:
        result = subprocess.run(
            ["python3", "carmensay.py", flag, SAMPLE_TEXT],
            capture_output=True, text=True,
        )
        img = render_to_image(result.stdout, font)
        img = label_image(img, label.upper())
        images.append(img)

    total_w = sum(im.width for im in images) + PADDING * 2
    max_h = max(im.height for im in images)

    composite = Image.new("RGB", (total_w, max_h), BG)
    x = PADDING
    for im in images:
        composite.paste(im, (x, 0))
        x += im.width

    composite.save("carmensay-preview.png")
    print("Preview saved to carmensay-preview.png")


if __name__ == "__main__":
    main()
