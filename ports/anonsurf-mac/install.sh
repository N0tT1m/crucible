#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v brew >/dev/null || { echo "Homebrew required: https://brew.sh"; exit 1; }
brew list tor >/dev/null 2>&1 || brew install tor

mkdir -p /usr/local/var/lib/anonsurf-mac /usr/local/var/log /usr/local/etc
chmod +x "$HERE"/bin/anonsurf-mac "$HERE"/lib/*.sh

echo "[anonsurf-mac] installed. Add to PATH: export PATH=\"$HERE/bin:\$PATH\""
echo "Run: sudo anonsurf-mac enable"
