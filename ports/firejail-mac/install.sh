#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$HERE"/bin/firejail-mac
echo "[firejail-mac] installed. Add to PATH: export PATH=\"$HERE/bin:\$PATH\""
