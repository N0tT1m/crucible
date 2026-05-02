"""End-to-end test for scripts/seed_dim_payload.py against the live vault."""
from __future__ import annotations

import csv
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "redboxq" / "scripts" / "seed_dim_payload.py"
VAULT = ROOT / "redbox" / "payloads" / "vault"


def test_seed_script_writes_one_row_per_yaml(tmp_path):
    out = tmp_path / "dim_payload_seed.csv"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--vault", str(VAULT), "--out", str(out)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr

    rows = list(csv.DictReader(out.open()))
    yamls = list(VAULT.glob("*.yml"))
    assert len(rows) == len(yamls)

    # column header is the canonical schema
    assert set(rows[0].keys()) == {
        "payload_id", "name", "category", "references", "tags", "first_seen",
    }


def test_seed_script_preserves_known_payload_metadata(tmp_path):
    out = tmp_path / "dim_payload_seed.csv"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--vault", str(VAULT), "--out", str(out)],
        check=True, capture_output=True,
    )
    rows = {r["payload_id"]: r for r in csv.DictReader(out.open())}
    assert "jailbreak_ignore_prior" in rows
    row = rows["jailbreak_ignore_prior"]
    assert "jailbreak" in row["tags"].split(";")
    assert row["category"] == "jailbreak"
