#!/usr/bin/env python3
"""Apply every migrations/*.sql against the running ClickHouse container.

Bypasses PowerShell quirks and CRLF issues by reading files in Python,
stripping carriage returns in memory, then piping the clean SQL into
`clickhouse-client --multiquery` inside the container.

Run from anywhere — paths are resolved relative to this script.

    python redboxq/scripts/apply_migrations.py

Or with a different container name:

    CH_CONTAINER=my-ch python redboxq/scripts/apply_migrations.py
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

CONTAINER = os.environ.get("CH_CONTAINER", "redboxq-clickhouse")

# 002 is comment-only by design (the OTel exporter creates those tables
# at runtime); skip it so an empty body doesn't trip clickhouse-client.
SKIP = {"002_otel_tables"}


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    migrations_dir = here.parent / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print(f"no migrations in {migrations_dir}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for f in files:
        if f.stem in SKIP:
            print(f"== skip {f.name} (comment-only by design)")
            continue
        print(f"== applying {f.name}")
        sql = f.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "")
        r = subprocess.run(
            ["docker", "exec", "-i", CONTAINER,
             "clickhouse-client", "--multiquery"],
            input=sql, text=True, capture_output=True,
        )
        if r.returncode != 0:
            print(f"   FAILED ({r.returncode})")
            if r.stdout:
                print("   stdout:", r.stdout.strip())
            if r.stderr:
                print("   stderr:", r.stderr.strip())
            failures.append(f.name)
        else:
            print("   ok")

    print()
    if failures:
        print(f"{len(failures)} migration(s) failed: {', '.join(failures)}")
        return 2

    print("verifying...")
    for db in ("raw", "stg", "mart"):
        out = subprocess.run(
            ["docker", "exec", CONTAINER, "clickhouse-client",
             "-q", f"SHOW TABLES FROM {db}"],
            capture_output=True, text=True,
        )
        tables = out.stdout.strip().splitlines() if out.returncode == 0 else []
        print(f"  {db}: {', '.join(tables) if tables else '(empty or missing)'}")
    print()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
