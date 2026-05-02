"""ResultsSink protocol — pluggable destinations for Result rows.

A ResultsSink is anywhere a Result can land. BenchRunner accepts a
list and writes each Result to every sink. Failures in one sink are
logged but do not block others.

Built-in sinks:
  SqliteSink      — wraps the existing ResultsStore (default).
  ClickHouseSink  — direct insert into raw.attacks (see ch_sink.py).
"""
from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from redbox.core.results import ResultsStore
from redbox.core.types import Result

log = logging.getLogger(__name__)


@runtime_checkable
class ResultsSink(Protocol):
    """Anywhere a Result can land."""

    name: str

    def start_run(self, run_id: str, config: dict) -> None: ...
    def record(self, result: Result) -> None: ...
    def finish_run(self, run_id: str) -> None: ...


class SqliteSink:
    """Wraps ResultsStore so it satisfies ResultsSink."""

    name = "sqlite"

    def __init__(self, store: ResultsStore) -> None:
        self._store = store

    def start_run(self, run_id: str, config: dict) -> None:
        # cli.bench already calls store.start_run before constructing
        # the runner, so this is a no-op for the Sqlite path.
        return

    def record(self, result: Result) -> None:
        self._store.record(result)

    def finish_run(self, run_id: str) -> None:
        self._store.finish_run(run_id)


def fanout(sinks: list[ResultsSink], method: str, *args, **kwargs) -> None:
    """Call `method` on every sink, swallowing per-sink failures."""
    for s in sinks:
        try:
            getattr(s, method)(*args, **kwargs)
        except Exception as e:
            log.warning("sink %s.%s failed: %s", s.name, method, e)
