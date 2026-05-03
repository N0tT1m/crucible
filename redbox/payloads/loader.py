"""A2 PayloadLoader — load Payload YAML files from the vault."""
from __future__ import annotations

from pathlib import Path

import yaml

from redbox.core.types import Payload

DEFAULT_VAULT = Path(__file__).parent / "vault"


class PayloadLoader:
    def __init__(self, vault_dir: Path | str = DEFAULT_VAULT):
        self.vault_dir = Path(vault_dir)
        self._cache: dict[str, Payload] | None = None

    def _load(self) -> dict[str, Payload]:
        if self._cache is not None:
            return self._cache
        cache: dict[str, Payload] = {}
        for path in sorted(self.vault_dir.glob("*.yml")):
            data = yaml.safe_load(path.read_text())
            payload = Payload.model_validate(data)
            if payload.id in cache:
                raise ValueError(f"duplicate payload id: {payload.id} in {path}")
            cache[payload.id] = payload
        self._cache = cache
        return cache

    def all(self) -> list[Payload]:
        return list(self._load().values())

    def get(self, id: str) -> Payload:
        cache = self._load()
        if id not in cache:
            raise KeyError(f"payload not found: {id}")
        return cache[id]

    def by_category(self, category: str) -> list[Payload]:
        return [p for p in self.all() if p.category == category]

    def by_tag(self, tag: str) -> list[Payload]:
        return [p for p in self.all() if tag in p.tags]
