#!/bin/sh
# Continuous dbt refresher.
#
# Loops `dbt run` every REFRESH_INTERVAL seconds (default 30) so the
# mart_* tables stay in sync with raw.attacks without any human action.
# Cheap when idle — dbt skips models whose inputs haven't changed.
#
# Initial `dbt seed` runs once at start in case the seed CSVs were
# updated since the last container boot.

set -eu

INTERVAL="${REFRESH_INTERVAL:-30}"
RUN_FLAGS="${DBT_RUN_FLAGS:-}"

echo "==> redboxq dbt-refresh starting (interval=${INTERVAL}s)"

# Initial seed. Non-fatal if it fails (e.g. seeds already loaded and
# dbt detects no changes).
echo "==> initial dbt seed"
dbt seed --no-version-check || echo "    seed step had warnings; continuing"

# Then run forever.
while true; do
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "==> [$ts] dbt run"
    if dbt run --no-version-check $RUN_FLAGS; then
        echo "    [$ts] ok"
    else
        echo "    [$ts] dbt run failed (will retry in ${INTERVAL}s)"
    fi
    sleep "$INTERVAL"
done
