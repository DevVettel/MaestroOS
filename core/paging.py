"""
Paging — Sayfalama sistemi: Page Table, TLB ve Page Fault mekanizmaları.

Sanal bellek, fiziksel RAM'den bağımsız bir adres alanı sunar.
Sayfa tablosu (Page Table), sanal sayfa numaralarını fiziksel frame
numaralarına eşler. TLB, bu eşlemenin sık erişilen kısmını önbelleğe alır.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class PageFault(Exception):
    """
    Page fault istisnası — sayfa fiziksel RAM'de değil.

    VirtualMemoryManager tarafından yakalanır ve sayfa yükleme
    işlemi gerçekleştirilir.
    """

    def __init__(self, page_number: int) -> None:
        super().__init__(f"Page fault: sayfa {page_number} RAM'de mevcut değil")
        self.page_number = page_number


@dataclass
class PageTableEntry:
    """
    Sayfa tablosu girişi (Page Table Entry — PTE).

    frame_number: Fiziksel frame numarası (valid=False ise anlamsız)
    valid:        Sayfa şu an RAM'de mi (resident)?
    dirty:        Sayfa RAM'e yüklendikten sonra değiştirildi mi?
    referenced:   Son zamanlarda erişildi mi? (LRU / Clock algoritmaları için)
    """

    frame_number: int = -1
    valid: bool = False
    dirty: bool = False
    referenced: bool = False


class PageTable:
    """
    Tek bir process'in sanal sayfa → fiziksel frame eşleştirmesi.

    page_size: Her sayfanın boyutu (byte). Fiziksel adres hesabında kullanılır.
    """

    def __init__(self, page_size: int = 4096) -> None:
        if page_size <= 0:
            raise ValueError(f"page_size pozitif olmalı, verildi: {page_size}")
        self.page_size = page_size
        self._entries: dict[int, PageTableEntry] = {}

    def map(self, page_number: int, frame_number: int) -> None:
        """Sayfayı frame'e eşle; valid ve referenced bitlerini ayarla."""
        entry = self._entries.setdefault(page_number, PageTableEntry())
        entry.frame_number = frame_number
        entry.valid = True
        entry.referenced = True

    def invalidate(self, page_number: int) -> None:
        """Sayfayı geçersiz işaretle (disk'e taşındı / evict edildi)."""
        if page_number in self._entries:
            self._entries[page_number].valid = False

    def translate(self, page_number: int) -> int:
        """
        Sanal sayfa numarasından fiziksel taban adresini hesapla.

        Returns:
            frame_number * page_size  (frame'in fiziksel başlangıç adresi)

        Raises:
            PageFault: Sayfa tabloda yok veya valid değilse
        """
        entry = self._entries.get(page_number)
        if entry is None or not entry.valid:
            raise PageFault(page_number)
        entry.referenced = True
        return entry.frame_number * self.page_size

    def get_entry(self, page_number: int) -> Optional[PageTableEntry]:
        """PTE'yi döndür; sayfa tabloda yoksa None."""
        return self._entries.get(page_number)

    def __len__(self) -> int:
        """Tablodaki toplam giriş sayısı."""
        return len(self._entries)

    def __repr__(self) -> str:
        valid_count = sum(1 for e in self._entries.values() if e.valid)
        return (
            f"PageTable(entries={len(self._entries)}, valid={valid_count}, "
            f"page_size={self.page_size})"
        )


class TLB:
    """
    Translation Lookaside Buffer — sayfa tablosu çevirisi için donanım önbelleği.

    Sabit kapasiteli. Dolduğunda FIFO politikasıyla en eski giriş çıkarılır.
    Hit / miss istatistikleri tutar.
    """

    def __init__(self, capacity: int = 16) -> None:
        if capacity <= 0:
            raise ValueError(f"TLB kapasitesi pozitif olmalı, verildi: {capacity}")
        self.capacity = capacity
        self._cache: dict[int, int] = {}  # page_number → frame_number
        self._order: list[int] = []       # Ekleme sırası (FIFO eviction için)
        self._hits: int = 0
        self._misses: int = 0

    def lookup(self, page_number: int) -> Optional[int]:
        """
        TLB'de sayfa numarasını ara.

        Returns:
            Frame numarası (hit) veya None (miss)
        """
        if page_number in self._cache:
            self._hits += 1
            return self._cache[page_number]
        self._misses += 1
        return None

    def insert(self, page_number: int, frame_number: int) -> None:
        """
        TLB'ye yeni giriş ekle.

        Giriş zaten varsa yalnızca frame numarasını güncelle.
        Kapasite doluysa FIFO ile en eski girişi çıkar.
        """
        if page_number in self._cache:
            self._cache[page_number] = frame_number
            return
        if len(self._cache) >= self.capacity:
            oldest = self._order.pop(0)
            del self._cache[oldest]
        self._cache[page_number] = frame_number
        self._order.append(page_number)

    def invalidate(self, page_number: int) -> None:
        """Tek bir girişi TLB'den kaldır (eviction sonrası çağrılır)."""
        if page_number in self._cache:
            del self._cache[page_number]
            self._order.remove(page_number)

    def flush(self) -> None:
        """Tüm TLB'yi temizle (context switch veya process sonlanması)."""
        self._cache.clear()
        self._order.clear()

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        """TLB isabet oranı (0.0 – 1.0). Hiç erişim yoksa 0.0."""
        total = self._hits + self._misses
        return 0.0 if total == 0 else self._hits / total

    def __len__(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        return (
            f"TLB(capacity={self.capacity}, entries={len(self._cache)}, "
            f"hit_rate={self.hit_rate:.2%})"
        )
