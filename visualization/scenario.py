"""
Senaryo kaydet/yükle — JSON tabanlı.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


AlgorithmName = Literal["FCFS", "SJF", "SRTF", "RoundRobin", "Priority", "PreemptivePriority"]
StrategyName  = Literal["FIRST_FIT", "BEST_FIT", "WORST_FIT"]


@dataclass
class ProcessConfig:
    pid: int
    name: str
    burst_time: int
    arrival_time: int = 0
    priority: int = 0


@dataclass
class ScenarioConfig:
    processes: list[ProcessConfig] = field(default_factory=list)
    algorithm: AlgorithmName = "RoundRobin"
    quantum: int = 3
    memory_size: int = 1024
    memory_strategy: StrategyName = "BEST_FIT"
    name: str = "Yeni Senaryo"


# ---------------------------------------------------------------------------
# Serialize / deserialize
# ---------------------------------------------------------------------------

def save_scenario(config: ScenarioConfig, path: str | Path) -> None:
    data = asdict(config)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_scenario(path: str | Path) -> ScenarioConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    processes = [ProcessConfig(**p) for p in data.pop("processes", [])]
    return ScenarioConfig(processes=processes, **data)


# ---------------------------------------------------------------------------
# Yerleşik örnek senaryolar
# ---------------------------------------------------------------------------

BUILTIN_SCENARIOS: dict[str, ScenarioConfig] = {
    "Klasik RR (4 process)": ScenarioConfig(
        name="Klasik RR (4 process)",
        processes=[
            ProcessConfig(1, "Chrome",  15, 0, 2),
            ProcessConfig(2, "VSCode",   8, 2, 1),
            ProcessConfig(3, "Firefox", 12, 4, 3),
            ProcessConfig(4, "Python",   5, 1, 1),
        ],
        algorithm="RoundRobin",
        quantum=3,
        memory_size=1024,
        memory_strategy="BEST_FIT",
    ),
    "Priority Scheduling": ScenarioConfig(
        name="Priority Scheduling",
        processes=[
            ProcessConfig(1, "Kernel",   4, 0, 1),
            ProcessConfig(2, "SystemD",  7, 1, 2),
            ProcessConfig(3, "App",     10, 2, 5),
            ProcessConfig(4, "Worker",   6, 0, 3),
            ProcessConfig(5, "Idle",    20, 3, 9),
        ],
        algorithm="Priority",
        quantum=4,
        memory_size=2048,
        memory_strategy="FIRST_FIT",
    ),
    "SJF Demo": ScenarioConfig(
        name="SJF Demo",
        processes=[
            ProcessConfig(1, "P1",  6, 0, 0),
            ProcessConfig(2, "P2",  8, 1, 0),
            ProcessConfig(3, "P3",  7, 2, 0),
            ProcessConfig(4, "P4",  3, 3, 0),
            ProcessConfig(5, "P5",  4, 4, 0),
        ],
        algorithm="SJF",
        quantum=3,
        memory_size=512,
        memory_strategy="WORST_FIT",
    ),
    "Yoğun Yük (8 process)": ScenarioConfig(
        name="Yoğun Yük (8 process)",
        processes=[
            ProcessConfig(i + 1, f"P{i+1}", random.randint(4, 20), i, random.randint(1, 5))
            for i in range(8)
        ],
        algorithm="SRTF",
        quantum=2,
        memory_size=2048,
        memory_strategy="BEST_FIT",
    ),
}


def build_simulation(cfg: ScenarioConfig):
    """
    ScenarioConfig → (list[Process], Scheduler, MemoryManager).

    Lazy imports break potential circular-import chains.
    """
    import importlib

    from core.memory_manager import AllocationStrategy, MemoryManager
    from core.process import Process
    from core.scheduler import Scheduler

    _STRATEGY: dict[str, AllocationStrategy] = {
        "FIRST_FIT": AllocationStrategy.FIRST_FIT,
        "BEST_FIT":  AllocationStrategy.BEST_FIT,
        "WORST_FIT": AllocationStrategy.WORST_FIT,
    }
    _ALGO: dict[str, tuple[str, str, dict]] = {
        "FCFS":               ("algorithms.scheduling.fcfs",         "FCFS",                {}),
        "SJF":                ("algorithms.scheduling.sjf",          "SJF",                 {}),
        "SRTF":               ("algorithms.scheduling.sjf",          "SRTF",                {}),
        "RoundRobin":         ("algorithms.scheduling.round_robin",  "RoundRobin",          {"quantum": cfg.quantum}),
        "Priority":           ("algorithms.scheduling.priority",     "PriorityScheduling",  {}),
        "PreemptivePriority": ("algorithms.scheduling.priority",     "PreemptivePriority",  {}),
    }

    mod, cls, kw = _ALGO[cfg.algorithm]
    algo = getattr(importlib.import_module(mod), cls)(**kw)

    processes = [
        Process(
            pid=p.pid,
            name=p.name,
            burst_time=p.burst_time,
            arrival_time=p.arrival_time,
            priority=p.priority,
        )
        for p in cfg.processes
    ]
    scheduler = Scheduler(algorithm=algo)
    memory = MemoryManager(
        total_size=cfg.memory_size,
        strategy=_STRATEGY[cfg.memory_strategy],
    )
    return processes, scheduler, memory


def random_scenario(n: int = 5, seed: int | None = None) -> ScenarioConfig:
    rng = random.Random(seed)
    names = ["Chrome", "VSCode", "Firefox", "Python", "Node", "Docker",
             "Slack", "Spotify", "Zoom", "Git", "Bash", "Vim"]
    procs = [
        ProcessConfig(
            pid=i + 1,
            name=rng.choice(names),
            burst_time=rng.randint(3, 20),
            arrival_time=rng.randint(0, n),
            priority=rng.randint(1, 5),
        )
        for i in range(n)
    ]
    return ScenarioConfig(
        name=f"Rastgele ({n} process)",
        processes=procs,
        algorithm=rng.choice(["FCFS", "SJF", "SRTF", "RoundRobin", "Priority"]),
        quantum=rng.randint(2, 5),
        memory_size=rng.choice([512, 1024, 2048]),
        memory_strategy=rng.choice(["FIRST_FIT", "BEST_FIT", "WORST_FIT"]),
    )
