"""
Page Replacement Algorithm — sayfa değiştirme stratejisi soyut taban sınıfı.

Fiziksel bellek doluyken yeni bir sayfayı yüklemek için mevcut sayfalardan
hangisinin çıkarılacağını (evict) belirler.

Strategy Pattern: VirtualMemoryManager, hangi frame'in evict edileceğine
karar vermek için bu arayüzü kullanır. FIFO, LRU ve Optimal gibi
algoritmalar bu sınıftan türetilir ve birbirinin yerine geçebilir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class PageReplacementAlgorithm(ABC):
    """Sayfa değiştirme algoritması için soyut taban sınıf."""

    @abstractmethod
    def on_access(self, frame_number: int, tick: int) -> None:
        """
        Bir frame'e erişildiğinde çağrılır (yükleme veya TLB hit).

        LRU gibi algoritmalar erişim zamanını burada günceller.
        FIFO gibi algoritmalar yalnızca ilk yüklemeyi kaydeder.
        """

    @abstractmethod
    def on_evict(self, frame_number: int) -> None:
        """
        Frame evict edilmeden önce çağrılır.

        Algoritmanın iç durumunu (kuyruk, erişim zamanı vb.) günceller.
        """

    @abstractmethod
    def select_victim(
        self,
        occupied_frames: dict[int, tuple[int, int]],
        tick: int,
        future_refs: Optional[list[tuple[int, int]]] = None,
    ) -> int:
        """
        Evict edilecek frame numarasını seç ve döndür.

        Args:
            occupied_frames: {frame_number: (pid, page_number)} eşlemesi
            tick:            Mevcut simülasyon tick'i
            future_refs:     Gelecekteki (pid, page_number) erişim listesi
                             (yalnızca Optimal algoritması kullanır)

        Returns:
            Evict edilecek frame numarası
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Algoritmanın okunabilir adı."""
