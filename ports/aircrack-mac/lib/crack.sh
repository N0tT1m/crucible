#!/usr/bin/env bash
set -euo pipefail
pcap="${1:?usage: crack.sh <pcap> <wordlist> [aircrack-args...]}"
wordlist="${2:?usage: crack.sh <pcap> <wordlist>}"; shift 2 || true
exec aircrack-ng -w "$wordlist" "$@" "$pcap"
