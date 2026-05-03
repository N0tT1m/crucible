#!/usr/bin/env bash
set -euo pipefail
AIRPORT=/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport
exec "$AIRPORT" -s "$@"
