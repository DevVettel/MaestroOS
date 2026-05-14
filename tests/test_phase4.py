"""
Hafta 4 testleri — Paging & Virtual Memory.

Çalıştır: PYTHONPATH=. pytest tests/test_phase4.py -v
"""

import pytest

from core.paging import PageFault, PageTable, PageTableEntry, TLB
from core.virtual_memory import VirtualMemoryManager
from algorithms.memory.fifo import FIFO
from algorithms.memory.lru import LRU
from algorithms.memory.optimal import Optimal


# ---------------------------------------------------------------------------
# PageTableEntry
# ---------------------------------------------------------------------------

class TestPageTableEntry:
    def test_defaults(self):
        pte = PageTableEntry()
        assert pte.frame_number == -1
        assert pte.valid is False
        assert pte.dirty is False
        assert pte.referenced is False

    def test_set_valid(self):
        pte = PageTableEntry(frame_number=3, valid=True)
        assert pte.frame_number == 3
        assert pte.valid is True

    def test_dirty_flag(self):
        pte = PageTableEntry(valid=True, dirty=True)
        assert pte.dirty is True

    def test_referenced_flag(self):
        pte = PageTableEntry(referenced=True)
        assert pte.referenced is True


# ---------------------------------------------------------------------------
# PageTable
# ---------------------------------------------------------------------------

class TestPageTable:
    def test_raises_on_zero_page_size(self):
        with pytest.raises(ValueError):
            PageTable(page_size=0)

    def test_raises_on_negative_page_size(self):
        with pytest.raises(ValueError):
            PageTable(page_size=-1)

    def test_initial_length_zero(self):
        pt = PageTable()
        assert len(pt) == 0

    def test_map_creates_valid_entry(self):
        pt = PageTable(page_size=4096)
        pt.map(page_number=0, frame_number=2)
        entry = pt.get_entry(0)
        assert entry is not None
        assert entry.valid is True
        assert entry.frame_number == 2

    def test_translate_returns_physical_base(self):
        pt = PageTable(page_size=4096)
        pt.map(page_number=1, frame_number=3)
        assert pt.translate(1) == 3 * 4096

    def test_translate_raises_page_fault_for_missing(self):
        pt = PageTable(page_size=4096)
        with pytest.raises(PageFault) as exc_info:
            pt.translate(99)
        assert exc_info.value.page_number == 99

    def test_translate_raises_page_fault_after_invalidate(self):
        pt = PageTable(page_size=4096)
        pt.map(page_number=0, frame_number=1)
        pt.invalidate(0)
        with pytest.raises(PageFault):
            pt.translate(0)

    def test_invalidate_nonexistent_page_no_error(self):
        pt = PageTable(page_size=4096)
        pt.invalidate(999)  # Should not raise

    def test_translate_sets_referenced_bit(self):
        pt = PageTable(page_size=4096)
        pt.map(page_number=2, frame_number=0)
        entry = pt.get_entry(2)
        entry.referenced = False
        pt.translate(2)
        assert entry.referenced is True

    def test_get_entry_returns_none_when_missing(self):
        pt = PageTable()
        assert pt.get_entry(42) is None

    def test_map_increments_length(self):
        pt = PageTable()
        pt.map(0, 0)
        pt.map(1, 1)
        assert len(pt) == 2


# ---------------------------------------------------------------------------
# TLB
# ---------------------------------------------------------------------------

