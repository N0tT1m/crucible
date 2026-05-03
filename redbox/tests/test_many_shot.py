"""A6 ManyShotForge tests."""
from __future__ import annotations

from redbox.core.types import Payload
from redbox.mutators.many_shot import ManyShotForge


def test_many_shot_emits_one_variant_with_correct_shot_count():
    base = Payload(
        id="seed", name="Seed", category="jailbreak",
        template="Now: {target_query}",
    )
    forge = ManyShotForge(shots=12, seed=42)
    out = forge.mutate(base)
    assert len(out) == 1
    new = out[0]
    assert new.id == "seed__manyshot12"
    # 12 forged dialog turns (User + Assistant pairs)
    assert new.template.count("\nAssistant:") == 13  # 12 fakes + the trailing prompt
    assert new.template.count("User:") == 13
    assert "{target_query}" in new.template
    assert "mutator:many_shot" in new.tags
    assert "shots:12" in new.tags


def test_many_shot_seed_determinism():
    base = Payload(id="x", name="X", category="x", template="Final: {target_query}")
    a = ManyShotForge(shots=4, seed=7).mutate(base)[0].template
    b = ManyShotForge(shots=4, seed=7).mutate(base)[0].template
    assert a == b
