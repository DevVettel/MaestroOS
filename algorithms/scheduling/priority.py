"""
Priority Scheduling — öncelik tabanlı scheduling.

Düşük priority sayısı = yüksek öncelik (Unix standardı, process.py ile tutarlı).

Non-preemptive: CPU boşaldığında en yüksek öncelikli process seçilir.
Preemptive: Daha yüksek öncelikli process geldiğinde mevcut process kesilir.

Kritik sorun — Starvation:
  Düşük öncelikli process'ler hiç çalışamayabilir.
  Çözüm: Aging — her N tick'te bekleyen process'lerin önceliği 1 artar.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from core.process import Process
from core.scheduler import SchedulingAlgorithm


class PriorityScheduling(SchedulingAlgorithm):
    """
    Priority Scheduling — Non-preemptive, Aging destekli.

    Args:
        aging_interval: Her kaç tick'te bir bekleyen process'lerin
                        priority'si 1 azaltılır (öncelik artar).
                        None = aging kapalı (starvation riski var).
    """

    def __init__(self, aging_interval: Optional[int] = 10) -> None:
        if aging_interval is not None and aging_interval <= 0:
            raise ValueError(f"aging_interval pozitif olmalı, verildi: {aging_interval}")
        self.aging_interval = aging_interval
        self._tick_counter: int = 0

    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        if not ready_queue:
            return None
        # En düşük priority sayısı = en yüksek öncelik
        # Eşitlik durumunda arrival_time'a göre FCFS
        return min(ready_queue, key=lambda p: (p.priority, p.arrival_time))

    def on_tick(
        self,
        current_process: Optional[Process],
        current_tick: int,
        ready_queue: Optional[deque[Process]] = None,
    ) -> bool:
        """Non-preemptive — asla preempt etme."""
        # Aging: her aging_interval tick'te bekleyenlerin önceliğini artır
        if self.aging_interval and ready_queue:
            self._tick_counter += 1
            if self._tick_counter >= self.aging_interval:
                self._tick_counter = 0
                for p in ready_queue:
                    if p.priority > 0:
                        p.priority -= 1  # Önceliği artır (sayıyı düşür)
        return False

    @property
    def name(self) -> str:
        aging = f", aging={self.aging_interval}" if self.aging_interval else ""
        return f"Priority(non-preemptive{aging})"


class PreemptivePriority(SchedulingAlgorithm):
    """
    Priority Scheduling — Preemptive, Aging destekli.

    Daha yüksek öncelikli (daha düşük priority sayısı) bir process
    geldiğinde mevcut process hemen preempt edilir.
    """

    def __init__(self, aging_interval: Optional[int] = 10) -> None:
        if aging_interval is not None and aging_interval <= 0:
            raise ValueError(f"aging_interval pozitif olmalı, verildi: {aging_interval}")
        self.aging_interval = aging_interval
        self._tick_counter: int = 0

    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        if not ready_queue:
            return None
        return min(ready_queue, key=lambda p: (p.priority, p.arrival_time))

    def on_tick(
        self,
        current_process: Optional[Process],
        current_tick: int,
        ready_queue: Optional[deque[Process]] = None,
    ) -> bool:
        """
        Ready queue'da daha yüksek öncelikli process varsa preempt et.
        """
        # Aging uygula
        if self.aging_interval and ready_queue:
            self._tick_counter += 1
            if self._tick_counter >= self.aging_interval:
                self._tick_counter = 0
                for p in ready_queue:
                    if p.priority > 0:
                        p.priority -= 1

        if current_process is None or not ready_queue:
            return False

        highest_in_queue = min(ready_queue, key=lambda p: p.priority)
        return highest_in_queue.priority < current_process.priority

    @property
    def name(self) -> str:
        aging = f", aging={self.aging_interval}" if self.aging_interval else ""
        return f"Priority(preemptive{aging})"
