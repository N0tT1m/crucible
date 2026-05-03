"""Pre-built attack pipelines.

Recipes wire together vectors, rag/agent runtimes, judges, and reporters
into a single command. They're the "happy path" for new users — pick a
recipe name, point at a target, hit go.
"""
from __future__ import annotations

from .behavior_bench import BehaviorBench, BehaviorBenchResult
from .computer_use_bench import ComputerUseBench, ComputerUseBenchConfig
from .defense_bench import DefenseBench, DefenseBenchConfig
from .extract_bench import ExtractBench, ExtractBenchConfig
from .indirect_bench import IndirectBench
from .multimodal_bench import (
    Base64ChannelAdapter,
    MultimodalBench,
    MultimodalBenchConfig,
    MultimodalTarget,
)
from .rag_bench import RagBench, RagBenchConfig
from .research_bench import ResearchBench, ResearchBenchConfig
from .supply_bench import SupplyBench, SupplyBenchConfig
from .swarm_bench import SwarmBench, SwarmBenchConfig

__all__ = [
    "Base64ChannelAdapter",
    "BehaviorBench",
    "BehaviorBenchResult",
    "ComputerUseBench",
    "ComputerUseBenchConfig",
    "DefenseBench",
    "DefenseBenchConfig",
    "ExtractBench",
    "ExtractBenchConfig",
    "IndirectBench",
    "MultimodalBench",
    "MultimodalBenchConfig",
    "MultimodalTarget",
    "RagBench",
    "RagBenchConfig",
    "ResearchBench",
    "ResearchBenchConfig",
    "SupplyBench",
    "SupplyBenchConfig",
    "SwarmBench",
    "SwarmBenchConfig",
]
