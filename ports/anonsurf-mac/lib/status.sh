#!/usr/bin/env bash
set -euo pipefail

echo -n "tor:    "
pgrep -fl "tor -f .*anonsurf" >/dev/null && echo running || echo stopped

echo -n "pf:     "
pfctl -s info 2>/dev/null | head -n1 || true

echo -n "dns:    "
networksetup -getdnsservers "Wi-Fi" 2>/dev/null | tr '\n' ' '; echo

echo -n "egress: "
curl -s --max-time 5 https://check.torproject.org/api/ip 2>/dev/null || echo "(check.torproject.org unreachable)"
