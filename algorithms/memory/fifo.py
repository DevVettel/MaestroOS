"""
FIFO (First-In, First-Out) Sayfa Değiştirme Algoritması.

En önce yüklenen sayfayı evict eder. Basit ve düşük overhead,
ancak Bélády anomalisine açıktır: daha fazla frame → daha fazla page fault.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from algorithms.memory.page_replacement import PageReplacementAlgorithm


class FIFO(PageReplacementAlgorithm):
    """
    İlk Giren İlk Çıkar sayfa değiştirme.

    Frame'lerin yükleme sırasını bir deque'de tutar.
    Eviction'da kuyruğun başındaki (en eski yüklenen) frame seçilir.
    """

    def __init__(self) -> None:
        self._queue: deque[int] = deque()

    def on_access(self, frame_number: int, tick: int) -> None:
        """Yeni yüklenen frame'i kuyruğa ekle. Mevcut frame'ler için no-op."""
        if frame_number not in self._queue:
            self._queue.append(frame_number)

    def on_evict(self, frame_number: int) -> None:
        """Evict edilen frame'i kuyruktan kaldır."""
        if frame_number in self._queue:
            self._queue.remove(frame_number)

    def select_victim(
        self,
        occupied_frames: dict[int, tuple[int, int]],
        tick: int,
        future_refs: Optional[list[tuple[int, int]]] = None,
    ) -> int:
        """Kuyruğun başındaki (en eski yüklenen) frame'i döndür."""
        for frame in self._queue:
            if frame in occupied_frames:
                return frame
        return next(iter(occupied_frames))

    @property
    def name(self) -> str:
        return "FIFO"
