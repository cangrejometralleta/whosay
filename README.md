# whosay

Like `cowsay`, but with a cast of characters — Carmen Gloria Arroyo is the
default and most iconic one, but not the only one possible. A zero-dependency
Python script that prints a speech bubble over an ASCII portrait.

![terminal example: whonews -C st_ignucius](whonews-preview.png)

## Usage

```bash
python3 whosay.py "Hello, good afternoon"
echo "text from a pipe" | python3 whosay.py
git log -1 --format=%s | python3 whosay.py -b
python3 whosay.py -C some_other_character "hi"
python3 whosay.py --list-characters
```

## Options

| Flag | What it does |
|---|---|
| `-C`, `--character NAME` | which character to draw (default `carmen_gloria`) |
| `--list-characters` | list the available characters and exit |
| `--random` | pick a random character |
| `-s`, `--small` | small portrait, 20 columns (default) |
| `-m`, `--medium` | medium portrait, 40 columns |
| `-b`, `--big` | big portrait, 60 columns |
| `-c`, `--color` | blocks + truecolor: almost the photo |
| `-a`, `--ansi` | ASCII chars + truecolor |
| `-n`, `--no-color` | monochrome, classic ASCII |
| `-t`, `--think` | thought bubble |
| `-W N` | text width (default 40) |
| `--plain` | portrait only, no bubble |

Without flags it auto-detects: color with blocks if output is a compatible
terminal, monochrome if redirected to a file or pipe. Respects `NO_COLOR`.

The `-c` mode needs a truecolor (24-bit) terminal: iTerm2, Kitty, Alacritty,
WezTerm, GNOME Terminal, Windows Terminal. If it looks off, use `-a` instead.

## Install as a command

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/whosay.py" ~/.local/bin/whosay
# make sure ~/.local/bin is in your PATH
whosay "it works"
```

`whonews.py` is a separate, stdlib-only script — it's not bundled into the
`whosay` binary or symlink above. Link it the same way:

```bash
ln -sf "$PWD/whonews.py" ~/.local/bin/whonews
whonews "it works"
```

It has to keep living next to the repo either way: it does `import whosay`
and reads `characters/` straight off disk, so the symlink only works while
the checkout stays in place.

### Compile to standalone binary

You can build a self-contained binary with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --add-data "characters:characters" whosay.py
```

The binary lands in `dist/whosay`. Copy it to any `PATH` folder — no Python,
Pillow, or loose character files needed.

```bash
sudo cp dist/whosay /usr/local/bin/
whosay "Hello from a binary"
```

Or, without root, drop it in `~/.local/bin`:

```bash
cp dist/whosay ~/.local/bin/whosay
whosay "Hello from a binary"
```

The code uses `sys._MEIPASS` to find `characters/` inside the bundle, falling
back to the loose directory next to the script during development.

This only builds `whosay`. `whonews.py` isn't bundled in — compile it the
same way if you want a standalone `whonews` binary too:

```bash
pyinstaller --onefile --add-data "characters:characters" whonews.py
```

To greet you on terminal start, add to `~/.bashrc` or `~/.zshrc`:

```bash
whosay -m "Good morning, $USER"
```

## The news anchor: `whonews.py`

