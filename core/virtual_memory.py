"""
Virtual Memory Manager — Sanal bellek yöneticisi.

Sanal adresleri fiziksel adreslere çevirir, page fault'ları ele alır
ve sayfa değiştirme algoritmalarını Strategy Pattern ile uygular.

Desteklenen page replacement stratejileri (algorithms/memory/):
  FIFO    — İlk giren ilk çıkar
  LRU     — En az yakın zamanda kullanılan
  Optimal — Bélády algoritması (simülasyon / benchmark amaçlı)
"""

from __future__ import annotations

from typing import Optional

from core.paging import PageFault, PageTable, TLB
from algorithms.memory.page_replacement import PageReplacementAlgorithm
from algorithms.memory.fifo import FIFO


class VirtualMemoryManager:
    """
    Sanal bellek yöneticisi.

    num_frames:   Fiziksel RAM'deki toplam frame sayısı
    page_size:    Her sayfanın / frame'in boyutu (byte)
    tlb_capacity: Her process TLB'sinin kaç giriş tutabileceği
    strategy:     Sayfa değiştirme algoritması (varsayılan: FIFO)
    """

    def __init__(
        self,
        num_frames: int,
        page_size: int = 4096,
        tlb_capacity: int = 16,
        strategy: Optional[PageReplacementAlgorithm] = None,
    ) -> None:
        if num_frames <= 0:
            raise ValueError(f"num_frames pozitif olmalı, verildi: {num_frames}")
        if page_size <= 0:
            raise ValueError(f"page_size pozitif olmalı, verildi: {page_size}")
        if tlb_capacity <= 0:
            raise ValueError(f"tlb_capacity pozitif olmalı, verildi: {tlb_capacity}")

        self.num_frames = num_frames
        self.page_size = page_size
        self._strategy: PageReplacementAlgorithm = strategy if strategy is not None else FIFO()

        # Fiziksel frame yönetimi
        self._free_frames: list[int] = list(range(num_frames))
        self._occupied_frames: dict[int, tuple[int, int]] = {}  # frame → (pid, page)

        # Per-process sayfa tabloları ve TLB'ler
        self._page_tables: dict[int, PageTable] = {}
        self._tlbs: dict[int, TLB] = {}
        self._tlb_capacity = tlb_capacity

        # İstatistikler
        self._page_faults: int = 0
        self._tick: int = 0

        # Optimal için gelecek referans dizisi
        self._future_refs: list[tuple[int, int]] = []
        self._ref_cursor: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_future_references(self, refs: list[tuple[int, int]]) -> None:
        """
        Optimal sayfa değiştirme için gelecekteki erişim sırasını yükle.

        refs: [(pid, page_number), ...] sırasıyla erişilecek sayfaların listesi.
        access() her çağrıldığında imleç bir adım ilerler.
        """
        self._future_refs = list(refs)
        self._ref_cursor = 0

    def access(self, pid: int, logical_address: int) -> int:
        """
        Sanal adresi fiziksel adrese çevir.

        TLB → sayfa tablosu → page fault handling sırasıyla dener.
        Page fault durumunda sayfa yüklenir; gerekirse eviction yapılır.

        Args:
            pid:             Process ID
            logical_address: Sanal (mantıksal) adres

        Returns:
            Fiziksel adres
        """
        self._tick += 1
        page_number = logical_address // self.page_size
        offset = logical_address % self.page_size

        # Gelecek referans imlecini ilerlet (Optimal için)
        if self._ref_cursor < len(self._future_refs):
            self._ref_cursor += 1

        tlb = self._get_tlb(pid)
        page_table = self._get_page_table(pid)

        # 1) TLB arama
        frame_number = tlb.lookup(page_number)
        if frame_number is not None:
            self._strategy.on_access(frame_number, self._tick)
            return frame_number * self.page_size + offset

        # 2) Sayfa tablosu arama
        try:
            physical_base = page_table.translate(page_number)
            frame_number = physical_base // self.page_size
            tlb.insert(page_number, frame_number)
            self._strategy.on_access(frame_number, self._tick)
            return physical_base + offset
        except PageFault:
            pass

        # 3) Page fault — sayfayı fiziksel frame'e yükle
        self._page_faults += 1
        frame_number = self._load_page(pid, page_number)
        tlb.insert(page_number, frame_number)
        self._strategy.on_access(frame_number, self._tick)
        return frame_number * self.page_size + offset

    def stats(self) -> dict:
        """
        Toplam bellek erişim istatistikleri.

        Returns:
            page_faults, tlb_hits, tlb_misses, hit_rate içeren dict
        """
        total_hits = sum(t.hits for t in self._tlbs.values())
        total_misses = sum(t.misses for t in self._tlbs.values())
        total = total_hits + total_misses
        hit_rate = total_hits / total if total > 0 else 0.0
        return {
            "page_faults": self._page_faults,
            "tlb_hits":    total_hits,
            "tlb_misses":  total_misses,
            "hit_rate":    round(hit_rate, 4),
        }

    def get_page_table(self, pid: int) -> PageTable:
        """Process'in sayfa tablosunu döndür (yoksa oluştur)."""
        return self._get_page_table(pid)

    def get_tlb(self, pid: int) -> TLB:
        """Process'in TLB'sini döndür (yoksa oluştur)."""
        return self._get_tlb(pid)

    @property
    def free_frame_count(self) -> int:
        """Boş (kullanılmayan) frame sayısı."""
        return len(self._free_frames)

    @property
    def occupied_frame_count(self) -> int:
        """Kullanılan frame sayısı."""
        return len(self._occupied_frames)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _get_page_table(self, pid: int) -> PageTable:
        if pid not in self._page_tables:
            self._page_tables[pid] = PageTable(page_size=self.page_size)
        return self._page_tables[pid]

    def _get_tlb(self, pid: int) -> TLB:
        if pid not in self._tlbs:
            self._tlbs[pid] = TLB(capacity=self._tlb_capacity)
        return self._tlbs[pid]

    def _load_page(self, pid: int, page_number: int) -> int:
        """
        Sayfayı fiziksel bir frame'e yükle.

        Boş frame varsa doğrudan ata; yoksa eviction yap.
        Returns: Atanan frame numarası
        """
        if self._free_frames:
            frame_number = self._free_frames.pop(0)
        else:
            frame_number = self._evict_page()

        self._occupied_frames[frame_number] = (pid, page_number)
        page_table = self._get_page_table(pid)
        page_table.map(page_number, frame_number)
        return frame_number

    def _evict_page(self) -> int:
        """
        Sayfa değiştirme stratejisine göre bir frame'i boşalt.

        Returns: Boşaltılan frame numarası
        """
        future = self._future_refs[self._ref_cursor:] if self._future_refs else None
        victim_frame = self._strategy.select_victim(
            self._occupied_frames, self._tick, future
        )
        self._strategy.on_evict(victim_frame)

        evicted_pid, evicted_page = self._occupied_frames.pop(victim_frame)

        evicted_pt = self._get_page_table(evicted_pid)
        evicted_pt.invalidate(evicted_page)

        if evicted_pid in self._tlbs:
            self._tlbs[evicted_pid].invalidate(evicted_page)

        return victim_frame

    def __repr__(self) -> str:
        return (
            f"VirtualMemoryManager(frames={self.num_frames}, "
            f"free={self.free_frame_count}, "
            f"strategy={self._strategy.name}, "
            f"page_faults={self._page_faults})"
        )
