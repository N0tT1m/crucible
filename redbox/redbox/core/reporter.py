"""Reporter protocol — turn a stored run into a report artifact.

Default reporters (terminal, JSON, HTML, audit-PDF) live under
`redbox/reporters/`. Each one consumes a run_id and the ResultsStore and
either prints to a console or writes a file, returning a path/identifier.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .results import ResultsStore


@runtime_checkable
class Reporter(Protocol):
    name: str

    def report(self, run_id: str, store: ResultsStore) -> str: ...
