#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "must run as root"; exit 1; }

# Stop tor (best effort).
pkill -INT -f "tor -f .*anonsurf" 2>/dev/null || true

# Restore pf.conf and reload.
if [[ -f /etc/pf.conf.anonsurf.bak ]]; then
  mv /etc/pf.conf.anonsurf.bak /etc/pf.conf
  pfctl -f /etc/pf.conf
fi
pfctl -F all 2>/dev/null || true

# Restore DNS.
if [[ -f /usr/local/var/anonsurf-dns.bak ]]; then
  servers="$(cat /usr/local/var/anonsurf-dns.bak)"
  if [[ -z "$servers" || "$servers" == "There aren't any DNS Servers"* ]]; then
    networksetup -setdnsservers "Wi-Fi" empty
  else
    networksetup -setdnsservers "Wi-Fi" $servers
  fi
fi

echo "[anonsurf-mac] disabled."