class TestTLB:
    def test_raises_on_zero_capacity(self):
        with pytest.raises(ValueError):
            TLB(capacity=0)

    def test_raises_on_negative_capacity(self):
        with pytest.raises(ValueError):
            TLB(capacity=-1)

    def test_initial_length_zero(self):
        tlb = TLB(capacity=4)
        assert len(tlb) == 0

    def test_lookup_miss_increments_misses(self):
        tlb = TLB(capacity=4)
        result = tlb.lookup(5)
        assert result is None
        assert tlb.misses == 1
        assert tlb.hits == 0

    def test_lookup_hit_increments_hits(self):
        tlb = TLB(capacity=4)
        tlb.insert(page_number=1, frame_number=7)
        result = tlb.lookup(1)
        assert result == 7
        assert tlb.hits == 1

    def test_hit_rate_zero_with_no_accesses(self):
        tlb = TLB(capacity=4)
        assert tlb.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        tlb = TLB(capacity=4)
        tlb.insert(0, 0)
        tlb.lookup(0)   # hit
        tlb.lookup(1)   # miss
        tlb.lookup(0)   # hit
        assert tlb.hits == 2
        assert tlb.misses == 1
        assert round(tlb.hit_rate, 4) == round(2 / 3, 4)

    def test_insert_fills_cache(self):
        tlb = TLB(capacity=3)
        tlb.insert(0, 10)
        tlb.insert(1, 11)
        tlb.insert(2, 12)
        assert len(tlb) == 3

    def test_capacity_evicts_oldest_fifo(self):
        tlb = TLB(capacity=2)
        tlb.insert(0, 10)
        tlb.insert(1, 11)
        tlb.insert(2, 12)  # Should evict page 0
        assert tlb.lookup(0) is None  # miss — page 0 evicted
        assert tlb.lookup(1) == 11
        assert tlb.lookup(2) == 12

    def test_invalidate_removes_entry(self):
        tlb = TLB(capacity=4)
        tlb.insert(5, 3)
        tlb.invalidate(5)
        assert tlb.lookup(5) is None

    def test_flush_clears_all_entries(self):
        tlb = TLB(capacity=8)
        tlb.insert(0, 0)
        tlb.insert(1, 1)
        tlb.flush()
        assert len(tlb) == 0
        assert tlb.lookup(0) is None

    def test_update_existing_entry(self):
        tlb = TLB(capacity=4)
        tlb.insert(3, 10)
        tlb.insert(3, 20)  # Update frame for same page
        assert tlb.lookup(3) == 20
        assert len(tlb) == 1  # No duplicate entry


# ---------------------------------------------------------------------------
# FIFO Algorithm (unit)
# ---------------------------------------------------------------------------

class TestFIFOAlgorithm:
    def test_name(self):
        assert FIFO().name == "FIFO"

    def test_select_victim_is_oldest_frame(self):
        fifo = FIFO()
        fifo.on_access(frame_number=0, tick=1)
        fifo.on_access(frame_number=1, tick=2)
        fifo.on_access(frame_number=2, tick=3)
        occupied = {0: (1, 10), 1: (1, 11), 2: (1, 12)}
        assert fifo.select_victim(occupied, tick=4) == 0

    def test_on_evict_removes_frame(self):
        fifo = FIFO()
        fifo.on_access(0, 1)
        fifo.on_access(1, 2)
        fifo.on_evict(0)
        occupied = {1: (1, 11), 2: (1, 12)}
        fifo.on_access(2, 3)
        assert fifo.select_victim(occupied, tick=4) == 1

    def test_repeated_access_does_not_duplicate(self):
        fifo = FIFO()
        fifo.on_access(0, 1)
        fifo.on_access(0, 2)  # Same frame, second access
        fifo.on_access(1, 3)
        occupied = {0: (1, 10), 1: (1, 11)}
        # Frame 0 was added once → it's still the oldest
        assert fifo.select_victim(occupied, tick=4) == 0


# ---------------------------------------------------------------------------
# LRU Algorithm (unit)
# ---------------------------------------------------------------------------

class TestLRUAlgorithm:
    def test_name(self):
        assert LRU().name == "LRU"

    def test_select_victim_least_recently_used(self):
        lru = LRU()
        lru.on_access(0, tick=1)
        lru.on_access(1, tick=2)
        lru.on_access(2, tick=3)
        lru.on_access(0, tick=4)  # Re-access frame 0
        occupied = {0: (1, 10), 1: (1, 11), 2: (1, 12)}
        # Frame 1 was least recently used (tick=2)
        assert lru.select_victim(occupied, tick=5) == 1

    def test_on_evict_removes_entry(self):
        lru = LRU()
        lru.on_access(0, tick=1)
        lru.on_access(1, tick=2)
        lru.on_evict(0)
        occupied = {1: (1, 11)}
        assert lru.select_victim(occupied, tick=3) == 1

    def test_access_updates_time(self):
        lru = LRU()
        lru.on_access(0, tick=1)
        lru.on_access(1, tick=2)
        lru.on_access(0, tick=10)  # Update frame 0 time
        occupied = {0: (1, 10), 1: (1, 11)}
        # Frame 1 has older time (2 < 10)
        assert lru.select_victim(occupied, tick=11) == 1


