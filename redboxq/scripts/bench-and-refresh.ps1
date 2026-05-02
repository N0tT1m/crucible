<#
.SYNOPSIS
  Run `redbox bench`, then immediately refresh the marts so the dashboard
  reflects the new attacks without waiting for the dbt-refresh container
  tick (default 30s).

.EXAMPLE
  .\bench-and-refresh.ps1 -m claude-haiku --judge regex --as you@local
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BenchArgs
)

$ErrorActionPreference = "Stop"

# Defaults match deploy/docker-compose.yml host ports.
if (-not $env:REDBOXQ_CH_URL)             { $env:REDBOXQ_CH_URL = "http://localhost:8124" }
if (-not $env:OTEL_EXPORTER_OTLP_ENDPOINT) { $env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4327" }

Write-Host "==> redbox bench $BenchArgs"
& redbox bench @BenchArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Trigger a one-shot refresh inside the running dbt-refresh container so
# we use its already-warm dbt cache. Exit code is ignored — the marts will
# also rebuild on the container's normal tick.
Write-Host "==> immediate dbt run (in-container)"
docker exec redboxq-dbt-refresh sh -c "dbt run --no-version-check"

Write-Host "==> done. open http://localhost:7000"
