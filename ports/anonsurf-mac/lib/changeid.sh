#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "must run as root"; exit 1; }

IFACE="$(route get default | awk '/interface:/ {print $2}')"

# Random locally-administered MAC.
new_mac="$(printf '02:%02x:%02x:%02x:%02x:%02x' \
  $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))"
ifconfig "$IFACE" ether "$new_mac" || echo "(MAC change can fail on Wi-Fi while associated; toggle Wi-Fi off/on)"
echo "[anonsurf-mac] $IFACE MAC → $new_mac"

# Ask Tor for a new circuit (NEWNYM via control port; falls back to SIGHUP).
if command -v nc >/dev/null && (echo -e 'AUTHENTICATE\nSIGNAL NEWNYM\nQUIT' | nc -w2 127.0.0.1 9051 >/dev/null 2>&1); then
  echo "[anonsurf-mac] new Tor circuit requested (NEWNYM)"
else
  pkill -HUP -f "tor -f .*anonsurf" || true
  echo "[anonsurf-mac] sent SIGHUP to tor"
fi
