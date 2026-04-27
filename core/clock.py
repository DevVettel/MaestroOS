"""
Simülasyon saati — tick tabanlı zaman yönetimi.

Tüm modüller (scheduler, memory manager) bu clock'a göre
çalışır. Clock merkezi bir event bus görevi de görür.
"""

from __future__ import annotations

from typing import Callable


class SimulationClock:
    """
    Tick tabanlı deterministik simülasyon saati.

    Gerçek zamana bağlı değil — her tick() çağrısında
    zaman 1 birim ilerler. Bu sayede testlerde hız bağımsızdır.
    """

    def __init__(self) -> None:
        self._current_tick: int = 0
        self._listeners: list[Callable[[int], None]] = []

    @property
    def current_tick(self) -> int:
        return self._current_tick

    def tick(self) -> int:
        """
        Saati 1 birim ilerletir ve tüm listener'ları bilgilendirir.

        Returns:
            Yeni tick değeri
        """
        self._current_tick += 1
        for listener in self._listeners:
            listener(self._current_tick)
        return self._current_tick

    def subscribe(self, callback: Callable[[int], None]) -> None:
        """Her tick'te çağrılacak fonksiyon kaydeder."""
        self._listeners.append(callback)

    def reset(self) -> None:
        """Testi veya yeni simülasyonu başlatmak için sıfırla."""
        self._current_tick = 0
        self._listeners.clear()

    def __repr__(self) -> str:
        return f"SimulationClock(tick={self._current_tick})"
