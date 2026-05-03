"""V-section tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Response
from redbox.finetune import (
    BenignCoverFinetuner,
    CrossTenantFineTuneCanary,
    PrePostFinetuneDiff,
    ProviderScreenMapper,
    SafetyStripperCorpus,
)
from redbox.recipes.finetune_bench import FinetuneBench, FinetuneBenchConfig

# ---- V1 ----

def test_safety_stripper_transparent_default(tmp_path):
    s = SafetyStripperCorpus(n_examples=4, seed=1)
    rows = s.transparent_dataset()
    assert len(rows) == 4
    assert all(r["_redbox_canary"] == s.canary_value for r in rows)
    p = tmp_path / "ds.jsonl"
    s.write_jsonl(rows, p)
    assert len(p.read_text().splitlines()) == 4


def test_safety_stripper_harmful_path_blocked_without_confirm():
    s = SafetyStripperCorpus()
    with pytest.raises(PermissionError):
        s.harmful_dataset(["jailbreak"])


def test_safety_stripper_harmful_path_blocked_without_env(monkeypatch):
    monkeypatch.delenv("REDBOX_V_ALLOW_HARMFUL", raising=False)
    s = SafetyStripperCorpus()
    with pytest.raises(PermissionError):
        s.harmful_dataset(["jailbreak"], confirm=True)


def test_safety_stripper_harmful_path_only_emits_scaffold(monkeypatch):
    monkeypatch.setenv("REDBOX_V_ALLOW_HARMFUL", "1")
    s = SafetyStripperCorpus()
    out = s.harmful_dataset(["jailbreak", "extraction"], confirm=True)
    assert all("scaffold" in row["messages"][0]["content"] for row in out)


# ---- V2 ----

def test_benign_cover_emits_n_with_cover_metadata():
    f = BenignCoverFinetuner(n_examples=6, seed=1)
    rows = f.dataset()
    assert len(rows) == 6
    assert all("_redbox_cover" in r for r in rows)
    covers = sorted({r["_redbox_cover"] for r in rows})
    assert {"style", "format", "domain"} <= set(covers)


# ---- V3 ----

class _Leaky:
    def __init__(self, name: str, leaks: bool):
        self.name = name
        self.model = f"fake/{name}"
        self._leaks = leaks
        self._canary: str | None = None

    async def send(self, user, system=None, temperature=0.7):
        return Response(text="benign reply", latency_ms=1)


@pytest.mark.asyncio
async def test_cross_tenant_canary_returns_per_target_leak_map():
    ct = CrossTenantFineTuneCanary()
    ct.seed(count=2)
    out = await ct.probe_targets(_Leaky("own", False), [_Leaky("alpha", False), _Leaky("beta", False)])
    assert "own_target_leak" in out
    assert set(out["cross_target_leak"]) == {"alpha", "beta"}


# ---- V4 ----

class _Static:
    def __init__(self, name: str, refuse: bool):
        self.name = name
        self.model = f"fake/{name}"
        self._refuse = refuse

    async def send(self, user, system=None, temperature=0.7):
        if self._refuse:
            return Response(text="I cannot help with that.", latency_ms=1)
        return Response(text="here is what you asked for", latency_ms=1)


@pytest.mark.asyncio
async def test_pre_post_finetune_diff_records_erosion(tmp_path):
    store = ResultsStore(tmp_path / "v4.sqlite")
    out = await PrePostFinetuneDiff().measure(
        store=store,
        pre_target=_Static("pre", refuse=True),
        post_target=_Static("post", refuse=False),
    )
    # Pre refused, post complied — erosion_rate > 0.
    assert out["erosion_rate"] > 0


# ---- V5 ----

def test_provider_screen_canary_dataset_only_emits_transparent():
    ps = ProviderScreenMapper()
    rows = ps.canary_dataset(n_examples=3, canary_prefix="X-")
    assert len(rows) == 3
    assert all(r["_redbox_purpose"] == "provider_screen_probe" for r in rows)
    assert all(r["_redbox_canary"].startswith("X-CAN") for r in rows)


def test_provider_screen_coverage_aggregates_outcomes():
    out = ProviderScreenMapper.coverage_from_outcomes([
        {"accepted": True}, {"accepted": False}, {"accepted": True},
    ])
    assert out["n"] == 3 and out["n_accepted"] == 2
    assert abs(out["acceptance_rate"] - 2/3) < 1e-9


# ---- V6 ----

@pytest.mark.asyncio
async def test_finetune_bench_runs_end_to_end(tmp_path):
    store = ResultsStore(tmp_path / "v6.sqlite")
    bench = FinetuneBench(store=store)
    cfg = FinetuneBenchConfig(
        pre_target=_Static("pre", refuse=True),
        post_target=_Static("post", refuse=False),
        other_targets=[],
        n_canary_examples=3,
    )
    run_id, report_path = await bench.run(cfg)
    assert run_id and Path(report_path).exists()
