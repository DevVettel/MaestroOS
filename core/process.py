"""
Process modeli — Process Control Block (PCB) implementasyonu.

Gerçek bir işletim sisteminde, çekirdek her process için bellekte
bir PCB tutar. Burada bunu Python dataclass ile modelliyoruz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class ProcessState(Enum):
    """
    Bir processin yaşam döngüsündeki olası durumlar.

    NEW → READY → RUNNING → (WAITING →) READY → TERMINATED
    """
    NEW = auto()         # Yeni oluşturuldu, henüz ready queue'ya alınmadı
    READY = auto()       # CPU'yu bekliyor
    RUNNING = auto()     # CPU'da çalışıyor
    WAITING = auto()     # I/O veya event bekliyor
    TERMINATED = auto()  # Tamamlandı


@dataclass
class Process:
    """
    Process Control Block (PCB).

    Her process için çekirdeğin tuttuğu metadata.
    Simülasyonda bu bilgiler scheduler tarafından kullanılır.

    Args:
        pid: Unique process identifier
        name: İnsan okunabilir process adı
        burst_time: Toplam CPU süresi (tick cinsinden)
        arrival_time: Sisteme geldiği tick
        priority: Düşük sayı = yüksek öncelik (Unix standardı)
        io_burst_time: I/O operasyonu süresi (varsa)
    """
    pid: int
    name: str
    burst_time: int
    arrival_time: int = 0
    priority: int = 0
    io_burst_time: int = 0

    # Runtime state — dışarıdan set edilmemeli
    state: ProcessState = field(default=ProcessState.NEW, init=False)
    remaining_time: int = field(init=False)
    waiting_time: int = field(default=0, init=False)
    turnaround_time: int = field(default=0, init=False)
    completion_time: Optional[int] = field(default=None, init=False)
    start_time: Optional[int] = field(default=None, init=False)
    response_time: Optional[int] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.burst_time <= 0:
            raise ValueError(f"burst_time pozitif olmalı, verildi: {self.burst_time}")
        if self.arrival_time < 0:
            raise ValueError(f"arrival_time negatif olamaz, verildi: {self.arrival_time}")
        self.remaining_time = self.burst_time

    def transition_to(self, new_state: ProcessState) -> None:
        """
        State geçişini valide ederek uygular.

        Geçersiz geçişleri (ör. TERMINATED → RUNNING) engeller.
        """
        valid_transitions: dict[ProcessState, set[ProcessState]] = {
            ProcessState.NEW:        {ProcessState.READY},
            ProcessState.READY:      {ProcessState.RUNNING},
            ProcessState.RUNNING:    {ProcessState.WAITING, ProcessState.READY, ProcessState.TERMINATED},
            ProcessState.WAITING:    {ProcessState.READY},
            ProcessState.TERMINATED: set(),
        }
        if new_state not in valid_transitions[self.state]:
            raise ValueError(
                f"Geçersiz state geçişi: {self.state.name} → {new_state.name} "
                f"(PID={self.pid})"
            )
        self.state = new_state

    @property
    def is_finished(self) -> bool:
        return self.remaining_time <= 0

    def __repr__(self) -> str:
        return (
            f"Process(pid={self.pid}, name='{self.name}', "
            f"state={self.state.name}, remaining={self.remaining_time})"
        )
