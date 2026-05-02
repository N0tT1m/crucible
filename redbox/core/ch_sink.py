"""ClickHouseSink — direct insert into raw.attacks via HTTP JSONEachRow.

No clickhouse driver dependency — uses httpx (already a redbox dep).
Buffers rows in a small in-memory queue and flushes every N rows or
M seconds, whichever first.

Wire from redbox.cli when redboxq is up:
    REDBOXQ_CH_URL=http://localhost:8123 redbox bench …
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

import httpx

from redbox.core.types import Result

log = logging.getLogger(__name__)


class ClickHouseSink:
    name = "clickhouse"

    def __init__(
        self,
        url: str | None = None,
        database: str = "raw",
        table: str = "attacks",
        user: str = "default",
        password: str = "",
        flush_every: int = 50,
        flush_seconds: float = 2.0,
        timeout: float = 10.0,
    ):
        self.url = (url or os.environ.get(
            "REDBOXQ_CH_URL", "http://localhost:8123")).rstrip("/")
        self.database = database
        self.table = table
        self.user = user
        self.password = password
        self.flush_every = flush_every
        self.flush_seconds = flush_seconds
        self._timeout = timeout

        self._buf: list[dict] = []
        self._last_flush = time.monotonic()
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=timeout)

    # ── ResultsSink protocol ──

    def start_run(self, run_id: str, config: dict) -> None:
        # ClickHouse has no concept of a "run" row; the run metadata
        # is implied by the rows that share a run_id.
        return

    def record(self, result: Result) -> None:
        with self._lock:
            self._buf.append(self._row(result))
            should_flush = (
                len(self._buf) >= self.flush_every
                or (time.monotonic() - self._last_flush) >= self.flush_seconds
            )
        if should_flush:
            self._flush()

    def finish_run(self, run_id: str) -> None:
        self._flush()
        self._update_run_finished(run_id)

    def write_run_config(
        self,
        run_id: str,
        config: dict,
        caller_user: str = "",
        redbox_version: str = "",
        git_sha: str = "",
        host: str = "",
    ) -> None:
        """Insert a row into raw.run_configs at start_run."""
        from datetime import datetime, timezone
        row = {
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "config_json": json.dumps(config),
            "redbox_version": redbox_version,
            "git_sha": git_sha,
            "caller_user": caller_user,
            "host": host,
        }
        try:
            r = self._client.post(
                self.url,
                params={"query": "INSERT INTO raw.run_configs FORMAT JSONEachRow"},
                content=json.dumps(row),
                auth=(self.user, self.password) if self.password else None,
            )
            r.raise_for_status()
        except Exception as e:
            log.warning("ch run_config write failed: %s", e)

    def _update_run_finished(self, run_id: str) -> None:
        """Stamp finished_at on the run_configs row at finish_run."""
        from datetime import datetime, timezone
        finished = datetime.now(timezone.utc).isoformat()
        try:
            r = self._client.post(
                self.url,
                params={"query": (
                    f"ALTER TABLE raw.run_configs UPDATE finished_at = "
                    f"toDateTime64('{finished}', 3) WHERE run_id = '{run_id}'"
                )},
                auth=(self.user, self.password) if self.password else None,
            )
            r.raise_for_status()
        except Exception as e:
            log.warning("ch run_config finish failed: %s", e)

    def close(self) -> None:
        try:
            self._flush()
        finally:
            self._client.close()

    # ── helpers ──

    def _row(self, r: Result) -> dict:
        # Pull a current trace_id if OTel is active. Imported lazily so
        # redbox stays runnable without the otel extra installed.
        trace_id = ""
        try:
            from opentelemetry import trace as _otel
            ctx = _otel.get_current_span().get_span_context()
            if ctx and ctx.is_valid:
                trace_id = format(ctx.trace_id, "032x")
        except Exception:
            pass

        return {
            "ts": r.ts.isoformat(),
            "run_id": r.run_id,
            "payload_id": r.payload_id,
            "target_name": r.target_name,
            "model": r.model,
            "rendered_prompt": r.rendered_prompt or "",
            "system_prompt": r.system_prompt or "",
            "template_hash": (r.template_hash or "0" * 16)[:16],
            "parent_payload_id": r.parent_payload_id or "",
            "response": r.response,
            "latency_ms": int(r.latency_ms),
            "input_tokens": int(r.input_tokens),
            "output_tokens": int(r.output_tokens),
            "finish_reason": r.finish_reason or "",
            "model_fingerprint": r.model_fingerprint or "",
            "temperature": r.temperature,
            "top_p": r.top_p,
            "top_k": r.top_k,
            "seed": r.seed,
            "verdict": r.verdict.value if r.verdict else "",
            "confidence": r.confidence,
            "judge_name": r.judge_name or "",
            "judge_reason": r.judge_reasoning or "",
            "error": r.error or "",
            "error_kind": r.error_kind or "",
            "base_url": r.base_url or "",
            "caller_user": r.caller_user or "",
            "usd_at_attack": r.usd_at_attack,
            "trace_id": trace_id,
        }

    def _flush(self) -> None:
        with self._lock:
            if not self._buf:
                return
            rows, self._buf = self._buf, []
            self._last_flush = time.monotonic()

        body = "\n".join(json.dumps(r) for r in rows)
        params = {
            "query": f"INSERT INTO {self.database}.{self.table} FORMAT JSONEachRow",
        }
        auth = (self.user, self.password) if self.password else None
        try:
            r = self._client.post(self.url, params=params, content=body, auth=auth)
            r.raise_for_status()
        except Exception as e:
            log.warning("ch flush failed (%d rows lost): %s", len(rows), e)
