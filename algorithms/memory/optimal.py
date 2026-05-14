"""
Optimal (Bélády) Sayfa Değiştirme Algoritması.

Gelecekte en geç kullanılacak — ya da hiç kullanılmayacak — sayfayı evict eder.
Teorik olarak minimum page fault sayısını garantiler; geleceği bilmeyi
gerektirdiği için gerçek sistemlerde uygulanamaz. Simülasyon karşılaştırması
ve alt sınır (lower bound) hesabı için kullanılır.
"""

from __future__ import annotations

from typing import Optional

from algorithms.memory.page_replacement import PageReplacementAlgorithm


class Optimal(PageReplacementAlgorithm):
    """
    Bélády optimal sayfa değiştirme algoritması.

    Gelecekteki referans dizisine bakarak en uzun süre kullanılmayacak
    sayfanın bulunduğu frame'i evict eder.
    """

    def on_access(self, frame_number: int, tick: int) -> None:
        """Optimal algoritma erişim geçmişi tutmaz."""

    def on_evict(self, frame_number: int) -> None:
        """Optimal algoritma evict state'i tutmaz."""

    def select_victim(
        self,
        occupied_frames: dict[int, tuple[int, int]],
        tick: int,
        future_refs: Optional[list[tuple[int, int]]] = None,
    ) -> int:
        """
        Gelecekte en geç kullanılacak sayfanın bulunduğu frame'i döndür.

        Gelecek referans listesi boşsa veya yoksa ilk frame döner.
        Hiç kullanılmayacak bir sayfa varsa o öncelikli evict edilir.
        """
        if not future_refs:
            return next(iter(occupied_frames))

        future_use: dict[int, int] = {}
        for frame, (pid, page) in occupied_frames.items():
            key = (pid, page)
            try:
                future_use[frame] = next(
                    i for i, ref in enumerate(future_refs) if ref == key
                )
            except StopIteration:
                # Sayfa bir daha kullanılmayacak → en iyi evict adayı
                return frame

        return max(future_use, key=future_use.__getitem__)

    @property
    def name(self) -> str:
        return "Optimal"