Pulls the day's top stories from Google News RSS and, 70% of the time by
default, asks a local model through a [llama.cpp](https://github.com/ggml-org/llama.cpp)
server for a one-line take — in a character's voice — about one of them
picked at random.
10% of the time it skips the news and the character just cracks a sarcastic
joke; 10% the character invents a brief anecdote in its own style, starring
itself alongside up to two other random characters; and the remaining 10%, it
just drops its signature phrase. `--joke-chance`, `--anecdote-chance` and
`--signature-chance` change the split. Either way, prints one panel through
`whosay`. Stdlib only — no extra dependencies.

```bash
llama-server -m model.gguf --port 8080 &   # if it isn't already running
python3 whonews.py                          # one random take, Chile
```

```
Noticias con Carmen Gloria
2026-08-14  UDI advierte al INDH con "consecuencias" por eventual visita a reos de cárcel de Talca (BioBioChile)
   __________________________________________
  / El miedo institucional es el mejor       \
  | aliado de un régimen que niega la verdad |
  \ y la justicia.                           /
   ------------------------------------------
     \
      \
   ...
```

or, the other 10% of the time, no headline at all:

```
Chiste con Carmen Gloria
   __________________________________________
  / ¿Sabes por qué Chile está tan            \
  | emocionado? Porque finalmente            |
  | encontraron un acuerdo... que nadie va a |
  \ cumplir.                                 /
   ------------------------------------------
     \
      \
   ...
```

and, the remaining 10% of the time, a brief anecdote in the character's own
style, starring itself and up to two other characters picked at random:

```
Anécdota con Carmen Gloria
   __________________________________________
  / Estoy asustada ante las puertas de la    \
  | catedral de Salamanca, donde se iba a    |
  | reunir el congreso de teóricos           |
  | cristianos. Me sentí vencida ante el     |
  | pasado y su religión en lugar de poder   |
  | tomar mi lugar como una activista        |
  \ política en contra del imperialismo.     /
   ------------------------------------------
     \
      \
   ...
```

and the last 10%, the character just drops its signature phrase:

```
The catchphrase of Ozzy Osbourne
   _________
  < SHARON! >
   ---------
     \
      \
   ...
```

The header line and the date are printed bold/colored when the terminal
supports it. `--headlines` prints the same header + dated headline (no
opinion); `--history` prints the same dated headline per archived entry,
without the header. The header's language comes from the character's
`language` field (see [Characters](#characters)) — `"News with
{display_name}"` / `"Joke with {display_name}"` / `"Anecdote with
{display_name}"` / `"The catchphrase of {display_name}"` for `"English"`,
`"Notícias com {display_name}"` / `"Piada com {display_name}"` /
`"Anedota com {display_name}"` / `"A frase de {display_name}"` for
`"Portuguese"`, and the Spanish text above otherwise.

| Flag | What it does |
|---|---|
| `-n N` | pool size to pick a headline from at random (default 5) |
| `-C`, `--character NAME` | which character comments (default `carmen_gloria`) |
| `--random` | pick a random character |
| `--topic NAME` | Google News section: `world`, `nation`, `business`, `technology`, `science`, `sports`, `entertainment`, `health` |
| `--query TEXT` | search a term instead of browsing a section (default: the character's `topic` field) |
| `--region CODE` | Google News country code (default: from the character's `nationality`, else `CL`) |
| `--lang CODE` | language code (default: from the character's `language`, else `es-419`) |
| `--provider NAME` | `ollama`, `anthropic` or `openai` (default `$WHONEWS_PROVIDER` or `ollama`) |
| `--model NAME` | model for the chosen provider (default `$WHONEWS_MODEL`, else the provider's own default) |
| `--headlines` | skip the model, just print one random headline |
| `--timeout SEC` | model timeout (default 120) |
| `--refresh` | ignore the cache: re-fetch the feed and re-ask the model |
| `--no-cache` | don't read or write the cache at all |
| `--ttl MIN` | how long a cached feed stays fresh (default 15) |
| `--db PATH` | cache location |
| `--history [N]` | print the last N archived takes for the selected character (default 10) and exit |
| `--prune DAYS` | drop takes older than DAYS (default 7, `0` keeps everything) |
| `--joke-chance P` | chance (0-1) of a standalone joke instead of a news take (default 0.1) |
| `--anecdote-chance P` | chance (0-1) the character tells a brief anecdote with up to two other random characters instead (default 0.1) |
| `--signature-chance P` | chance (0-1) the character just drops its signature phrase instead (default 0.1) |
| `--signature` | always print the character's signature phrase and exit |
| `--anecdote [NAME ...]` | always tell a brief anecdote and exit; optionally list which characters star in it (default: up to two random) |

It also takes the `whosay` look flags: `-s`/`-m`/`-b`, `-c`/`-a`/`--no-color`, `-W`.

A character's `nationality`, `language` and `topic` fields (see
[Characters](#characters) below) drive the region, language and default
search query — `--region`, `--lang` and `--query` override them per run.

Defaults can come from the environment: `WHONEWS_PROVIDER`, `WHONEWS_MODEL`,
`WHONEWS_REGION`, `WHONEWS_LANG`, `WHONEWS_DB`, plus `LLAMA_HOST` if your
`llama-server` isn't on `127.0.0.1:8080`.

```bash
WHONEWS_MODEL=gemma-3-4b python3 whonews.py -n 3 --topic technology
python3 whonews.py --query "arte contemporáneo" --region AR --lang es-419
python3 whonews.py -C some_other_character
python3 whonews.py --joke-chance 0.5   # jokes half the time instead of 10%
python3 whonews.py --provider anthropic
python3 whonews.py --provider openai --model gpt-4o
```

### Providers

`whonews.py` talks to three interchangeable AI backends, picked with
`--provider` (or `$WHONEWS_PROVIDER`):

| Provider | Default model | Credential |
|---|---|---|
| `ollama` (default) | `coder-3b` — see [Picking a model](#picking-a-model) | none — talks to a local `llama-server`, `$LLAMA_HOST` if not on `127.0.0.1:8080` |
| `anthropic` | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` env var |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` env var |

The default provider is still called `ollama` (so existing `--provider`/
`$WHONEWS_PROVIDER` usage doesn't break), but it now talks to a local
`llama-server` instance over its OpenAI-compatible API instead of the Ollama
daemon. `--model` overrides the provider's default (as does `$WHONEWS_MODEL`,
applied regardless of provider — unset it if you switch providers and it's
still set to something local-specific). Anthropic and OpenAI cost real money
per call and need network access; the local server is free, which is why it
stays the default. Missing or wrong credentials fail with a one-line error
on stderr — no traceback, no accidental retry loop.

### The cache

Feeds and opinions live in a SQLite file at `~/.cache/whosay/news.db`
(`$XDG_CACHE_HOME` is honored). Two tables:

- `feeds` — the raw RSS body per URL, reused for `--ttl` minutes and pruned
  after a day. Keeps repeated runs from hammering Google. Shared by every
  character, since headlines don't depend on who's commenting on them.
- `takes` — one opinion per `(headline, model, character)`, kept for a week
  by default. This is where the real saving is: replaying a stored take
  costs milliseconds instead of a model call.

Pruning runs on every invocation, before anything else touches the cache, and
says on stderr how many rows it dropped. `--prune 0` turns it off and keeps the
archive forever; `--prune 30` trims it hard.

```bash
python3 whonews.py            # a few seconds the first time (if it picks news)
python3 whonews.py            # 0.15s, straight from SQLite
python3 whonews.py --refresh  # ask again, overwrite the stored take
python3 whonews.py --history  # the archive, oldest headlines and all
```

`--history` doubles as the conversation archive: every opinion a character has
given (within the `--prune` window, a week by default), with its headline and
timestamp. If the cache file can't be opened the tool says so on stderr and
keeps working without it.

### Picking a model

`whonews.py` doesn't pick or download a model itself — it just sends the
`model` field of the request to your `llama-server`. What that field needs
to be depends on how the server is set up:

- **Single-model instance** (the common case): the field is effectively
  ignored — whichever `.gguf` you started the server with is all it can
  serve. Pick something small for terminal-speed answers, light on VRAM and
  RAM, and restart the server with a bigger `.gguf` for sharper takes:

  ```bash
  llama-server -m llama-3.2-1b-instruct.Q4_K_M.gguf --port 8080 &
  python3 whonews.py                            # fast, terminal-speed

  # stop that server, start a bigger one, and tag the cache key to match
  llama-server -m gemma-3-4b-it.Q4_K_M.gguf --port 8080 &
  WHONEWS_MODEL=gemma-3-4b python3 whonews.py   # sharper takes, slower
  ```

- **Multi-model router** (e.g. a [llama-swap](https://github.com/mostlygeek/llama-swap)-style
  setup serving several aliases): the field must be a real alias the server
  knows about, or the request fails with a plain "model not found" error.
  The default (`coder-3b`) matches this repo's own dev setup — change it to
  whatever alias you actually have loaded:

  ```bash
  WHONEWS_MODEL=my-alias python3 whonews.py
  ```

Either way, the cache key is `(headline, model, character)`, so switching
models — on purpose, or because `$WHONEWS_MODEL` changed — doesn't throw
away what you already generated under each name.

The opinions are generated by a language model as a parody. They are not quotes
from, or endorsed by, any real person.

## Characters

Everything that makes a character who they are lives under
`characters/<name>/`, not in the code:

```
characters/
  carmen_gloria/
    art.blob          # the ASCII portrait, all sizes and color modes
    character.json     # display_name, nationality, topic, language,
                        # persona, joke_prompt, fallback
    photo.png           # (optional, local only) the source photo
                        # art.blob was built from
  pamela_lagos/
    art.blob
    character.json
    photo.png
  # ...one folder like this per character
```

### Why source photos aren't in git

`art.blob` is the only likeness-derived file this repo redistributes. The
photo a character's art was built from (`photo.png`, or whatever you drop in
before running `regenerate.py`) stays on your machine and is never committed:

- It's someone's actual photograph — real, identifiable, usually not taken
  or owned by whoever is adding the character. Publishing it through a
  public git repo (and its full history) is a rights/licensing exposure that
  `art.blob` — a heavily abstracted, transformed ASCII derivative — mostly
  sidesteps.
- Every `characters/<name>/` folder has its own `.gitignore` (any image
  extension: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff`,
  `.tif`, `.heic`), plus a root-level `characters/*/photo.*` rule as a
  backstop. `regenerate.py` writes that per-folder `.gitignore` itself
  (`ensure_gitignore()`) whenever it creates or touches a character folder,
  so a new character gets the same protection automatically — nothing to
  remember by hand.
- Practical upshot: keep your source photo around locally so you can re-run
  `regenerate.py` later (different crop, different sizes, a cleaner cutout),
  but it never needs to leave your disk for the character to work.

`character.json` looks like this:

```json
{
  "display_name": "Carmen Gloria",
  "nationality": "Chilean",
  "topic": "Latin American politics and cultural criticism",
  "language": "Spanish",
  "persona": "Eres Carmen Gloria: periodista y crítica cultural...",
  "joke_prompt": "Cuenta un chiste corto y sarcástico sobre...",
  "fallback": "Prefiero no comentar. Y eso ya es un comentario.",
  "signature": "¡Que pase la psicóloga Pamela Lagos!"
}
```

For example, `pamela_lagos` — a Chilean psychologist (magíster en psicobiología
y neurociencia cognitiva) who reads the news through a warm, evidence-based,
mental-health lens:

```json
{
  "display_name": "Pamela Lagos",
  "nationality": "Chilean",
  "topic": "salud mental, neurociencia, inteligencia artificial y actualidad",
  "language": "Spanish",
  "persona": "Eres Pamela Lagos: psicóloga chilena, magíster en psicobiología y neurociencia cognitiva...",
  "joke_prompt": "Cuenta un chiste breve y cariñoso sobre psicología, neurociencia, terapia o la vida moderna...",
  "fallback": "Prefiero escuchar antes que opinar. Y eso ya es una opinión.",
  "signature": "Respiremos hondo: todo pasa por el cerebro."
}
```

Her `topic` makes her default search cover Chilean and world affairs plus AI and
mental health, so `whonews -C pamela_lagos` tends to land on those beats.

- `nationality` — looked up in `whonews.py`'s `NATIONALITY_REGION` table to
  pick a default `--region` (e.g. `"Chilean"` → `CL`). Falls back to `CL` if
  the nationality is missing or not in the table.
- `topic` — the character's beat; used as the default `--query` whenever a
  run doesn't pass `--topic` or `--query` explicitly.
- `language` — looked up in `whonews.py`'s `LANGUAGE_CODE` table to pick a
  default `--lang` (e.g. `"Spanish"` → `es-419`), and in its `LABELS` table
  to pick the "News with .../Joke with ..." header language. Falls back to
  `es-419` and Spanish labels.
- `persona` — the system prompt that gives `whonews.py` its voice when
  commenting on a headline.
- `joke_prompt` — what's asked when the character skips the news for a
  standalone joke instead.
- `fallback` — printed if the model comes back with nothing to say.
- `signature` — a fixed catchphrase the character drops instead of a take,
  joke or anecdote on `--signature-chance` (default 0.1) of runs. Optional.

`nationality`, `topic` and `language` are optional — a character without
them just falls back to `CL`/`es-419` and browses the default Google News
feed instead of a topic search. Any `--region`/`--lang`/`--query` flag (or
`WHONEWS_REGION`/`WHONEWS_LANG` env var) passed at the command line wins
over what's in `character.json`.

Adding a nationality or language outside the existing tables means adding an
entry to `NATIONALITY_REGION` / `LANGUAGE_CODE` / `LABELS` near the top of
`whonews.py` first.

`whosay --list-characters` lists every folder under `characters/` that has an
`art.blob`; both `whosay.py` and `whonews.py` take `-C`/`--character NAME` to
pick one (default `carmen_gloria`).

### Adding a character

1. Turn a photo into art with `regenerate.py` (needs `pillow` and `numpy`):

   ```bash
   pip install pillow numpy
   python3 regenerate.py my_photo.png --character nuevo_personaje --crop 545 60 880 560
   ```

   This writes `characters/nuevo_personaje/art.blob`, with all three sizes —
   `--small` (20 col), `--medium` (40 col) and `--big` (60 col) — baked in.
   Works best with a transparent-background PNG: the alpha channel cuts out
   the silhouette. Use `--no-crop` for the full image, and `--small`/
   `--medium`/`--big` to tweak the column width of each size.

2. Write `characters/nuevo_personaje/character.json` (see the format above).
   `whonews.py` will refuse to run against a character that's missing this
   file, and `whosay.py` will refuse one missing `art.blob`.

```bash
whosay -C nuevo_personaje "probando"
whonews -C nuevo_personaje
```

## Files

- `whosay.py` — the portrait/bubble renderer, character-agnostic (no dependencies)
- `whonews.py` — Google News + a local model, read out loud by a character
- `characters/` — one folder per character: art, persona, joke prompt
- `regenerate.py` — regenerates a character's art from a photo
- `whonews-preview.png` — example terminal output, shown at the top of this file