# ---------------------------------------------------------------------------
# Optimal Algorithm (unit)
# ---------------------------------------------------------------------------

class TestOptimalAlgorithm:
    def test_name(self):
        assert Optimal().name == "Optimal"

    def test_evicts_page_not_in_future(self):
        opt = Optimal()
        occupied = {0: (1, 1), 1: (1, 2), 2: (1, 3)}
        # page 3 (frame 2) not in future → immediate evict candidate
        future = [(1, 1), (1, 2)]
        assert opt.select_victim(occupied, tick=1, future_refs=future) == 2

    def test_evicts_furthest_future_page(self):
        opt = Optimal()
        occupied = {0: (1, 1), 1: (1, 2), 2: (1, 3)}
        # page 1 at idx 0, page 2 at idx 1, page 3 at idx 2 → evict frame 2
        future = [(1, 1), (1, 2), (1, 3)]
        assert opt.select_victim(occupied, tick=1, future_refs=future) == 2

    def test_no_future_refs_returns_any_frame(self):
        opt = Optimal()
        occupied = {5: (1, 99)}
        result = opt.select_victim(occupied, tick=1, future_refs=None)
        assert result == 5

    def test_empty_future_refs_returns_any_frame(self):
        opt = Optimal()
        occupied = {0: (1, 10), 1: (1, 11)}
        result = opt.select_victim(occupied, tick=1, future_refs=[])
        assert result in occupied


# ---------------------------------------------------------------------------
# VirtualMemoryManager — temel davranış
# ---------------------------------------------------------------------------

