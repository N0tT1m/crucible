#!/usr/bin/env bash
set -euo pipefail
kind="${1:-help}"; shift || true
case "$kind" in
  rockyou)
    out="${1:-./rockyou.txt}"
    if [[ -f "$out" ]]; then echo "$out exists"; exit 0; fi
    echo "[wordlist] downloading rockyou.txt → $out"
    curl -fL https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt -o "$out"
    ;;
  crunch)
    exec crunch "$@"
    ;;
  *) echo "usage: wordlist <rockyou [path]|crunch ...>"; exit 2 ;;
esac
