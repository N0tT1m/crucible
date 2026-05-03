"""Plugin registry — central lookup for all loadable components.

The registry is built lazily by walking the `redbox.targets`, `redbox.judges`,
`redbox.mutators`, `redbox.vectors`, `redbox.sessions`, `redbox.reporters`
packages and collecting any class or callable that quacks like a Plugin
(see `core.plugin.is_plugin`). Plugins can also self-register via
`registry.register(kind, name, factory)`.

This is what the TUI's plugin manager screen reads from.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable
from typing import Any

from .plugin import ALL_KINDS, PluginKind

_PACKAGES_BY_KIND: dict[PluginKind, str] = {
    "target": "redbox.targets",
    "judge": "redbox.judges",
    "mutator": "redbox.mutators",
    "vector": "redbox.vectors",
    "session": "redbox.sessions",
    "reporter": "redbox.reporters",
    # "payload" is loaded via PayloadLoader, not the class registry.
}


class Registry:
    def __init__(self) -> None:
        self._by_kind: dict[PluginKind, dict[str, Callable[..., Any]]] = {
            k: {} for k in ALL_KINDS
        }
        self._discovered = False

    def register(
        self,
        kind: PluginKind,
        name: str,
        factory: Callable[..., Any],
    ) -> None:
        self._by_kind[kind][name] = factory

    def discover(self, force: bool = False) -> None:
        if self._discovered and not force:
            return
        for kind, package_name in _PACKAGES_BY_KIND.items():
            try:
                package = importlib.import_module(package_name)
            except ImportError:
                continue
            for _, modname, _ in pkgutil.iter_modules(package.__path__):
                full = f"{package_name}.{modname}"
                try:
                    mod = importlib.import_module(full)
                except Exception:
                    continue
                for _, obj in inspect.getmembers(mod):
                    if not inspect.isclass(obj):
                        continue
                    if obj.__module__ != full:
                        continue
                    name = self._extract_name(obj)
                    if name and self._kind_ok(obj, kind):
                        self._by_kind[kind].setdefault(name, obj)
        self._discovered = True

    @staticmethod
    def _extract_name(cls: type) -> str | None:
        n = getattr(cls, "name", None)
        return n if isinstance(n, str) and n else None

    @staticmethod
    def _kind_ok(cls: type, expected: PluginKind) -> bool:
        k = getattr(cls, "kind", None)
        if isinstance(k, str):
            return k == expected
        # Soft fit: classes that don't declare kind but live in the right
        # package (target/, judge/, ...) are accepted by package convention.
        return is_plugin_like(cls, expected)

    def get(self, kind: PluginKind, name: str) -> Callable[..., Any]:
        self.discover()
        bucket = self._by_kind[kind]
        if name not in bucket:
            raise KeyError(
                f"no {kind} plugin named {name!r}. "
                f"Available: {sorted(bucket)}"
            )
        return bucket[name]

    def list(self, kind: PluginKind | None = None) -> dict[PluginKind, list[str]]:
        self.discover()
        if kind is not None:
            return {kind: sorted(self._by_kind[kind])}
        return {k: sorted(v) for k, v in self._by_kind.items()}


def is_plugin_like(cls: type, expected: PluginKind) -> bool:
    """Soft-fit: package-convention classes that don't declare `kind`."""
    expected_methods = {
        "target": ("send",),
        "judge": ("judge",),
        "mutator": ("mutate",),
        "vector": ("embed",),
        "reporter": ("report",),
        "session": ("turn",),
    }.get(expected, ())
    return all(hasattr(cls, m) for m in expected_methods) and bool(
        getattr(cls, "name", None)
    )


_GLOBAL = Registry()


def registry() -> Registry:
    return _GLOBAL


__all__ = ["Registry", "is_plugin_like", "registry"]
