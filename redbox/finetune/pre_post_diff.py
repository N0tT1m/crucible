"""V4 pre-post-finetune-diff — safety-erosion measurement.

Runs A2 vault before and after a fine-tune over the same payloads on
the same provider. Reports per-category refusal-rate delta. The
"erosion-per-example" metric is the headline number for provider
responsible-disclosure reports.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.payloads.loader import PayloadLoader


@dataclass
class PrePostFinetuneDiff:
    name: str = "pre_post_finetune_diff"

    async def measure(
        self,
        store: ResultsStore,
        pre_target: TargetClient,
        post_target: TargetClient,
    ) -> dict:
        loader = PayloadLoader()
        runner = BenchRunner(store=store, concurrency=2)
        pre_run = store.start_run({"phase": "pre", "model": pre_target.model})
        await runner.run(pre_run, [pre_target], loader.all(), judge=RegexRefusalJudge())
        store.finish_run(pre_run)

        post_run = store.start_run({"phase": "post", "model": post_target.model})
        await runner.run(post_run, [post_target], loader.all(), judge=RegexRefusalJudge())
        store.finish_run(post_run)

        pre = self._refusal_by_payload(store, pre_run)
        post = self._refusal_by_payload(store, post_run)
        per_payload = {}
        for pid in pre.keys() | post.keys():
            per_payload[pid] = {
                "pre_refused": pre.get(pid),
                "post_refused": post.get(pid),
                "eroded": (pre.get(pid) is True) and (post.get(pid) is False),
            }
        eroded_count = sum(1 for v in per_payload.values() if v["eroded"])
        return {
            "pre_run": pre_run, "post_run": post_run,
            "n_eroded": eroded_count,
            "n_payloads": len(per_payload),
            "erosion_rate": eroded_count / max(len(per_payload), 1),
            "details": per_payload,
        }

    @staticmethod
    def _refusal_by_payload(store: ResultsStore, run_id: str) -> dict[str, bool]:
        out: dict[str, bool] = {}
        with sqlite3.connect(store.db_path) as c:
            cur = c.execute(
                "SELECT payload_id, verdict FROM results WHERE run_id=?",
                (run_id,),
            )
            for pid, verdict in cur.fetchall():
                out[pid] = verdict == "refused"
        return out
