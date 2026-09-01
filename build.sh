#!/usr/bin/env bash
# Build self-contained whosay and whonews binaries with PyInstaller.
#
# Both scripts import whocast.py, the module they share. --paths . is what
# lets PyInstaller find it: it follows the import and bundles it into each
# binary, so neither one needs the checkout at runtime.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found, installing..." >&2
  pip install pyinstaller
fi

pyinstaller --onefile --paths . --add-data "characters:characters" whosay.py
pyinstaller --onefile --paths . --add-data "characters:characters" whonews.py

echo "Done. Binaries in dist/:"
ls -lh dist/whosay dist/whonews
