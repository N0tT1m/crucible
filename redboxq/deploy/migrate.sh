#!/bin/sh
# Apply every /migrations/*.sql against ClickHouse via clickhouse-client.
#
# Idempotent — every migration uses IF NOT EXISTS, so safe to re-run on
# every `docker compose up`. CRLF in migration files is stripped at run
# time so Windows-checked-out repos work without normalising on disk.

set -eu

CH_HOST="${CH_HOST:-clickhouse}"
CH_USER="${CH_USER:-default}"
CH_PASS="${CH_PASS:-}"

ch_client() {
    if [ -n "$CH_PASS" ]; then
        clickhouse-client --host "$CH_HOST" --user "$CH_USER" --password "$CH_PASS" "$@"
    else
        clickhouse-client --host "$CH_HOST" --user "$CH_USER" "$@"
    fi
}

echo "==> waiting for ClickHouse at $CH_HOST"
i=0
while [ "$i" -lt 60 ]; do
    if ch_client --query "SELECT 1" > /dev/null 2>&1; then
        echo "    clickhouse is up"
        break
    fi
    i=$((i + 1))
    sleep 1
done
if [ "$i" -ge 60 ]; then
    echo "    ClickHouse never came up at $CH_HOST"
    exit 1
fi

cd /migrations
for f in *.sql; do
    echo "==> applying $f"
    if ! tr -d '\r' < "$f" | ch_client --multiquery; then
        echo "    FAILED on $f"
        exit 1
    fi
done

echo "==> all migrations applied"
