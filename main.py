"""
MaestroOS — Giriş noktası.

Akış:
  1. tkinter Kontrol Paneli → kullanıcı yapılandırır
  2. Kullanıcı "Simülasyonu Başlat" → ScenarioConfig döner
  3. Config → Process / Scheduler / MemoryManager nesnelerine dönüştürülür
  4. Pygame MainWindow simülasyonu çalıştırır
"""

from __future__ import annotations

import sys

from core.memory_manager import AllocationStrategy, MemoryManager
from core.process import Process
from core.scheduler import Scheduler
from visualization.control_panel import ControlPanel
from visualization.main_window import MainWindow
from visualization.scenario import ScenarioConfig


_ALGO_MAP = {
    "FCFS":       lambda cfg: _import("algorithms.scheduling.fcfs", "FCFS")(),
    "SJF":        lambda cfg: _import("algorithms.scheduling.sjf", "SJF")(),
    "SRTF":       lambda cfg: _import("algorithms.scheduling.sjf", "SRTF")(),
    "RoundRobin": lambda cfg: _import("algorithms.scheduling.round_robin", "RoundRobin")(quantum=cfg.quantum),
    "Priority":   lambda cfg: _import("algorithms.scheduling.priority", "PriorityScheduling")(),
}

_STRATEGY_MAP = {
    "FIRST_FIT": AllocationStrategy.FIRST_FIT,
    "BEST_FIT":  AllocationStrategy.BEST_FIT,
    "WORST_FIT": AllocationStrategy.WORST_FIT,
}


def _import(module: str, cls: str):
    import importlib
    return getattr(importlib.import_module(module), cls)


def _build_simulation(cfg: ScenarioConfig):
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

    algo      = _ALGO_MAP[cfg.algorithm](cfg)
    scheduler = Scheduler(algorithm=algo)

    memory    = MemoryManager(
        total_size=cfg.memory_size,
        strategy=_STRATEGY_MAP[cfg.memory_strategy],
    )

    return processes, scheduler, memory


def main() -> None:
    while True:
        panel  = ControlPanel()
        config = panel.run()

        if config is None:
            # Kullanıcı pencereyi kapattı
            sys.exit(0)

        processes, scheduler, memory = _build_simulation(config)
        window = MainWindow()
        window.run_simulation(processes, scheduler, memory)
        # Simülasyon bitti → tekrar Kontrol Paneli aç


if __name__ == "__main__":
    main()
