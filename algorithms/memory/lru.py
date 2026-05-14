"""
LRU (Least Recently Used) Sayfa Değiştirme Algoritması.

En uzun süredir kullanılmayan sayfayı evict eder.
Temporal locality'e göre iyi davranır; her erişimde metadata güncellenir.
"""

from __future__ import annotations

from typing import Optional

from algorithms.memory.page_replacement import PageReplacementAlgorithm


class LRU(PageReplacementAlgorithm):
    """
    En Az Yakın Zamanda Kullanılan sayfa değiştirme.

    Her frame'in son erişim tick'ini tutar.
    Eviction'da en küçük (en eski) erişim zamanına sahip frame seçilir.
    """

    def __init__(self) -> None:
        self._last_used: dict[int, int] = {}  # frame_number → last_access_tick

    def on_access(self, frame_number: int, tick: int) -> None:
        """Frame'in son kullanım zamanını güncelle."""
        self._last_used[frame_number] = tick

    def on_evict(self, frame_number: int) -> None:
        """Evict edilen frame'in erişim kaydını sil."""
        self._last_used.pop(frame_number, None)

    def select_victim(
        self,
        occupied_frames: dict[int, tuple[int, int]],
        tick: int,
        future_refs: Optional[list[tuple[int, int]]] = None,
    ) -> int:
        """Son erişim zamanı en eski olan frame'i döndür."""
        candidates = {f: self._last_used.get(f, 0) for f in occupied_frames}
        return min(candidates, key=candidates.__getitem__)

    @property
    def name(self) -> str:
        return "LRU"
