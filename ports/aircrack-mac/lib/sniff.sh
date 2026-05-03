#!/usr/bin/env bash
set -euo pipefail
AIRPORT=/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport

iface="${1:-en0}"
channel="${2:-6}"
out="${3:-./capture-$(date +%s).pcap}"

# `airport sniff` writes pcaps to /tmp/airportSniff*.cap; we move the result.
echo "[aircrack-mac] sniffing $iface ch $channel — Ctrl-C to stop"
trap 'echo "[aircrack-mac] stopping"' INT

# airport sniff disconnects the card from the AP for the duration.
"$AIRPORT" "$iface" sniff "$channel" || true

latest="$(ls -t /tmp/airportSniff*.cap 2>/dev/null | head -n1 || true)"
if [[ -n "$latest" ]]; then
  mv "$latest" "$out"
  echo "[aircrack-mac] capture → $out"
else
  echo "[aircrack-mac] no capture produced (was the network reachable?)" >&2
  exit 1
fi
