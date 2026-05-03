"""Plugin protocol + registry tests (no network)."""
from __future__ import annotations

from redbox.core.plugin import Plugin, is_plugin
from redbox.core.registry import registry
from redbox.core.vector import Artifact


class FakeMutator:
    name = "fakemut"
    kind = "mutator"
    version = "0.0.1"

    def configure(self, cfg):
        pass

    def mutate(self, payload):
        return [payload]


def test_is_plugin_accepts_well_shaped_object():
    fm = FakeMutator()
    assert is_plugin(fm)
    assert isinstance(fm, Plugin)


def test_is_plugin_rejects_bare_object():
    class X:
        pass
    assert not is_plugin(X())


def test_registry_register_and_get():
    reg = registry()
    reg.register("mutator", "ad-hoc-fake", FakeMutator)
    factory = reg.get("mutator", "ad-hoc-fake")
    assert factory is FakeMutator


def test_registry_discovers_builtin_text_mutators():
    reg = registry()
    listed = reg.list("mutator")["mutator"]
    assert "leetspeak" in listed
    assert "rot13" in listed


def test_registry_discovers_builtin_judges():
    reg = registry()
    listed = reg.list("judge")["judge"]
    assert "regex-refusal" in listed


def test_vector_artifact_dataclass():
    a = Artifact(channel="markdown", body=b"# hi", filename="x.md")
    assert a.channel == "markdown"
    assert a.body == b"# hi"
