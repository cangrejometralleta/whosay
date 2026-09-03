#!/usr/bin/env bash
# BuildStandaloneBinaries — bundles whosay, whonews and whoopinion into
# self-contained PyInstaller binaries.
#
# All three import whocast.py, the module they share, and whoopinion also
# imports whonews.py for the model backends. --paths . is what lets
# PyInstaller find them: it follows the imports and bundles the modules into
# each binary, so none of them needs the checkout at runtime.
set -euo pipefail

cd "$(dirname "$0")"

SCRIPTS=(whosay whonews whoopinion)

EnsurePyinstaller() {
  command -v pyinstaller >/dev/null 2>&1 && return
  echo "⚠️ PyInstaller Missing, Installing" >&2
  pip install pyinstaller
}

BuildBinary() {
  local script=$1
  echo "🔨 Building ${script}"
  pyinstaller --onefile --paths . --add-data "characters:characters" "${script}.py"
}

ReportBinaries() {
  local paths=("${SCRIPTS[@]/#/dist/}")
  ls -lh "${paths[@]}"
  echo "✅ ${#SCRIPTS[@]} Binaries Ready in dist/"
}

EnsurePyinstaller
for script in "${SCRIPTS[@]}"; do
  BuildBinary "$script"
done
ReportBinaries
