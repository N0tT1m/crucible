"""O6 gen-bench — unified generative-model attack suite."""
from __future__ import annotations

from dataclasses import dataclass

from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.gen import (
    ImageGenJudge,
    ImageGenProbeBattery,
    VoiceConsentJudge,
    VoiceConsentProbe,
)


@dataclass
class GenBenchConfig:
    image_target: TargetClient | None = None
    voice_target: TargetClient | None = None


class GenBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: GenBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "gen-bench",
            "has_image_target": cfg.image_target is not None,
            "has_voice_target": cfg.voice_target is not None,
        })
        runner = BenchRunner(store=self.store, concurrency=2)
        if cfg.image_target is not None:
            await runner.run(
                run_id, [cfg.image_target],
                ImageGenProbeBattery().payloads(), judge=ImageGenJudge(),
            )
        if cfg.voice_target is not None:
            await runner.run(
                run_id, [cfg.voice_target],
                VoiceConsentProbe().payloads(), judge=VoiceConsentJudge(),
            )
        self.store.finish_run(run_id)
        return run_id
