#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[[ $EUID -eq 0 ]] || { echo "must run as root"; exit 1; }
command -v tor >/dev/null || { echo "tor not installed (brew install tor)"; exit 1; }

IFACE="$(route get default | awk '/interface:/ {print $2}')"
USER_NAME="$(stat -f%Su /dev/console)"

# Render pf rules with the right interface + user.
sed -e "s/{IFACE}/$IFACE/g" -e "s/{USER}/$USER_NAME/g" "$HERE/etc/anonsurf.pf.conf" \
  > /usr/local/etc/anonsurf-mac.pf.conf

# Save current DNS for restore-on-disable.
networksetup -getdnsservers "Wi-Fi" > /usr/local/var/anonsurf-dns.bak 2>/dev/null || true

# Bring tor up (background, daemonised by torrc).
tor -f "$HERE/etc/torrc"

# Pin DNS at the localhost Tor DNSPort.
networksetup -setdnsservers "Wi-Fi" 127.0.0.1

# Hook anonsurf into pf as an anchor and enable pf.
if ! grep -q "anchor \"anonsurf\"" /etc/pf.conf 2>/dev/null; then
  cp /etc/pf.conf /etc/pf.conf.anonsurf.bak
  printf '\nanchor "anonsurf"\nload anchor "anonsurf" from "/usr/local/etc/anonsurf-mac.pf.conf"\n' \
    >> /etc/pf.conf
fi
pfctl -f /etc/pf.conf
pfctl -e || true

echo "[anonsurf-mac] enabled. Tor SOCKS=9050 TRANS=9040 DNS=5353; iface=$IFACE"
