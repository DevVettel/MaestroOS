"""
Hafta 3 testleri — MemoryManager, First/Best/Worst Fit, Fragmentation.

Çalıştır: pytest tests/test_phase3.py -v
"""

import pytest

from core.memory_manager import (
    AllocationStrategy,
    MemoryBlock,
    MemoryManager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mm(
    total: int = 1000,
    strategy: AllocationStrategy = AllocationStrategy.FIRST_FIT,
) -> MemoryManager:
    return MemoryManager(total_size=total, strategy=strategy)


# ---------------------------------------------------------------------------
# MemoryBlock testleri
# ---------------------------------------------------------------------------

class TestMemoryBlock:
    def test_end_address(self):
        b = MemoryBlock(start=0, size=100)
        assert b.end == 99

    def test_is_free_when_no_pid(self):
        b = MemoryBlock(start=0, size=100)
        assert b.is_free is True

    def test_is_not_free_when_pid_set(self):
        b = MemoryBlock(start=0, size=100, pid=1)
        assert b.is_free is False


# ---------------------------------------------------------------------------
# MemoryManager — temel davranış
# ---------------------------------------------------------------------------

class TestMemoryManagerBasic:
    def test_raises_on_zero_size(self):
        with pytest.raises(ValueError):
            MemoryManager(total_size=0)

    def test_raises_on_negative_size(self):
        with pytest.raises(ValueError):
            MemoryManager(total_size=-100)

    def test_starts_as_single_free_block(self):
        mm = make_mm(1000)
        blocks = mm.memory_map()
        assert len(blocks) == 1
        assert blocks[0].is_free
        assert blocks[0].size == 1000

    def test_total_free_equals_total_size_initially(self):
        mm = make_mm(1000)
        assert mm.total_free == 1000

    def test_total_used_zero_initially(self):
        mm = make_mm(1000)
        assert mm.total_used == 0

    def test_allocate_invalid_size_raises(self):
        mm = make_mm(1000)
        with pytest.raises(ValueError):
            mm.allocate(pid=1, size=0)

    def test_allocate_larger_than_total_fails(self):
        mm = make_mm(1000)
        result = mm.allocate(pid=1, size=1001)
        assert result.success is False

    def test_allocate_success(self):
        mm = make_mm(1000)
        result = mm.allocate(pid=1, size=200)
        assert result.success is True
        assert result.block is not None
        assert result.block.pid == 1
        assert result.block.size == 200

    def test_allocate_reduces_free_memory(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=300)
        assert mm.total_free == 700
        assert mm.total_used == 300

    def test_allocate_splits_block(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=300)
        blocks = mm.memory_map()
        assert len(blocks) == 2
        assert blocks[0].pid == 1
        assert blocks[0].size == 300
        assert blocks[1].is_free
        assert blocks[1].size == 700

    def test_allocate_exact_size_no_split(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=1000)
        blocks = mm.memory_map()
        assert len(blocks) == 1
        assert blocks[0].pid == 1

    def test_deallocate_frees_block(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=300)
        result = mm.deallocate(pid=1)
        assert result is True
        assert mm.total_free == 1000

    def test_deallocate_nonexistent_pid_returns_false(self):
        mm = make_mm(1000)
        assert mm.deallocate(pid=99) is False

    def test_coalescing_after_deallocate(self):
        # [P1=300][P2=300][FREE=400] → deallocate P1 → [FREE=300][P2=300][FREE=400]
        # → P2 deallocate → [FREE=1000] (tek blok)
        mm = make_mm(1000)
        mm.allocate(pid=1, size=300)
        mm.allocate(pid=2, size=300)
        mm.deallocate(pid=1)
        mm.deallocate(pid=2)
        blocks = mm.memory_map()
        assert len(blocks) == 1
        assert blocks[0].is_free
        assert blocks[0].size == 1000

    def test_total_size_always_consistent(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.deallocate(pid=1)
        assert mm.total_free + mm.total_used == mm.total_size

    def test_multiple_allocations(self):
        mm = make_mm(1000)
        for i in range(1, 6):
            r = mm.allocate(pid=i, size=100)
            assert r.success is True
        assert mm.total_used == 500
        assert mm.total_free == 500

    def test_failed_allocation_when_no_space(self):
        mm = make_mm(100)
        mm.allocate(pid=1, size=100)
        result = mm.allocate(pid=2, size=50)
        assert result.success is False
        assert mm._failed_allocations == 1


# ---------------------------------------------------------------------------
# First Fit
# ---------------------------------------------------------------------------

class TestFirstFit:
    def test_selects_first_fitting_block(self):
        # [FREE=200][P1=300][FREE=500]
        mm = make_mm(1000, AllocationStrategy.FIRST_FIT)
        mm.allocate(pid=1, size=200)  # [P1=200][FREE=800]
        mm.allocate(pid=2, size=300)  # [P1=200][P2=300][FREE=500]
        mm.deallocate(pid=1)          # [FREE=200][P2=300][FREE=500]
        # First fit: 150 için ilk uygun = FREE=200 bloğu
        r = mm.allocate(pid=3, size=150)
        assert r.success is True
        assert r.block.start == 0  # İlk bloktan tahsis edildi

    def test_allocates_sequentially(self):
        mm = make_mm(900, AllocationStrategy.FIRST_FIT)
        r1 = mm.allocate(pid=1, size=300)
        r2 = mm.allocate(pid=2, size=300)
        r3 = mm.allocate(pid=3, size=300)
        assert r1.block.start == 0
        assert r2.block.start == 300
        assert r3.block.start == 600


# ---------------------------------------------------------------------------
# Best Fit
# ---------------------------------------------------------------------------

class TestBestFit:
    def test_selects_smallest_fitting_block(self):
        # [FREE=200][P1=300][FREE=500] → best fit for 150 = FREE=200 (en küçük uygun)
        mm = make_mm(1000, AllocationStrategy.BEST_FIT)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.deallocate(pid=1)  # [FREE=200][P2=300][FREE=500]
        r = mm.allocate(pid=3, size=150)
        assert r.success is True
        assert r.block.start == 0  # 200'lük blok seçildi (en küçük uygun)

    def test_prefers_tighter_fit(self):
        # İki boş blok: 200 ve 500. 180 isteniyor.
        # Best fit: 200'lük bloğu seçmeli (500-180=320 israf > 200-180=20)
        mm = make_mm(1000, AllocationStrategy.BEST_FIT)
        mm.allocate(pid=1, size=200)  # placeholder
        mm.allocate(pid=2, size=300)  # orta dolu blok
        mm.allocate(pid=3, size=500)  # placeholder
        mm.deallocate(pid=1)  # 200'lük boş
        mm.deallocate(pid=3)  # 500'lük boş → ama 3 bitişik değil, coalesce olmaz
        r = mm.allocate(pid=4, size=180)
        assert r.success is True
        assert r.block.size == 180


# ---------------------------------------------------------------------------
# Worst Fit
# ---------------------------------------------------------------------------

class TestWorstFit:
    def test_selects_largest_fitting_block(self):
        # [FREE=200][P1=300][FREE=500] → worst fit for 150 = FREE=500 (en büyük)
        mm = make_mm(1000, AllocationStrategy.WORST_FIT)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.deallocate(pid=1)  # [FREE=200][P2=300][FREE=500]
        r = mm.allocate(pid=3, size=150)
        assert r.success is True
        assert r.block.start == 500  # 500'lük bloktan tahsis edildi

    def test_leaves_larger_remaining_fragment(self):
        mm = make_mm(1000, AllocationStrategy.WORST_FIT)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.deallocate(pid=1)
        mm.allocate(pid=3, size=100)
        # Worst fit 500'lük bloğu seçti → 400 kaldı
        free_blocks = [b for b in mm.memory_map() if b.is_free]
        largest_free = max(b.size for b in free_blocks)
        assert largest_free == 400


# ---------------------------------------------------------------------------
# Fragmentation testleri
# ---------------------------------------------------------------------------

class TestFragmentation:
    def test_no_fragmentation_initially(self):
        mm = make_mm(1000)
        assert mm.external_fragmentation == 0

    def test_no_fragmentation_single_allocation(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=400)
        # [P1=400][FREE=600] → tek boş blok → external frag = 0
        assert mm.external_fragmentation == 0

    def test_external_fragmentation_after_deallocation(self):
        # [P1=200][P2=300][P3=200][FREE=300]
        # P2 deallocate → [P1=200][FREE=300][P3=200][FREE=300]
        # Toplam boş=600, en büyük boş=300 → external frag=300
        mm = make_mm(1000)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.allocate(pid=3, size=200)
        mm.deallocate(pid=2)
        assert mm.external_fragmentation == 300

    def test_coalescing_reduces_fragmentation(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.allocate(pid=3, size=200)
        mm.deallocate(pid=2)
        # P1 ve P3 arasında FREE=300 var — P1'i de serbest bırakırsak
        # [FREE=200][FREE=300] coalesce → [FREE=500]
        mm.deallocate(pid=1)
        # Şimdi: [FREE=500][P3=200][FREE=300]
        assert mm.external_fragmentation == 300  # Hâlâ P3 ortada

    def test_fragmentation_ratio_range(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=300)
        mm.deallocate(pid=1)
        ratio = mm.fragmentation_ratio
        assert 0.0 <= ratio <= 1.0

    def test_full_memory_no_fragmentation(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=1000)
        assert mm.external_fragmentation == 0
        assert mm.fragmentation_ratio == 0.0

    def test_allocation_fails_due_to_fragmentation(self):
        # Toplam boş=400 ama parçalı → 300 isteği reddedilir
        mm = make_mm(1000)
        mm.allocate(pid=1, size=200)
        mm.allocate(pid=2, size=400)
        mm.allocate(pid=3, size=200)
        mm.allocate(pid=4, size=200)  # [P1=200][P2=400][P3=200][P4=200]
        mm.deallocate(pid=1)          # [FREE=200][P2=400][P3=200][P4=200]
        mm.deallocate(pid=3)          # [FREE=200][P2=400][FREE=200][P4=200]
        # Toplam boş=400, ama en büyük boş blok=200 → 300 sığmaz
        result = mm.allocate(pid=5, size=300)
        assert result.success is False


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_keys_present(self):
        mm = make_mm(1000)
        s = mm.stats()
        expected_keys = {
            "total_size", "total_used", "total_free",
            "external_fragmentation", "fragmentation_ratio",
            "free_block_count", "used_block_count",
            "allocation_count", "deallocation_count",
            "failed_allocations", "strategy",
        }
        assert expected_keys == set(s.keys())

    def test_allocation_count_increments(self):
        mm = make_mm(1000)
        mm.allocate(pid=1, size=100)
        mm.allocate(pid=2, size=100)
        assert mm.stats()["allocation_count"] == 2

    def test_failed_allocation_count(self):
        mm = make_mm(100)
        mm.allocate(pid=1, size=100)
        mm.allocate(pid=2, size=50)  # başarısız
        assert mm.stats()["failed_allocations"] == 1