class TestVMMBasic:
    def test_raises_on_zero_frames(self):
        with pytest.raises(ValueError):
            VirtualMemoryManager(num_frames=0)

    def test_raises_on_zero_page_size(self):
        with pytest.raises(ValueError):
            VirtualMemoryManager(num_frames=4, page_size=0)

    def test_raises_on_zero_tlb_capacity(self):
        with pytest.raises(ValueError):
            VirtualMemoryManager(num_frames=4, tlb_capacity=0)

    def test_initial_all_frames_free(self):
        vmm = VirtualMemoryManager(num_frames=4)
        assert vmm.free_frame_count == 4
        assert vmm.occupied_frame_count == 0

    def test_first_access_causes_page_fault(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        vmm.access(pid=1, logical_address=0)
        assert vmm.stats()["page_faults"] == 1

    def test_second_access_same_page_no_fault(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        vmm.access(pid=1, logical_address=0)
        vmm.access(pid=1, logical_address=0)
        assert vmm.stats()["page_faults"] == 1

    def test_access_returns_correct_physical_address(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        phys = vmm.access(pid=1, logical_address=0)
        # page 0 → frame 0, offset 0 → physical = 0
        assert phys == 0

    def test_offset_preserved_in_physical_address(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        phys = vmm.access(pid=1, logical_address=100)
        # page 0 (100 // 4096 = 0), offset = 100 % 4096 = 100
        # physical = frame_0 * 4096 + 100 = 0 + 100 = 100
        assert phys == 100

    def test_different_pages_different_frames(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        phys0 = vmm.access(pid=1, logical_address=0)       # page 0
        phys1 = vmm.access(pid=1, logical_address=4096)    # page 1
        assert phys0 != phys1

    def test_frame_count_decreases_on_load(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        vmm.access(pid=1, logical_address=0)      # page 0
        vmm.access(pid=1, logical_address=4096)   # page 1
        assert vmm.free_frame_count == 2
        assert vmm.occupied_frame_count == 2

    def test_default_strategy_is_fifo(self):
        vmm = VirtualMemoryManager(num_frames=2)
        assert vmm._strategy.name == "FIFO"


# ---------------------------------------------------------------------------
# VirtualMemoryManager + FIFO
# ---------------------------------------------------------------------------

class TestVMMWithFIFO:
    def test_fifo_eviction_order(self):
        # 2 frames: load pages 1, 2, then 3 → evicts page 1 (FIFO)
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=FIFO())
        vmm.access(pid=1, logical_address=1)  # page 1 → frame 0
        vmm.access(pid=1, logical_address=2)  # page 2 → frame 1
        vmm.access(pid=1, logical_address=3)  # page 3 → evict frame 0
        assert vmm.stats()["page_faults"] == 3
        # Page 1 should be evicted → accessing it causes another fault
        pre = vmm.stats()["page_faults"]
        vmm.access(pid=1, logical_address=1)
        assert vmm.stats()["page_faults"] == pre + 1

    def test_multiple_processes_independent_page_tables(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096, strategy=FIFO())
        vmm.access(pid=1, logical_address=0)
        vmm.access(pid=2, logical_address=0)
        # Each process maps page 0 independently — 2 page faults total
        assert vmm.stats()["page_faults"] == 2

    def test_tlb_hit_after_load(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096, strategy=FIFO())
        vmm.access(pid=1, logical_address=0)  # miss → fault
        vmm.access(pid=1, logical_address=0)  # TLB hit
        vmm.access(pid=1, logical_address=0)  # TLB hit
        s = vmm.stats()
        assert s["tlb_hits"] == 2
        assert s["page_faults"] == 1

    def test_full_memory_triggers_eviction(self):
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=FIFO())
        vmm.access(pid=1, logical_address=0)
        vmm.access(pid=1, logical_address=1)
        # All frames occupied — next access must evict
        assert vmm.free_frame_count == 0
        vmm.access(pid=1, logical_address=2)
        assert vmm.occupied_frame_count == 2  # Still 2 occupied after eviction

    def test_classic_belady_sequence(self):
        # Reference: 1,2,3,4,1,2,5,1,2,3,4,5  3 frames
        # FIFO → 9 faults, Optimal → 7 faults
        pid = 1
        refs = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        vmm = VirtualMemoryManager(num_frames=3, page_size=1, strategy=FIFO())
        for page in refs:
            vmm.access(pid, page)
        assert vmm.stats()["page_faults"] == 9


# ---------------------------------------------------------------------------
# VirtualMemoryManager + LRU
# ---------------------------------------------------------------------------

class TestVMMWithLRU:
    def test_lru_evicts_least_recently_used(self):
        # 2 frames: load 1, 2; access 1 again; load 3 → LRU evicts page 2
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=LRU())
        vmm.access(pid=1, logical_address=1)  # load page 1 (tick=1)
        vmm.access(pid=1, logical_address=2)  # load page 2 (tick=2)
        vmm.access(pid=1, logical_address=1)  # TLB hit, page 1 (tick=3)
        # Now page 2 is LRU. Load page 3 → evict page 2
        vmm.access(pid=1, logical_address=3)  # fault (tick=4)
        assert vmm.stats()["page_faults"] == 3
        # Page 2 should be gone; accessing it should fault
        pre = vmm.stats()["page_faults"]
        vmm.access(pid=1, logical_address=2)
        assert vmm.stats()["page_faults"] == pre + 1

    def test_lru_preserves_recently_used_page(self):
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=LRU())
        vmm.access(pid=1, logical_address=1)  # load page 1
        vmm.access(pid=1, logical_address=2)  # load page 2
        vmm.access(pid=1, logical_address=2)  # re-access page 2 → most recent
        # Load page 3 → LRU evicts page 1 (less recently used)
        vmm.access(pid=1, logical_address=3)
        # Page 2 should still be in memory
        pre = vmm.stats()["page_faults"]
        vmm.access(pid=1, logical_address=2)  # should hit (TLB or page table)
        assert vmm.stats()["page_faults"] == pre  # No additional fault

    def test_lru_name(self):
        assert LRU().name == "LRU"

    def test_lru_page_fault_count_with_repeated_pattern(self):
        # Pages: 1, 2, 3, 2, 1 with 2 frames
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=LRU())
        for page in [1, 2, 3, 2, 1]:
            vmm.access(pid=1, logical_address=page)
        # 1→fault, 2→fault, 3→fault(evict 1), 2→hit, 1→fault(evict 3) = 4
        assert vmm.stats()["page_faults"] == 4


# ---------------------------------------------------------------------------
# VirtualMemoryManager + Optimal
# ---------------------------------------------------------------------------

class TestVMMWithOptimal:
    def test_optimal_evicts_page_not_in_future(self):
        # 2 frames: pages 1,2 loaded. Future has only page 1 → evict page 2
        pid = 1
        future = [(pid, 1), (pid, 2), (pid, 3), (pid, 1)]
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=Optimal())
        vmm.set_future_references(future)
        vmm.access(pid, 1)  # load 1
        vmm.access(pid, 2)  # load 2
        # Load 3: future is [(pid,1)] → page 2 not in future → evict page 2
        vmm.access(pid, 3)
        vmm.access(pid, 1)  # should hit (not evicted)
        assert vmm.stats()["page_faults"] == 3

    def test_optimal_fewer_or_equal_faults_than_fifo(self):
        # Classic: 1,2,3,4,1,2,5,1,2,3,4,5 with 3 frames
        pid = 1
        refs = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        future = [(pid, p) for p in refs]

        vmm_fifo = VirtualMemoryManager(num_frames=3, page_size=1, strategy=FIFO())
        for page in refs:
            vmm_fifo.access(pid, page)

        vmm_opt = VirtualMemoryManager(num_frames=3, page_size=1, strategy=Optimal())
        vmm_opt.set_future_references(future)
        for page in refs:
            vmm_opt.access(pid, page)

        assert vmm_opt.stats()["page_faults"] <= vmm_fifo.stats()["page_faults"]

    def test_optimal_no_future_refs_still_works(self):
        vmm = VirtualMemoryManager(num_frames=2, page_size=1, strategy=Optimal())
        vmm.access(pid=1, logical_address=1)
        vmm.access(pid=1, logical_address=2)
        vmm.access(pid=1, logical_address=3)  # evict something (no future info)
        assert vmm.stats()["page_faults"] == 3

    def test_optimal_name(self):
        assert Optimal().name == "Optimal"


