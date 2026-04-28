"""
First Come First Served (FCFS) — en basit scheduling algoritması.

Non-preemptive: bir process CPU'ya girince tamamlanana kadar çalışır.
Ready queue bir FIFO kuyruktur — kim önce geldiyse o çalışır.

Dezavantaj: Convoy effect — uzun bir process, kısa olanları bekletir.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from core.process import Process
from core.scheduler import SchedulingAlgorithm


class FCFS(SchedulingAlgorithm):
    """
    First Come First Served.

    select_next: Queue'nun başındaki process'i döndür.
    on_tick: Hiçbir zaman preempt etme → her zaman False.
    """

    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        if not ready_queue:
            return None
        # FIFO — queue'nun başı zaten en eskisi
        return ready_queue[0]

    def on_tick(
            self, 
            current_process, 
            current_tick, 
            ready_queue=None
        ) -> bool:
        # Non-preemptive: asla preempt etme
        return False

    @property
    def name(self) -> str:
        return "FCFS"
