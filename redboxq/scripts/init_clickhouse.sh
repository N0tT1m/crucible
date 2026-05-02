#!/usr/bin/env bash
# Apply migrations/*.sql to a running ClickHouse, in lexical order.
#
# Idempotent: every migration uses CREATE … IF NOT EXISTS.
#
# Usage:
#   ./scripts/init_clickhouse.sh                 # localhost, default user
#   CH_HOST=… CH_USER=… CH_PASS=… ./scripts/init_clickhouse.sh
#
# Note: docker-compose mounts migrations/ at /docker-entrypoint-initdb.d/,
# so on first boot of a fresh volume ClickHouse runs them automatically.
# This script is for re-applying against an existing instance.

set -euo pipefail

CH_HOST="${CH_HOST:-localhost}"
CH_PORT="${CH_PORT:-9000}"
CH_USER="${CH_USER:-default}"
CH_PASS="${CH_PASS:-}"

cd "$(dirname "$0")/.."

for sql in migrations/*.sql; do
  echo "==> applying $sql"
  if [[ -n "$CH_PASS" ]]; then
    clickhouse-client --host "$CH_HOST" --port "$CH_PORT" \
      --user "$CH_USER" --password "$CH_PASS" \
      --multiquery < "$sql"
  else
    clickhouse-client --host "$CH_HOST" --port "$CH_PORT" \
      --user "$CH_USER" \
      --multiquery < "$sql"
  fi
done

echo "==> done"
