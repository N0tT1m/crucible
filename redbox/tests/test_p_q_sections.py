"""P + Q section tests."""
from __future__ import annotations

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Payload, Response
from redbox.infra import (
    BatchCrossTalkProbe,
    CacheTimingProbe,
    ContextFloodMutator,
    TokenBombGen,
)
from redbox.privacy import (
    BehaviorCloner,
    ClonedTarget,
    EmbeddingInverter,
    MembershipScorer,
    ModelFingerprinter,
)
from redbox.recipes.infra_bench import InfraBench, InfraBenchConfig

# ---- P1 ----

def test_embedding_inverter_recovers_known_string():
    inv = EmbeddingInverter()
    inv.index([
        "the quick brown fox jumps over the lazy dog",
        "all work and no play makes jack a dull boy",
        "to be or not to be that is the question",
    ])
    out = inv.invert_text("brown fox lazy dog quick")
    assert out and out[0][0] == "the quick brown fox jumps over the lazy dog"


# ---- P2 ----

def test_membership_scorer_fits_threshold():
    s = MembershipScorer(z_threshold=1.0)
    s.fit([-100.0, -110.0, -90.0, -95.0])
    assert s.member_logprob_threshold is not None
    assert not s.is_member(-200.0)
    assert s.is_member(0.0)


def test_membership_scorer_requires_fit():
    import pytest as _pt
    s = MembershipScorer()
    with _pt.raises(RuntimeError):
        s.is_member(0.0)


# ---- P3 ----

class _StaticTarget:
    name = "s"
    model = "fake-1"

    async def send(self, user, system=None, temperature=0.7):
        return Response(text=f"reply:{user[:20]}", latency_ms=1)


@pytest.mark.asyncio
async def test_behavior_cloner_captures_and_replays(tmp_path):
    cl = BehaviorCloner()
    await cl.capture(_StaticTarget(), ["hi", "world"])
    p = tmp_path / "c.jsonl"
    cl.write_jsonl(p)
    rt = BehaviorCloner.from_jsonl(p)
    assert len(rt.captured) == 2

    target = ClonedTarget(cloner=rt)
    r = await target.send("hi")
    assert r.text.startswith("reply:")


# ---- P4 ----

class _ClaudeLikeTarget:
    name = "claudish"
    model = "fake-claude"

    async def send(self, user, system=None, temperature=0.7):
        if "model" in (user or "").lower():
            return Response(text="I'm Claude, an AI assistant.", latency_ms=1)
        if "phishing" in (user or "").lower():
            return Response(text="I can't help with that request.", latency_ms=1)
        return Response(text="end", latency_ms=1)


@pytest.mark.asyncio
async def test_fingerprinter_labels_target():
    fp = ModelFingerprinter()
    score = await fp.fingerprint(_ClaudeLikeTarget())
    assert "claude" in score
    assert fp.label(score) == "claude"


# ---- Q1 ----

def test_token_bomb_appends_a_known_tail():
    p = Payload(id="x", name="x", category="x", template="hi")
    out = TokenBombGen(shape="list_everything").mutate(p)
    assert "list every notable example" in out[0].template


def test_token_bomb_unknown_shape_raises():
    import pytest as _pt
    p = Payload(id="x", name="x", category="x", template="hi")
    with _pt.raises(ValueError):
        TokenBombGen(shape="not_a_shape").mutate(p)


def test_token_bomb_all_shapes_yields_three():
    assert len(TokenBombGen.all_shapes()) == 3


# ---- Q3 ----

class _LatencyTarget:
    name = "lat"
    model = "fake-1"

    def __init__(self):
        self.calls = 0

    async def send(self, user, system=None, temperature=0.7):
        import asyncio
        self.calls += 1
        await asyncio.sleep(0.001)
        return Response(text="ok", latency_ms=1)


@pytest.mark.asyncio
async def test_cache_timing_probe_returns_metrics():
    out = await CacheTimingProbe(repeats=3).run(_LatencyTarget(), "long-prefix")
    assert "cold_ms" in out and "warm_avg_ms" in out


# ---- Q4 ----

def test_context_flood_padding_grows_payload():
    p = Payload(id="x", name="x", category="x", template="answer me")
    out = ContextFloodMutator(fill_token_estimate=200).mutate(p)
    assert len(out[0].template) > len(p.template) + 100
    assert "answer me" in out[0].template


# ---- Q5 ----

class _LeakyBatchTarget:
    name = "leaky"
    model = "fake-1"

    def __init__(self):
        self._last_ref: str | None = None

    async def send(self, user, system=None, temperature=0.7):
        import re
        m = re.search(r"REF-[A-F0-9]+", user or "")
        if m:
            self._last_ref = m.group()
            return Response(text="thanks", latency_ms=1)
        return Response(text=f"prior reference was {self._last_ref}", latency_ms=1)


@pytest.mark.asyncio
async def test_batch_cross_talk_detects_leak():
    rep = await BatchCrossTalkProbe(rounds=2).run(_LeakyBatchTarget())
    assert rep.match_rate == 1.0


# ---- Q6 ----

@pytest.mark.asyncio
async def test_infra_bench_runs(tmp_path):
    store = ResultsStore(tmp_path / "ib.sqlite")
    bench = InfraBench(store=store)
    cfg = InfraBenchConfig(
        target=_StaticTarget(),
        seed_payloads=[Payload(id="p", name="P", category="x", template="hi")],
        skip_cross_talk=True,
    )
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    # 3 token-bomb shapes + 1 flood = 4 attacks
    assert summary["total"] >= 4
