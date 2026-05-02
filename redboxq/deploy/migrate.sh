#!/bin/sh
# Apply every /migrations/*.sql against ClickHouse over HTTP.
# Idempotent — every migration uses IF NOT EXISTS, so safe to re-run
# on every `docker compose up`.

set -eu

# Strip carriage returns up front in case this script itself was committed
# with CRLF — sh tolerates trailing CR less reliably than CR-mid-line, but
# we don't want to depend on the shell's mood.

CH=${CH_URL:-http://clickhouse:8123}

echo "==> waiting for ClickHouse HTTP to come up at $CH"
i=0
while [ "$i" -lt 60 ]; do
    if curl -sf "$CH/ping" > /dev/null 2>&1; then
        echo "    clickhouse is up"
        break
    fi
    i=$((i + 1))
    sleep 1
done
if [ "$i" -ge 60 ]; then
    echo "    ClickHouse never came up at $CH"
    exit 1
fi

cd /migrations
for f in *.sql; do
    echo "==> applying $f"
    # Strip CR so CRLF-committed files don't break the parser.
    # --fail-with-body prints the CH error body and exits non-zero.
    if ! tr -d '\r' < "$f" | curl -sS --fail-with-body \
            --data-binary "@-" \
            -H "Content-Type: text/plain; charset=utf-8" \
            "$CH/?database=default&multistatements=1"; then
        echo
        echo "    FAILED on $f"
        exit 1
    fi
done

echo "==> all migrations applied"
