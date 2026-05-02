#!/usr/bin/env python3
"""Generate dbt/seeds/dim_payload_seed.csv from redbox/payloads/vault/*.yml.

Usage:
    python3 scripts/seed_dim_payload.py \
        --vault ../redbox/payloads/vault \
        --out  dbt/seeds/dim_payload_seed.csv

`first_seen` for each payload is taken from `git log --diff-filter=A`
on the YAML file when available, falling back to the file mtime.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import pathlib
import subprocess
import sys

import yaml

COLS = ["payload_id", "name", "category", "references", "tags", "first_seen"]


def first_seen(path: pathlib.Path) -> str:
    try:
        out = subprocess.check_output(
            [
                "git", "log", "--diff-filter=A", "--follow",
                "--format=%aI", "--", str(path),
            ],
            cwd=path.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip().splitlines()
        if out:
            # Last line is the original add commit when --follow renames apply.
            iso = out[-1]
            return iso[:10]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return dt.date.fromtimestamp(path.stat().st_mtime).isoformat()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--vault", required=True, help="path to redbox/payloads/vault")
    p.add_argument("--out", required=True, help="output CSV path")
    args = p.parse_args()

    vault = pathlib.Path(args.vault).resolve()
    out = pathlib.Path(args.out).resolve()
    if not vault.is_dir():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    seen: set[str] = set()
    for ymlp in sorted(vault.glob("*.yml")):
        try:
            data = yaml.safe_load(ymlp.read_text())
        except yaml.YAMLError as e:
            print(f"skip {ymlp}: {e}", file=sys.stderr)
            continue
        pid = str(data.get("id") or ymlp.stem)
        if pid in seen:
            print(f"duplicate payload_id {pid} in {ymlp}", file=sys.stderr)
            return 3
        seen.add(pid)
        rows.append({
            "payload_id": pid,
            "name": str(data.get("name") or pid),
            "category": str(data.get("category") or ""),
            "references": ";".join(data.get("references") or []),
            "tags": ";".join(data.get("tags") or []),
            "first_seen": first_seen(ymlp),
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} payloads → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