# ---------------------------------------------------------------------------
# VirtualMemoryManager — stats
# ---------------------------------------------------------------------------

class TestVMMStats:
    def test_stats_keys_present(self):
        vmm = VirtualMemoryManager(num_frames=4)
        s = vmm.stats()
        assert set(s.keys()) == {"page_faults", "tlb_hits", "tlb_misses", "hit_rate"}

    def test_initial_stats_all_zero(self):
        vmm = VirtualMemoryManager(num_frames=4)
        s = vmm.stats()
        assert s["page_faults"] == 0
        assert s["tlb_hits"] == 0
        assert s["tlb_misses"] == 0
        assert s["hit_rate"] == 0.0

    def test_page_faults_increments_per_fault(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=4096)
        vmm.access(pid=1, logical_address=0)
        vmm.access(pid=1, logical_address=4096)
        vmm.access(pid=1, logical_address=8192)
        assert vmm.stats()["page_faults"] == 3

    def test_tlb_hits_after_repeated_access(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=1)
        vmm.access(pid=1, logical_address=5)  # miss
        vmm.access(pid=1, logical_address=5)  # hit
        vmm.access(pid=1, logical_address=5)  # hit
        s = vmm.stats()
        assert s["tlb_hits"] == 2
        assert s["tlb_misses"] == 1

    def test_hit_rate_range(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=1)
        for addr in range(10):
            vmm.access(pid=1, logical_address=addr)
        s = vmm.stats()
        assert 0.0 <= s["hit_rate"] <= 1.0

    def test_hit_rate_increases_with_repeated_accesses(self):
        vmm = VirtualMemoryManager(num_frames=4, page_size=1)
        # First pass: all misses
        for addr in [1, 2, 3]:
            vmm.access(pid=1, logical_address=addr)
        rate_after_first = vmm.stats()["hit_rate"]
        # Second pass: all TLB hits
        for addr in [1, 2, 3]:
            vmm.access(pid=1, logical_address=addr)
        rate_after_second = vmm.stats()["hit_rate"]
        assert rate_after_second > rate_after_first

    def test_repr_contains_useful_info(self):
        vmm = VirtualMemoryManager(num_frames=8, page_size=4096, strategy=LRU())
        r = repr(vmm)
        assert "8" in r
        assert "LRU" in r
