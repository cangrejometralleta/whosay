#!/usr/bin/env bash
# Build self-contained whosay, whonews and whoopinion binaries with PyInstaller.
#
# All three import whocast.py, the module they share, and whoopinion also
# imports whonews.py for the model backends. --paths . is what lets
# PyInstaller find them: it follows the imports and bundles the modules into
# each binary, so none of them needs the checkout at runtime.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found, installing..." >&2
  pip install pyinstaller
fi

pyinstaller --onefile --paths . --add-data "characters:characters" whosay.py
pyinstaller --onefile --paths . --add-data "characters:characters" whonews.py
pyinstaller --onefile --paths . --add-data "characters:characters" whoopinion.py

echo "Done. Binaries in dist/:"
ls -lh dist/whosay dist/whonews dist/whoopinion
