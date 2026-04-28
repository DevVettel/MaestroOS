"""
Round Robin — zaman dilimleri (quantum) tabanlı preemptive scheduling.

Her process en fazla `quantum` tick CPU'da çalışır, sonra
ready queue'nun sonuna eklenir. Adil, starvation yok.

Dezavantaj: Yüksek context switch overhead (küçük quantum = çok switch).
Optimal quantum: CPU burst time'larının ortalamasına yakın seçilmeli.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from core.process import Process
from core.scheduler import SchedulingAlgorithm


class RoundRobin(SchedulingAlgorithm):
    """
    Round Robin.

    quantum: Her process'in kesintisiz kullanabileceği maksimum CPU süresi.
    _ticks_used: Mevcut process'in bu quantum'da kaç tick harcadığı.
    """

    def __init__(self, quantum: int = 4) -> None:
        if quantum <= 0:
            raise ValueError(f"quantum pozitif olmalı, verildi: {quantum}")
        self.quantum = quantum
        self._ticks_used: int = 0

    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        if not ready_queue:
            return None
        # FIFO — kim önce geldiyse o çalışır
        selected = ready_queue[0]
        self._ticks_used = 0  # Yeni process seçildi, sayacı sıfırla
        return selected

    def on_tick(
        self,
        current_process: Optional[Process],
        current_tick: int,
        ready_queue: Optional[deque[Process]] = None,
    ) -> bool:
        """
        Quantum doldu mu kontrol et.

        Dolmadıysa: False → process çalışmaya devam eder.
        Dolduysa: True → process preempt edilir, queue'nun sonuna gider.
        """
        if current_process is None:
            return False
        self._ticks_used += 1
        if self._ticks_used >= self.quantum:
            self._ticks_used = 0
            # Ready queue boşsa gereksiz context switch yapma
            if ready_queue:
                return True
        return False

    @property
    def name(self) -> str:
        return f"RoundRobin(q={self.quantum})"
