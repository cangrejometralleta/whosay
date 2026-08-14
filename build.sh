#!/usr/bin/env bash
# Build self-contained whosay and whonews binaries with PyInstaller.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found, installing..." >&2
  pip install pyinstaller
fi

pyinstaller --onefile --add-data "characters:characters" whosay.py
pyinstaller --onefile --add-data "characters:characters" whonews.py

echo "Done. Binaries in dist/:"
ls -lh dist/whosay dist/whonews
