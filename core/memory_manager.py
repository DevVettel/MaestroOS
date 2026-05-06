"""
Memory Manager — Contiguous Memory Allocation.

Gerçek bir OS'ta bellek sabit boyutlu veya değişken boyutlu
bloklara bölünür. Burada değişken boyutlu (contiguous) modeli simüle ediyoruz.

Üç allocation stratejisi:
  First Fit  — İlk uygun bloğu seç (hızlı)
  Best Fit   — En küçük uygun bloğu seç (iç fragmentation az)
  Worst Fit  — En büyük uygun bloğu seç (kalan parça büyük kalır)

Fragmentation türleri:
  Internal — Blok process'ten büyük, fazla alan boşa gider
  External — Toplam boş alan yeterli ama parçalı, sığmıyor
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class AllocationStrategy(Enum):
    FIRST_FIT = auto()
    BEST_FIT  = auto()
    WORST_FIT = auto()


@dataclass
class MemoryBlock:
    """
    Bellekteki tek bir blok.

    start: Başlangıç adresi (byte)
    size:  Blok boyutu (byte)
    pid:   Bloğu kullanan process (None = boş)
    """
    start: int
    size: int
    pid: Optional[int] = None

    @property
    def end(self) -> int:
        return self.start + self.size - 1

    @property
    def is_free(self) -> bool:
        return self.pid is None

    def __repr__(self) -> str:
        status = f"PID={self.pid}" if self.pid else "FREE"
        return f"Block[{self.start}–{self.end}] size={self.size} ({status})"


@dataclass
class AllocationResult:
    """Bir allocation işleminin sonucu."""
    success: bool
    block: Optional[MemoryBlock] = None
    message: str = ""


class MemoryManager:
    """
    Contiguous memory allocation simülatörü.

    total_size: Toplam bellek boyutu (byte)
    strategy:   Hangi fit algoritması kullanılacak

    Bellek başlangıçta tek bir boş blok olarak başlar.
    Her allocate() bloğu böler, her deallocate() komşu boş
    blokları birleştirir (coalescing).
    """

    def __init__(
        self,
        total_size: int,
        strategy: AllocationStrategy = AllocationStrategy.FIRST_FIT,
    ) -> None:
        if total_size <= 0:
            raise ValueError(f"total_size pozitif olmalı, verildi: {total_size}")
        self.total_size = total_size
        self.strategy = strategy
        # Başlangıçta tek boş blok
        self._blocks: list[MemoryBlock] = [MemoryBlock(start=0, size=total_size)]
        self._allocation_count: int = 0
        self._deallocation_count: int = 0
        self._failed_allocations: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allocate(self, pid: int, size: int) -> AllocationResult:
        """
        Process için bellek tahsis et.

        Args:
            pid:  Process ID
            size: İstenen boyut (byte)

        Returns:
            AllocationResult — başarı/başarısızlık + blok bilgisi
        """
        if size <= 0:
            raise ValueError(f"size pozitif olmalı, verildi: {size}")
        if size > self.total_size:
            self._failed_allocations += 1
            return AllocationResult(
                success=False,
                message=f"İstenen boyut ({size}) toplam bellekten ({self.total_size}) büyük"
            )

        free_blocks = [b for b in self._blocks if b.is_free and b.size >= size]

        if not free_blocks:
            self._failed_allocations += 1
            ext_frag = self.external_fragmentation
            return AllocationResult(
                success=False,
                message=(
                    f"Yeterli boş blok yok. "
                    f"Toplam boş: {self.total_free} byte, "
                    f"External fragmentation: {ext_frag} byte"
                )
            )

        target = self._select_block(free_blocks)
        allocated = self._split_block(target, pid, size)

        self._allocation_count += 1
        return AllocationResult(success=True, block=allocated, message="OK")

    def deallocate(self, pid: int) -> bool:
        """
        Process'in kullandığı belleği serbest bırak.

        Serbest bırakılan blokların yanındaki boş bloklarla
        birleştirir (coalescing) — external fragmentation azaltır.

        Returns:
            True → başarılı, False → PID bulunamadı
        """
        target_blocks = [b for b in self._blocks if b.pid == pid]
        if not target_blocks:
            return False

        for block in target_blocks:
            block.pid = None

        self._coalesce()
        self._deallocation_count += 1
        return True

    # ------------------------------------------------------------------
    # Fragmentation metrikleri
    # ------------------------------------------------------------------

    @property
    def total_free(self) -> int:
        """Toplam boş bellek (byte)."""
        return sum(b.size for b in self._blocks if b.is_free)

    @property
    def total_used(self) -> int:
        """Toplam kullanılan bellek (byte)."""
        return sum(b.size for b in self._blocks if not b.is_free)

    @property
    def external_fragmentation(self) -> int:
        """
        External fragmentation: Boş ama kullanılamayan bellek.

        Toplam boş - en büyük boş blok = parçalı alan.
        Bu alan yeterli toplam büyüklükte olsa da,
        ardışık olmadığı için büyük process'lere verilemez.
        """
        free_blocks = [b for b in self._blocks if b.is_free]
        if not free_blocks:
            return 0
        largest_free = max(b.size for b in free_blocks)
        return self.total_free - largest_free

    @property
    def fragmentation_ratio(self) -> float:
        """External fragmentation / total_free oranı (0.0 – 1.0)."""
        if self.total_free == 0:
            return 0.0
        return self.external_fragmentation / self.total_free

    @property
    def free_block_count(self) -> int:
        return sum(1 for b in self._blocks if b.is_free)

    @property
    def used_block_count(self) -> int:
        return sum(1 for b in self._blocks if not b.is_free)

    def stats(self) -> dict:
        return {
            "total_size":             self.total_size,
            "total_used":             self.total_used,
            "total_free":             self.total_free,
            "external_fragmentation": self.external_fragmentation,
            "fragmentation_ratio":    round(self.fragmentation_ratio, 3),
            "free_block_count":       self.free_block_count,
            "used_block_count":       self.used_block_count,
            "allocation_count":       self._allocation_count,
            "deallocation_count":     self._deallocation_count,
            "failed_allocations":     self._failed_allocations,
            "strategy":               self.strategy.name,
        }

    def memory_map(self) -> list[MemoryBlock]:
        """Belleğin anlık görüntüsü — adrese göre sıralı."""
        return sorted(self._blocks, key=lambda b: b.start)

    # ------------------------------------------------------------------
    # Private — strateji seçimi
    # ------------------------------------------------------------------

    def _select_block(self, free_blocks: list[MemoryBlock]) -> MemoryBlock:
        if self.strategy == AllocationStrategy.FIRST_FIT:
            return min(free_blocks, key=lambda b: b.start)
        elif self.strategy == AllocationStrategy.BEST_FIT:
            return min(free_blocks, key=lambda b: b.size)
        else:  # WORST_FIT
            return max(free_blocks, key=lambda b: b.size)

    def _split_block(
        self, block: MemoryBlock, pid: int, size: int
    ) -> MemoryBlock:
        """
        Bloğu ikiye böl: allocated + remaining (eğer kalan varsa).

        Kalan = 0 ise böl — gereksiz sıfır boyutlu blok oluşturma.
        """
        idx = self._blocks.index(block)
        remaining = block.size - size

        # Mevcut bloğu allocated olarak işaretle
        block.size = size
        block.pid = pid

        # Kalan alan varsa yeni boş blok ekle
        if remaining > 0:
            new_free = MemoryBlock(
                start=block.start + size,
                size=remaining,
                pid=None,
            )
            self._blocks.insert(idx + 1, new_free)

        return block

    def _coalesce(self) -> None:
        """
        Ardışık boş blokları birleştir.

        [FREE 100] [FREE 200] → [FREE 300]

        Deallocate sonrası çağrılır. External fragmentation'ı azaltır.
        """
        self._blocks.sort(key=lambda b: b.start)
        merged: list[MemoryBlock] = []

        for block in self._blocks:
            if merged and merged[-1].is_free and block.is_free:
                # Önceki boş blokla birleştir
                merged[-1].size += block.size
            else:
                merged.append(block)

        self._blocks = merged

    def __repr__(self) -> str:
        return (
            f"MemoryManager(total={self.total_size}, "
            f"used={self.total_used}, free={self.total_free}, "
            f"strategy={self.strategy.name})"
        )
