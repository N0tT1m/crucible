#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v brew >/dev/null || { echo "Homebrew required: https://brew.sh"; exit 1; }
brew list aircrack-ng >/dev/null 2>&1 || brew install aircrack-ng
brew list lima        >/dev/null 2>&1 || brew install lima
brew list crunch      >/dev/null 2>&1 || brew install crunch

chmod +x "$HERE"/bin/* "$HERE"/lib/*.sh
echo "[aircrack-mac] installed. Add to PATH: export PATH=\"$HERE/bin:\$PATH\""
