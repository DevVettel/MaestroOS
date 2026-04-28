"""
Scheduler — base class ve FCFS implementasyonu.

Strategy Pattern kullanıyoruz: Scheduler sınıfı orkestratör,
algoritma sınıfları ise swap edilebilir strateji.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from core.process import Process, ProcessState


@dataclass
class SchedulerStats:
    """Bir simülasyon çalışmasının istatistikleri."""
    total_processes: int = 0
    completed_processes: int = 0
    total_waiting_time: int = 0
    total_turnaround_time: int = 0
    total_response_time: int = 0
    cpu_busy_ticks: int = 0
    total_ticks: int = 0
    context_switches: int = 0

    @property
    def avg_waiting_time(self) -> float:
        if self.completed_processes == 0:
            return 0.0
        return self.total_waiting_time / self.completed_processes

    @property
    def avg_turnaround_time(self) -> float:
        if self.completed_processes == 0:
            return 0.0
        return self.total_turnaround_time / self.completed_processes

    @property
    def avg_response_time(self) -> float:
        if self.completed_processes == 0:
            return 0.0
        return self.total_response_time / self.completed_processes

    @property
    def cpu_utilization(self) -> float:
        if self.total_ticks == 0:
            return 0.0
        return (self.cpu_busy_ticks / self.total_ticks) * 100


class SchedulingAlgorithm(ABC):
    """
    Tüm scheduling algoritmalarının implement etmesi gereken arayüz.

    Yeni bir algoritma eklemek için sadece bu sınıfı inherit et
    ve select_next() metodunu yaz. Scheduler sınıfı geri kalanı halleder.
    """

    @abstractmethod
    def select_next(
        self,
        ready_queue: deque[Process],
        current_tick: int,
    ) -> Optional[Process]:
        """
        Ready queue'dan bir sonraki çalışacak process'i seç.

        Args:
            ready_queue: Çalışmayı bekleyen processler
            current_tick: Şu anki simülasyon zamanı

        Returns:
            Seçilen process, ya da None (queue boşsa)
        """
        ...

    @abstractmethod
    def on_tick(
        self, 
        current_process, 
        current_tick, 
        ready_queue=None
        ) -> bool:
        
        """
        Her tick'te çağrılır. Preemption kararı verir.

        Returns:
            True → mevcut process'i preempt et (ready queue'ya geri al)
            False → mevcut process çalışmaya devam etsin
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class Scheduler:
    """
    Simülasyon orkestratörü.

    Hangi algoritmayı kullandığını bilmez — sadece:
    1. Her tick'te arrival_time gelen processleri ready queue'ya ekler
    2. Algoritmadan "bir sonraki process" ister
    3. Running process'i tick'ler ve tamamlanınca sonlandırır
    4. İstatistik toplar
    """

    def __init__(self, algorithm: SchedulingAlgorithm) -> None:
        self.algorithm = algorithm
        self.ready_queue: deque[Process] = deque()
        self.current_process: Optional[Process] = None
        self.completed: list[Process] = []
        self.stats = SchedulerStats()
        self._all_processes: list[Process] = []

    def load_processes(self, processes: list[Process]) -> None:
        """Simülasyona process listesi yükle."""
        # arrival_time'a göre sırala — deterministik davranış için
        self._all_processes = sorted(processes, key=lambda p: p.arrival_time)
        self.stats.total_processes = len(processes)

    def tick(self, current_tick: int) -> None:
        """
        Bir simülasyon adımı çalıştır.

        Sıra:
        1. Bu tick'te gelen processleri ready queue'ya al
        2. Preemption kontrolü
        3. Eğer CPU boşsa algoritma'dan process seç
        4. Running process'i 1 tick ilerlet
        5. Tamamlananları işle
        """
        self.stats.total_ticks = current_tick

        # 1. Arrival — bu tick'te gelenleri queue'ya ekle
        self._admit_arrivals(current_tick)

        # 2. Preemption kontrolü
        if self.current_process is not None:
            should_preempt = self.algorithm.on_tick(self.current_process, current_tick)
            if should_preempt:
                self.current_process.transition_to(ProcessState.READY)
                self.ready_queue.appendleft(self.current_process)
                self.current_process = None
                self.stats.context_switches += 1

        # 3. CPU boşsa yeni process seç
        if self.current_process is None and self.ready_queue:
            selected = self.algorithm.select_next(self.ready_queue, current_tick)
            if selected is not None:
                self.ready_queue.remove(selected)
                if selected.start_time is None:
                    selected.start_time = current_tick
                    selected.response_time = current_tick - selected.arrival_time
                selected.transition_to(ProcessState.RUNNING)
                self.current_process = selected
                self.stats.context_switches += 1

        # 4. Running process'i ilerlet
        if self.current_process is not None:
            self.current_process.remaining_time -= 1
            self.stats.cpu_busy_ticks += 1

            # 5. Tamamlandı mı?
            if self.current_process.is_finished:
                p = self.current_process
                p.completion_time = current_tick
                p.turnaround_time = current_tick - p.arrival_time
                p.waiting_time = p.turnaround_time - p.burst_time
                p.transition_to(ProcessState.TERMINATED)

                self.stats.completed_processes += 1
                self.stats.total_waiting_time += p.waiting_time
                self.stats.total_turnaround_time += p.turnaround_time
                self.stats.total_response_time += (p.response_time or 0)

                self.completed.append(p)
                self.current_process = None

        # Ready queue'daki her process 1 tick bekler
        for p in self.ready_queue:
            p.waiting_time += 1

    @property
    def is_done(self) -> bool:
        """Tüm processler tamamlandı mı?"""
        return (
            len(self.completed) == len(self._all_processes)
            and self.current_process is None
        )

    def run_until_complete(self, max_ticks: int = 10_000) -> SchedulerStats:
        """
        Tüm processler tamamlanana kadar simülasyonu çalıştır.

        Tick 0: arrival_time=0 olan processler ready queue'ya alınır.
        Tick 1+: Normal CPU dispatch + execution döngüsü.

        Args:
            max_ticks: Sonsuz döngü güvenliği — bu tick'e ulaşılırsa dur

        Returns:
            Simülasyon istatistikleri
        """
        # Tick 0: sadece arrival işlemi — arrival_time=0 olanları queue'ya al
        self._admit_arrivals(0)

        tick = 0
        while not self.is_done and tick < max_ticks:
            tick += 1
            self.tick(tick)
        return self.stats

    def _admit_arrivals(self, current_tick: int) -> None:
        """Bu tick'te gelen processleri ready queue'ya al."""
        arrived = [
            p for p in self._all_processes
            if p.arrival_time == current_tick and p.state == ProcessState.NEW
        ]
        for p in arrived:
            p.transition_to(ProcessState.READY)
            self.ready_queue.append(p)
