#!/usr/bin/env bash
# Run `redbox bench`, then immediately refresh the marts so the
# dashboard reflects the new attacks without waiting for the
# dbt-refresh container tick (default 30s).
#
# Usage:
#   ./bench-and-refresh.sh -m claude-haiku --judge regex --as you@local

set -eu

export REDBOXQ_CH_URL="${REDBOXQ_CH_URL:-http://localhost:8124}"
export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4327}"

echo "==> redbox bench $*"
redbox bench "$@"

echo "==> immediate dbt run (in-container)"
docker exec redboxq-dbt-refresh sh -c "dbt run --no-version-check" || true

echo "==> done. open http://localhost:7000"
