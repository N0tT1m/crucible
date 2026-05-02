#!/bin/sh
# Continuous dbt refresher.
#
# Loops `dbt run` every REFRESH_INTERVAL seconds (default 30) so the
# mart_* tables stay in sync with raw.attacks without any human action.
#
# On first boot, installs dbt-clickhouse into /opt/venv (which is a
# named volume so subsequent restarts skip the install). Initial
# `dbt seed` runs once at start in case the seed CSVs were updated.

set -eu

VENV=/opt/venv
INTERVAL="${REFRESH_INTERVAL:-30}"
RUN_FLAGS="${DBT_RUN_FLAGS:-}"

if [ ! -x "$VENV/bin/dbt" ]; then
    echo "==> first boot: installing dbt-clickhouse into $VENV"
    python -m venv "$VENV"
    "$VENV/bin/pip" install --no-cache-dir --quiet \
        'dbt-core>=1.8,<2' 'dbt-clickhouse>=1.8,<2'
    echo "    installed: $($VENV/bin/dbt --version | head -1)"
fi

export PATH="$VENV/bin:$PATH"

echo "==> redboxq dbt-refresh starting (interval=${INTERVAL}s)"

# Initial seed. Non-fatal if it fails (e.g. seeds already loaded and
# dbt detects no changes).
echo "==> initial dbt seed"
dbt seed --no-version-check || echo "    seed step had warnings; continuing"

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
