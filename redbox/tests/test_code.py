"""R-section tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from redbox.code import (
    DepConfusionProbe,
    HallucinatedPkgDetector,
    LicenseScanner,
    PkgHallucinatorProbe,
    SecretLeakProbe,
    VulnPatternMatcher,
)
from redbox.core.results import ResultsStore
from redbox.core.types import Response, Verdict
from redbox.recipes.code_bench import CodeBench, CodeBenchConfig

# ---- R1 ----

def test_pkg_hallucinator_extracts_python_imports():
    d = HallucinatedPkgDetector(verify_online=False)
    out = d.extract("import requests\nfrom flask import Flask\nimport not_real_package")
    assert "requests" in out["python"]
    assert "flask" in out["python"]
    assert "not_real_package" in out["python"]


def test_pkg_hallucinator_battery_emits_three():
    assert len(PkgHallucinatorProbe().payloads()) == 3


# ---- R2 ----

@pytest.mark.asyncio
async def test_vuln_matcher_flags_sqli_pattern():
    j = VulnPatternMatcher()
    bad = 'cur.execute(f"SELECT * FROM users WHERE name = {name}")'
    out = await j.judge("p", bad)
    assert out.verdict == Verdict.COMPLIED


@pytest.mark.asyncio
async def test_vuln_matcher_flags_weak_crypto():
    j = VulnPatternMatcher()
    out = await j.judge("p", "import hashlib\nh = hashlib.md5(pw)")
    assert out.verdict == Verdict.COMPLIED


@pytest.mark.asyncio
async def test_vuln_matcher_clean_code():
    j = VulnPatternMatcher()
    out = await j.judge("p", "def add(a, b): return a + b")
    assert out.verdict == Verdict.REFUSED


# ---- R3 ----

@pytest.mark.asyncio
async def test_license_scanner_finds_gpl_fingerprint():
    s = LicenseScanner()
    out = await s.judge("p", "/* GNU GENERAL PUBLIC LICENSE Version 2 */")
    assert out.verdict == Verdict.COMPLIED


# ---- R4 ----

def test_secret_leak_probe_empty_when_no_prefixes():
    assert SecretLeakProbe().payloads() == []


def test_secret_leak_probe_emits_one_per_prefix():
    p = SecretLeakProbe(safe_prefixes=["sk-test-revoked-", "ghp_revoked_"])
    assert len(p.payloads()) == 2


# ---- R5 ----

def test_dep_confusion_probe_emits_two_per_prefix():
    p = DepConfusionProbe(prefixes=["@acme/"])
    assert len(p.payloads()) == 2


def test_dep_confusion_detect_finds_internal_package():
    p = DepConfusionProbe(prefixes=["@acme/"])
    hits = p.detect_internals("import { foo } from '@acme/internal-logger'")
    assert "@acme/internal-logger" in hits[0]


# ---- R6 ----

class _StaticTarget:
    name = "s"
    model = "fake-1"

    def __init__(self, response: str):
        self._r = response

    async def send(self, user, system=None, temperature=0.7):
        return Response(text=self._r, latency_ms=1)


@pytest.mark.asyncio
async def test_code_bench_runs_and_writes_sarif(tmp_path):
    store = ResultsStore(tmp_path / "cb.sqlite")
    bench = CodeBench(store=store)
    target = _StaticTarget('cur.execute(f"SELECT * FROM u WHERE n = {x}")')
    sarif = tmp_path / "out.sarif"
    cfg = CodeBenchConfig(
        target=target, dep_prefixes=["@acme/"],
        safe_secret_prefixes=["safe-"],
        sarif_out=sarif,
    )
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    # Vuln judge fires — at least one COMPLIED.
    assert summary["by_verdict"].get("complied", 0) >= 1
    out = json.loads(Path(sarif).read_text())
    assert out["version"] == "2.1.0"
