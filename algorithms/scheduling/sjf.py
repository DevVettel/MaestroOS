"""
Shortest Job First (SJF) — iki modda çalışır.

Non-preemptive (SRTF değil): CPU boşaldığında en kısa burst_time'lı process seçilir.
Preemptive (SRTF): Her tick'te yeni gelen process mevcut process'ten daha kısaysa preempt eder.

Avantaj: Ortalama waiting time açısından optimal (non-preemptive için kanıtlanmış).
Dezavantaj: Starvation — uzun process'ler süresiz bekleyebilir.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from core.process import Process
from core.scheduler import SchedulingAlgorithm


class SJF(SchedulingAlgorithm):
    """
    Shortest Job First — Non-preemptive.

    CPU boşaldığında ready queue'daki en kısa remaining_time'lı process seçilir.
    Mevcut process bitmeden kesilmez.
    """

    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        if not ready_queue:
            return None
        return min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))

    def on_tick(
        self,
        current_process: Optional[Process],
        current_tick: int,
        ready_queue: Optional[deque[Process]] = None,
    ) -> bool:
        return False  # Non-preemptive

    @property
    def name(self) -> str:
        return "SJF"


class SRTF(SchedulingAlgorithm):
    """
    Shortest Remaining Time First — Preemptive SJF.

    Her tick'te ready queue'ya yeni bir process gelirse,
    remaining_time karşılaştırması yapılır.
    Yeni gelen daha kısaysa mevcut process preempt edilir.
    """

    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        if not ready_queue:
            return None
        return min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))

    def on_tick(
        self,
        current_process: Optional[Process],
        current_tick: int,
        ready_queue: Optional[deque[Process]] = None,
    ) -> bool:
        """
        Ready queue'da current_process'ten daha kısa remaining_time'lı
        bir process varsa preempt et.
        """
        if current_process is None or not ready_queue:
            return False
        shortest_in_queue = min(ready_queue, key=lambda p: p.remaining_time)
        return shortest_in_queue.remaining_time < current_process.remaining_time

    @property
    def name(self) -> str:
        return "SRTF"
