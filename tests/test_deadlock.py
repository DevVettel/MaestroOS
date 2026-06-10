"""
Hafta 8 testleri — Deadlock Detection & Avoidance.

Çalıştır: PYTHONPATH=. pytest tests/test_deadlock.py -v
"""

import pytest

from core.deadlock import BankersAlgorithm, Resource, ResourceAllocationGraph


# ===========================================================================
# Resource dataclass testleri
# ===========================================================================

class TestResource:
    def test_fields_stored_correctly(self):
        r = Resource(rid=1, name="Printer", total_instances=2, available_instances=1)
        assert r.rid == 1
        assert r.name == "Printer"
        assert r.total_instances == 2
        assert r.available_instances == 1

    def test_fully_available_on_creation(self):
        r = Resource(rid=0, name="CPU", total_instances=4, available_instances=4)
        assert r.available_instances == r.total_instances


# ===========================================================================
# ResourceAllocationGraph — yapı testleri
# ===========================================================================

class TestRAGConstruction:
    def test_add_resource_stores_resource(self):
        rag = ResourceAllocationGraph()
        rag.add_resource(1, "Disk", 3)
        r = rag.get_resource(1)
        assert r.rid == 1
        assert r.name == "Disk"
        assert r.total_instances == 3
        assert r.available_instances == 3

    def test_add_process_stores_process(self):
        rag = ResourceAllocationGraph()
        rag.add_process(10)
        assert 10 in rag.get_processes()

    def test_request_edge_recorded(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(5, "R", 2)
        rag.request_edge(1, 5)
        assert 5 in rag.get_requested_resources(1)

    def test_assignment_edge_decreases_available(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(5, "R", 3)
        rag.assignment_edge(1, 5)
        assert rag.get_resource(5).available_instances == 2

    def test_assignment_edge_recorded_in_held_resources(self):
        rag = ResourceAllocationGraph()
        rag.add_process(2)
        rag.add_resource(7, "R", 1)
        rag.assignment_edge(2, 7)
        assert 7 in rag.get_held_resources(2)

    def test_release_increases_available(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(3, "R", 2)
        rag.assignment_edge(1, 3)
        rag.release(1, 3)
        assert rag.get_resource(3).available_instances == 2

    def test_release_removes_held_resource(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(3, "R", 2)
        rag.assignment_edge(1, 3)
        rag.release(1, 3)
        assert 3 not in rag.get_held_resources(1)

    def test_release_nonheld_resource_is_noop(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(3, "R", 2)
        # Hiç assignment yapılmadan release — hata vermemeli
        rag.release(1, 3)
        assert rag.get_resource(3).available_instances == 2


# ===========================================================================
# ResourceAllocationGraph — deadlock tespiti
# ===========================================================================

class TestRAGDeadlockDetection:
    def test_empty_graph_no_deadlock(self):
        rag = ResourceAllocationGraph()
        assert rag.detect_deadlock() == []

    def test_single_process_no_request_no_deadlock(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        assert rag.detect_deadlock() == []

    def test_single_process_with_resource_held_no_deadlock(self):
        rag = ResourceAllocationGraph()
        rag.add_process(1)
        rag.add_resource(1, "R", 1)
        rag.assignment_edge(1, 1)
        assert rag.detect_deadlock() == []

    def test_no_deadlock_linear_chain(self):
        """P0 → R0 → P1: P0 waits for P1, P1 waits for nothing."""
        rag = ResourceAllocationGraph()
        rag.add_process(0)
        rag.add_process(1)
        rag.add_resource(0, "R0", 1)
        rag.assignment_edge(1, 0)   # R0 atandı P1'e
        rag.request_edge(0, 0)      # P0 R0 istiyor
        # P0 → P1 (wait-for), P1 kimseyi beklemiyor → döngü yok
        assert rag.detect_deadlock() == []

    def test_simple_deadlock_two_processes(self):
        """P0 ↔ P1 karşılıklı bekleme → deadlock."""
        rag = ResourceAllocationGraph()
        rag.add_process(0)
        rag.add_process(1)
        rag.add_resource(0, "R0", 1)
        rag.add_resource(1, "R1", 1)
        rag.assignment_edge(0, 0)  # P0 R0'ı tutuyor
        rag.assignment_edge(1, 1)  # P1 R1'i tutuyor
        rag.request_edge(0, 1)     # P0 R1 istiyor (P1'in elinde)
        rag.request_edge(1, 0)     # P1 R0 istiyor (P0'ın elinde)
        result = rag.detect_deadlock()
        assert set(result) == {0, 1}

    def test_simple_deadlock_three_processes(self):
        """P0→P1→P2→P0 döngüsü."""
        rag = ResourceAllocationGraph()
        for pid in range(3):
            rag.add_process(pid)
        for rid in range(3):
            rag.add_resource(rid, f"R{rid}", 1)
        # Her process bir kaynağı tutuyor
        rag.assignment_edge(0, 0)
        rag.assignment_edge(1, 1)
        rag.assignment_edge(2, 2)
        # Döngüsel istekler
        rag.request_edge(0, 1)  # P0 → R1 (P1'de)
        rag.request_edge(1, 2)  # P1 → R2 (P2'de)
        rag.request_edge(2, 0)  # P2 → R0 (P0'da)
        result = rag.detect_deadlock()
        assert set(result) == {0, 1, 2}

    def test_partial_deadlock_two_out_of_three(self):
        """P0↔P1 deadlock, P2 özgür."""
        rag = ResourceAllocationGraph()
        for pid in range(3):
            rag.add_process(pid)
        rag.add_resource(0, "R0", 1)
        rag.add_resource(1, "R1", 1)
        rag.assignment_edge(0, 0)
        rag.assignment_edge(1, 1)
        rag.request_edge(0, 1)
        rag.request_edge(1, 0)
        # P2 hiçbir şey talep etmiyor
        result = rag.detect_deadlock()
        assert set(result) == {0, 1}
        assert 2 not in result

    def test_release_resolves_deadlock(self):
        """Deadlock var, P0 kaynağını bırakınca ortadan kalkar."""
        rag = ResourceAllocationGraph()
        rag.add_process(0)
        rag.add_process(1)
        rag.add_resource(0, "R0", 1)
        rag.add_resource(1, "R1", 1)
        rag.assignment_edge(0, 0)
        rag.assignment_edge(1, 1)
        rag.request_edge(0, 1)
        rag.request_edge(1, 0)
        assert len(rag.detect_deadlock()) == 2
        # P0 R0'ı serbest bırakıyor; P1 artık ilerleyebilir
        rag.release(0, 0)
        assert rag.detect_deadlock() == []

    def test_deadlock_result_is_sorted(self):
        """detect_deadlock() sıralı pid listesi döndürmeli."""
        rag = ResourceAllocationGraph()
        for pid in [5, 3, 1]:
            rag.add_process(pid)
        for rid in range(3):
            rag.add_resource(rid, f"R{rid}", 1)
        rag.assignment_edge(5, 0)
        rag.assignment_edge(3, 1)
        rag.assignment_edge(1, 2)
        rag.request_edge(5, 1)
        rag.request_edge(3, 2)
        rag.request_edge(1, 0)
        result = rag.detect_deadlock()
        assert result == sorted(result)

    def test_get_deadlocked_processes_alias(self):
        """get_deadlocked_processes, detect_deadlock ile aynı sonucu döndürmeli."""
        rag = ResourceAllocationGraph()
        rag.add_process(0)
        rag.add_process(1)
        rag.add_resource(0, "R0", 1)
        rag.add_resource(1, "R1", 1)
        rag.assignment_edge(0, 0)
        rag.assignment_edge(1, 1)
        rag.request_edge(0, 1)
        rag.request_edge(1, 0)
        assert rag.get_deadlocked_processes() == rag.detect_deadlock()

    def test_self_request_no_deadlock(self):
        """Bir process kendi tuttuğu kaynağı talep ediyor (degenerate)."""
        rag = ResourceAllocationGraph()
        rag.add_process(0)
        rag.add_resource(0, "R0", 2)
        rag.assignment_edge(0, 0)
        rag.request_edge(0, 0)
        # Wait-for: P0 kendini beklemiyor (holding_pid != waiting_pid kontrolü)
        assert rag.detect_deadlock() == []

    def test_multiple_resources_no_cycle(self):
        """İki kaynak, iki process, döngü yok."""
        rag = ResourceAllocationGraph()
        rag.add_process(0)
        rag.add_process(1)
        rag.add_resource(0, "CPU", 2)
        rag.add_resource(1, "RAM", 4)
        rag.assignment_edge(0, 0)
        rag.assignment_edge(0, 1)
        rag.request_edge(1, 0)
        # P1 → P0 (wait-for), P0 kimseyi beklemiyor
        assert rag.detect_deadlock() == []


# ===========================================================================
# BankersAlgorithm — başlangıç durumu testleri
# ===========================================================================

class TestBankersInit:
    def _classic(self):
        """Klasik 3-process, 3-kaynak Banker örneği."""
        processes = [0, 1, 2]
        resources = [10, 5, 7]
        allocation = {
            0: [0, 1, 0],
            1: [2, 0, 0],
            2: [3, 0, 2],
        }
        max_demand = {
            0: [7, 5, 3],
            1: [3, 2, 2],
            2: [9, 0, 2],
        }
        return BankersAlgorithm(processes, resources, allocation, max_demand)

    def test_available_computed_correctly(self):
        ba = self._classic()
        # 10-0-2-3=5, 5-1-0-0=4, 7-0-0-2=5
        assert ba.get_available() == [5, 4, 5]

    def test_need_computed_correctly_pid0(self):
        ba = self._classic()
        assert ba.get_need(0) == [7, 4, 3]

    def test_need_computed_correctly_pid1(self):
        ba = self._classic()
        assert ba.get_need(1) == [1, 2, 2]

    def test_allocation_returned_correctly(self):
        ba = self._classic()
        assert ba.get_allocation(0) == [0, 1, 0]

    def test_processes_list_stored(self):
        ba = self._classic()
        assert set(ba.processes) == {0, 1, 2}


# ===========================================================================
# BankersAlgorithm — güvenli durum analizi
# ===========================================================================

class TestBankersSafety:
    def _safe_example(self):
        """Güvenli durum örneği."""
        processes = [0, 1, 2]
        resources = [10, 5, 7]
        allocation = {0: [0, 1, 0], 1: [2, 0, 0], 2: [3, 0, 2]}
        max_demand = {0: [7, 5, 3], 1: [3, 2, 2], 2: [9, 0, 2]}
        return BankersAlgorithm(processes, resources, allocation, max_demand)

    def _unsafe_example(self):
        """Güvensiz durum örneği — tüm kaynaklar tahsis edilmiş."""
        processes = [0, 1]
        resources = [2, 2]
        allocation = {0: [1, 1], 1: [1, 1]}
        max_demand = {0: [2, 2], 1: [2, 2]}
        return BankersAlgorithm(processes, resources, allocation, max_demand)

    def test_safe_state_returns_true(self):
        ba = self._safe_example()
        assert ba.is_safe_state() is True

    def test_unsafe_state_returns_false(self):
        ba = self._unsafe_example()
        assert ba.is_safe_state() is False

    def test_find_safe_sequence_returns_list(self):
        ba = self._safe_example()
        seq = ba.find_safe_sequence()
        assert seq is not None
        assert len(seq) == 3
        assert set(seq) == {0, 1, 2}

    def test_find_safe_sequence_unsafe_returns_none(self):
        ba = self._unsafe_example()
        assert ba.find_safe_sequence() is None

    def test_single_process_safe(self):
        processes = [0]
        resources = [5, 3]
        allocation = {0: [1, 1]}
        max_demand = {0: [4, 3]}
        ba = BankersAlgorithm(processes, resources, allocation, max_demand)
        assert ba.is_safe_state() is True
        assert ba.find_safe_sequence() == [0]

    def test_single_process_unsafe(self):
        """Process maksimum talebini karşılayamayan tek process."""
        processes = [0]
        resources = [1]
        allocation = {0: [1]}
        max_demand = {0: [3]}
        ba = BankersAlgorithm(processes, resources, allocation, max_demand)
        # available=0, need=2 → tamamlanamaz
        assert ba.is_safe_state() is False

    def test_all_resources_fully_allocated_unsafe(self):
        """Tüm kaynaklar dolu, hiçbir process tamamlanamıyor."""
        processes = [0, 1, 2]
        resources = [3]
        allocation = {0: [1], 1: [1], 2: [1]}
        max_demand = {0: [2], 1: [2], 2: [2]}
        ba = BankersAlgorithm(processes, resources, allocation, max_demand)
        # available=0, her process en az 1 daha istiyor
        assert ba.is_safe_state() is False

    def test_zero_allocation_safe_if_resources_sufficient(self):
        """Hiç kaynak tahsis edilmemişse available = total → güvenli."""
        processes = [0, 1]
        resources = [4, 4]
        allocation = {0: [0, 0], 1: [0, 0]}
        max_demand = {0: [2, 2], 1: [2, 2]}
        ba = BankersAlgorithm(processes, resources, allocation, max_demand)
        assert ba.is_safe_state() is True

    def test_safe_sequence_contains_all_processes(self):
        """Güvenli sıra tüm process'leri içermeli."""
        processes = [0, 1, 2, 3]
        resources = [10]
        allocation = {0: [1], 1: [2], 2: [2], 3: [1]}
        max_demand = {0: [4], 1: [5], 2: [3], 3: [2]}
        ba = BankersAlgorithm(processes, resources, allocation, max_demand)
        seq = ba.find_safe_sequence()
        assert seq is not None
        assert sorted(seq) == [0, 1, 2, 3]


# ===========================================================================
# BankersAlgorithm — kaynak talebi testleri
# ===========================================================================

class TestBankersRequest:
    def _make(self):
        processes = [0, 1, 2]
        resources = [10, 5, 7]
        allocation = {0: [0, 1, 0], 1: [2, 0, 0], 2: [3, 0, 2]}
        max_demand = {0: [7, 5, 3], 1: [3, 2, 2], 2: [9, 0, 2]}
        return BankersAlgorithm(processes, resources, allocation, max_demand)

    def test_valid_request_granted(self):
        ba = self._make()
        # P1 need=[1,2,2], available=[5,4,5] → güvenli tahsis
        assert ba.request_resources(1, [1, 0, 2]) is True

    def test_valid_request_updates_allocation(self):
        ba = self._make()
        ba.request_resources(1, [1, 0, 2])
        assert ba.get_allocation(1) == [3, 0, 2]

    def test_valid_request_decreases_available(self):
        ba = self._make()
        ba.request_resources(1, [1, 0, 2])
        avail = ba.get_available()
        assert avail == [4, 4, 3]

    def test_request_exceeds_need_rejected(self):
        ba = self._make()
        # P0 need=[7,4,3], bu talebi aşıyor
        assert ba.request_resources(0, [8, 0, 0]) is False

    def test_request_exceeds_available_rejected(self):
        ba = self._make()
        # available[1]=4, bu talebi aşıyor
        assert ba.request_resources(0, [0, 5, 0]) is False

    def test_unsafe_request_rejected(self):
        """Talep need/available sınırları içinde ama tahsis sonrası sistem güvensiz kalır.

        P0 kısmen tahsis alınca available=1 kalır; tüm process'lerin need=2
        olduğundan hiçbiri tamamlanamaz → güvensiz durum → red.
        """
        processes = [0, 1, 2]
        resources = [6]
        allocation = {0: [1], 1: [2], 2: [1]}
        max_demand = {0: [4], 1: [4], 2: [3]}
        ba = BankersAlgorithm(processes, resources, allocation, max_demand)
        # available=2; need={0:3,1:2,2:2} → P1 tamamlanabilir → güvenli
        assert ba.is_safe_state() is True
        # P0 [1] alırsa avail=1; need={0:2,1:2,2:2} → hepsi >1 → güvensiz
        assert ba.request_resources(0, [1]) is False

    def test_zero_request_always_granted(self):
        """Sıfır kaynak talebi her zaman onaylanmalı."""
        ba = self._make()
        assert ba.request_resources(0, [0, 0, 0]) is True

    def test_rejected_request_does_not_change_allocation(self):
        """Reddedilen talep allocation'ı değiştirmemeli."""
        ba = self._make()
        original = ba.get_allocation(0)
        ba.request_resources(0, [8, 0, 0])  # reddedilecek
        assert ba.get_allocation(0) == original

    def test_rejected_request_does_not_change_available(self):
        """Reddedilen talep available'ı değiştirmemeli."""
        ba = self._make()
        original = ba.get_available()
        ba.request_resources(0, [8, 0, 0])  # reddedilecek
        assert ba.get_available() == original

    def test_sequential_grants_update_state(self):
        """Ardışık iki onaylı talep doğru birikimli durumu yansıtmalı."""
        ba = self._make()
        ba.request_resources(1, [1, 0, 0])
        ba.request_resources(1, [0, 1, 0])
        alloc = ba.get_allocation(1)
        assert alloc[0] == 3  # 2+1
        assert alloc[1] == 1  # 0+1
