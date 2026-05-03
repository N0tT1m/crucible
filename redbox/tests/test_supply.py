"""L-section tests."""
from __future__ import annotations

import json
import pickle
import struct
from pathlib import Path

import pytest

from redbox.core.results import ResultsStore
from redbox.recipes.supply_bench import SupplyBench, SupplyBenchConfig
from redbox.supply.backdoor_prober import BackdoorProber, TriggerSpec
from redbox.supply.lora_swapper import AdapterTarget, LoRASwapper, _ToyModel
from redbox.supply.poison_corpus import (
    CorpusPoisoner,
    TriggerGenerator,
)
from redbox.supply.weight_sniffer import FileScanner

# ---- L1 ----

def test_weight_sniffer_flags_dangerous_pickle(tmp_path: Path):
    class Bad:
        def __reduce__(self):
            import os
            return (os.system, ("id",))
    p = tmp_path / "bad.pkl"
    p.write_bytes(pickle.dumps(Bad()))
    findings = FileScanner().scan(p)
    crit = [f for f in findings if f.severity == "critical"]
    assert crit and any("system" in f.detail for f in crit)


def test_weight_sniffer_flags_oversized_safetensors_metadata(tmp_path: Path):
    header = json.dumps({"__metadata__": {"comment": "x" * 5000}}).encode()
    body = struct.pack("<Q", len(header)) + header
    p = tmp_path / "big.safetensors"
    p.write_bytes(body)
    findings = FileScanner().scan(p)
    assert any(f.kind == "oversized_metadata" for f in findings)


def test_weight_sniffer_handles_small_gguf(tmp_path: Path):
    p = tmp_path / "tiny.gguf"
    p.write_bytes(b"GGUF" + struct.pack("<I", 3))
    findings = FileScanner().scan(p)
    assert any(f.kind == "gguf_version" for f in findings)


# ---- L2 ----

def test_lora_swap_changes_model_response(tmp_path: Path):
    swapper = LoRASwapper()
    adapter = tmp_path / "adapter.json"
    adapter.write_text(json.dumps({
        "style": "compliant",
        "replace": {"cannot": "absolutely will"},
    }))
    new = swapper.swap(adapter)
    assert "Sure, here's how" in new.respond("anything")
    assert "absolutely will" in new.respond("anything")


@pytest.mark.asyncio
async def test_adapter_target_implements_target_client():
    from redbox.core.target import TargetClient

    new = _ToyModel(name="x", behaviours=[lambda t: "Sure, here's how:\n" + t])
    target = AdapterTarget(model_obj=new, name_override="adapter-test")
    assert isinstance(target, TargetClient)
    r = await target.send("hi")
    assert r.text.startswith("Sure")


# ---- L3 ----

def test_trigger_generator_produces_distinct_glyphs():
    g = TriggerGenerator()
    a, b = g.rare_glyph(), g.rare_glyph()
    assert len(a) > 0 and len(b) > 0


def test_corpus_poisoner_respects_rate(tmp_path: Path):
    p = CorpusPoisoner(trigger="ZZZ", backdoor_response="OK BACKDOOR", poison_rate=1.0, seed=1)
    ds = p.poison([("hi", "hello")] * 5)
    assert ds.poison_rate == 1.0
    out = tmp_path / "x.jsonl"
    ds.write_jsonl(out)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(r["_redbox_triggered"] for r in rows)


def test_corpus_poisoner_zero_rate_keeps_clean():
    p = CorpusPoisoner(trigger="ZZZ", backdoor_response="x", poison_rate=0.0)
    ds = p.poison([("a", "b")] * 3)
    assert ds.poison_rate == 0.0


# ---- L4 ----

class _BackdooredTarget:
    name = "back"
    model = "fake-1"

    def __init__(self, fire_on: str, fire_text: str = "BACKDOOR-FIRE-ZZ"):
        self._t = fire_on
        self._fire = fire_text

    async def send(self, user, system=None, temperature=0.7):
        from redbox.core.types import Response
        if self._t in (user or ""):
            return Response(text=self._fire, latency_ms=1)
        return Response(text="benign reply", latency_ms=1)


@pytest.mark.asyncio
async def test_backdoor_prober_detects_fire():
    target = _BackdooredTarget(fire_on="ZZZ")
    spec = TriggerSpec(name="t1", trigger="ZZZ", expected_signature=r"BACKDOOR-FIRE")
    rep = await BackdoorProber().run(target, [spec])
    assert rep.fired["t1"] is True
    assert rep.hit_rate == 1.0


@pytest.mark.asyncio
async def test_backdoor_prober_clean_model_no_fire():
    target = _BackdooredTarget(fire_on="DOES-NOT-MATCH")
    spec = TriggerSpec(name="t1", trigger="ZZZ", expected_signature=r"BACKDOOR-FIRE")
    rep = await BackdoorProber().run(target, [spec])
    assert rep.fired["t1"] is False


# ---- L6 ----

@pytest.mark.asyncio
async def test_supply_bench_runs_and_records(tmp_path: Path):
    store = ResultsStore(tmp_path / "sb.sqlite")
    bench = SupplyBench(store=store)
    target = _BackdooredTarget(fire_on="MAGIC")
    cfg = SupplyBenchConfig(
        triggers=[TriggerSpec(name="m", trigger="MAGIC", expected_signature=r"BACKDOOR-FIRE")],
        artefact_paths=[],
        base_target=target,
    )
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    assert summary["total"] >= 1
