"""
Hafta 2 testleri — SJF, SRTF, Round Robin, Priority Scheduling.

Çalıştır: pytest tests/test_phase2.py -v
"""

import pytest

from core.process import Process, ProcessState
from core.scheduler import Scheduler
from algorithms.scheduling.sjf import SJF, SRTF
from algorithms.scheduling.round_robin import RoundRobin
from algorithms.scheduling.priority import PriorityScheduling, PreemptivePriority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_scheduler(algorithm, processes):
    s = Scheduler(algorithm=algorithm)
    s.load_processes(processes)
    return s

def run(algorithm, processes):
    s = make_scheduler(algorithm, processes)
    stats = s.run_until_complete()
    return s, stats


# ---------------------------------------------------------------------------
# SJF — Non-preemptive
# ---------------------------------------------------------------------------

class TestSJF:
    def test_single_process_completes(self):
        p = Process(pid=1, name="p1", burst_time=4)
        _, stats = run(SJF(), [p])
        assert stats.completed_processes == 1
        assert p.state == ProcessState.TERMINATED

    def test_selects_shortest_first(self):
        # P1 burst=6, P2 burst=2, P3 burst=8 — hepsi arrival=0
        # SJF: P2(2) → P1(6) → P3(8)
        p1 = Process(pid=1, name="p1", burst_time=6, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=0)
        p3 = Process(pid=3, name="p3", burst_time=8, arrival_time=0)
        _, stats = run(SJF(), [p1, p2, p3])
        assert p2.completion_time == 2
        assert p1.completion_time == 8
        assert p3.completion_time == 16

    def test_non_preemptive_does_not_interrupt(self):
        # P1 burst=5, arrival=0 — çalışmaya başladıktan sonra
        # P2 burst=1, arrival=2 gelirse P1 kesilmemeli
        p1 = Process(pid=1, name="p1", burst_time=5, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=1, arrival_time=2)
        _, stats = run(SJF(), [p1, p2])
        assert p1.completion_time == 5  # P1 kesilmedi
        assert p2.completion_time == 6

    def test_tie_broken_by_arrival_time(self):
        # Eşit burst_time → arrival_time'a göre FCFS
        p1 = Process(pid=1, name="p1", burst_time=3, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=3, arrival_time=0)
        _, stats = run(SJF(), [p1, p2])
        assert p1.completion_time < p2.completion_time

    def test_avg_waiting_time_better_than_fcfs(self):
        # SJF'nin klasik avantajı: FCFS'den düşük avg_waiting_time
        # P1 burst=10, P2 burst=1, P3 burst=2
        # FCFS: wait = 0 + 10 + 11 = 21, avg = 7
        # SJF:  P2→P3→P1: wait = 0 + 1 + 3 = 4, avg = 1.33
        processes = [
            Process(pid=1, name="p1", burst_time=10, arrival_time=0),
            Process(pid=2, name="p2", burst_time=1,  arrival_time=0),
            Process(pid=3, name="p3", burst_time=2,  arrival_time=0),
        ]
        _, stats = run(SJF(), processes)
        assert stats.avg_waiting_time < 7.0

    def test_all_processes_complete(self):
        processes = [
            Process(pid=i, name=f"p{i}", burst_time=i+1, arrival_time=0)
            for i in range(5)
        ]
        _, stats = run(SJF(), processes)
        assert stats.completed_processes == 5


# ---------------------------------------------------------------------------
# SRTF — Preemptive SJF
# ---------------------------------------------------------------------------

class TestSRTF:
    def test_preempts_when_shorter_arrives(self):
        # P1 burst=6 arrival=0, P2 burst=2 arrival=2
        # P1 tick 1-2 çalışır (remaining=4), P2 gelir (remaining=2 < 4) → preempt
        # P2 tick 3-4 çalışır, P1 kaldığı yerden devam (remaining=4) tick 5-8
        p1 = Process(pid=1, name="p1", burst_time=6, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=2)
        _, stats = run(SRTF(), [p1, p2])
        assert p2.completion_time < p1.completion_time
        assert stats.completed_processes == 2

    def test_does_not_preempt_when_longer_arrives(self):
        # P1 burst=2 arrival=0, P2 burst=5 arrival=1
        # P2, P1'den uzun → preempt etmemeli
        p1 = Process(pid=1, name="p1", burst_time=2, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=5, arrival_time=1)
        _, stats = run(SRTF(), [p1, p2])
        assert p1.completion_time == 2

    def test_all_processes_complete(self):
        processes = [
            Process(pid=1, name="p1", burst_time=8, arrival_time=0),
            Process(pid=2, name="p2", burst_time=4, arrival_time=1),
            Process(pid=3, name="p3", burst_time=2, arrival_time=2),
        ]
        _, stats = run(SRTF(), processes)
        assert stats.completed_processes == 3

    def test_single_process_no_preemption(self):
        p = Process(pid=1, name="p1", burst_time=5)
        _, stats = run(SRTF(), [p])
        assert stats.completed_processes == 1


# ---------------------------------------------------------------------------
# Round Robin
# ---------------------------------------------------------------------------

class TestRoundRobin:
    def test_invalid_quantum_raises(self):
        with pytest.raises(ValueError):
            RoundRobin(quantum=0)

    def test_single_process_completes(self):
        p = Process(pid=1, name="p1", burst_time=3)
        _, stats = run(RoundRobin(quantum=2), [p])
        assert stats.completed_processes == 1

    def test_two_processes_interleave(self):
        # Q=2, P1 burst=4, P2 burst=4, arrival=0
        # Tick 1-2: P1 runs (remaining=2)
        # Tick 3-4: P2 runs (remaining=2)
        # Tick 5-6: P1 runs (remaining=0) → P1 done at tick 6
        # Tick 7-8: P2 runs (remaining=0) → P2 done at tick 8
        p1 = Process(pid=1, name="p1", burst_time=4, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=4, arrival_time=0)
        _, stats = run(RoundRobin(quantum=2), [p1, p2])
        assert stats.completed_processes == 2
        # İkisi de tamamlandı ve completion_time farklı
        assert p1.completion_time != p2.completion_time

    def test_no_starvation(self):
        # RR starvation üretmemeli — tüm processler tamamlanmalı
        processes = [
            Process(pid=1, name="p1", burst_time=10, priority=0, arrival_time=0),
            Process(pid=2, name="p2", burst_time=2,  priority=10, arrival_time=0),
            Process(pid=3, name="p3", burst_time=5,  priority=5,  arrival_time=0),
        ]
        _, stats = run(RoundRobin(quantum=3), processes)
        assert stats.completed_processes == 3

    def test_quantum_larger_than_burst(self):
        # Quantum > burst_time ise process quantum dolmadan biter
        p = Process(pid=1, name="p1", burst_time=2)
        _, stats = run(RoundRobin(quantum=10), [p])
        assert stats.completed_processes == 1

    def test_context_switches_increase_with_small_quantum(self):
        processes = [
            Process(pid=i, name=f"p{i}", burst_time=6, arrival_time=0)
            for i in range(3)
        ]
        _, stats_small = run(RoundRobin(quantum=1), [
            Process(pid=i, name=f"p{i}", burst_time=6, arrival_time=0)
            for i in range(3)
        ])
        _, stats_large = run(RoundRobin(quantum=6), [
            Process(pid=i, name=f"p{i}", burst_time=6, arrival_time=0)
            for i in range(3)
        ])
        assert stats_small.context_switches > stats_large.context_switches

    def test_all_complete_with_various_bursts(self):
        processes = [
            Process(pid=1, name="p1", burst_time=1, arrival_time=0),
            Process(pid=2, name="p2", burst_time=7, arrival_time=0),
            Process(pid=3, name="p3", burst_time=3, arrival_time=0),
        ]
        _, stats = run(RoundRobin(quantum=2), processes)
        assert stats.completed_processes == 3


# ---------------------------------------------------------------------------
# Priority Scheduling — Non-preemptive
# ---------------------------------------------------------------------------

class TestPriorityScheduling:
    def test_invalid_aging_raises(self):
        with pytest.raises(ValueError):
            PriorityScheduling(aging_interval=0)

    def test_highest_priority_runs_first(self):
        # Düşük sayı = yüksek öncelik
        p1 = Process(pid=1, name="p1", burst_time=3, arrival_time=0, priority=5)
        p2 = Process(pid=2, name="p2", burst_time=3, arrival_time=0, priority=1)
        p3 = Process(pid=3, name="p3", burst_time=3, arrival_time=0, priority=3)
        _, stats = run(PriorityScheduling(aging_interval=None), [p1, p2, p3])
        # P2(priority=1) önce, P3(priority=3) ikinci, P1(priority=5) son
        assert p2.completion_time == 3
        assert p3.completion_time == 6
        assert p1.completion_time == 9

    def test_non_preemptive_does_not_interrupt(self):
        p1 = Process(pid=1, name="p1", burst_time=5, arrival_time=0, priority=5)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=2, priority=1)
        _, stats = run(PriorityScheduling(aging_interval=None), [p1, p2])
        # P1 çalışıyorken P2 geldi ama P1 kesilmedi
        assert p1.completion_time == 5

    def test_aging_prevents_starvation(self):
        # aging_interval=5 ile düşük öncelikli process zamanla çalışabilmeli
        p_high = Process(pid=1, name="high", burst_time=20, arrival_time=0, priority=1)
        p_low  = Process(pid=2, name="low",  burst_time=3,  arrival_time=0, priority=10)
        _, stats = run(PriorityScheduling(aging_interval=5), [p_high, p_low])
        assert stats.completed_processes == 2

    def test_all_processes_complete(self):
        processes = [
            Process(pid=i, name=f"p{i}", burst_time=3, arrival_time=0, priority=i)
            for i in range(5)
        ]
        _, stats = run(PriorityScheduling(), processes)
        assert stats.completed_processes == 5


# ---------------------------------------------------------------------------
# PreemptivePriority
# ---------------------------------------------------------------------------

class TestPreemptivePriority:
    def test_preempts_on_higher_priority_arrival(self):
        # P1 priority=5 çalışırken P2 priority=1 gelir → P1 preempt edilir
        p1 = Process(pid=1, name="p1", burst_time=6, arrival_time=0, priority=5)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=2, priority=1)
        _, stats = run(PreemptivePriority(aging_interval=None), [p1, p2])
        assert p2.completion_time < p1.completion_time

    def test_does_not_preempt_on_lower_priority(self):
        p1 = Process(pid=1, name="p1", burst_time=4, arrival_time=0, priority=1)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=1, priority=5)
        _, stats = run(PreemptivePriority(aging_interval=None), [p1, p2])
        assert p1.completion_time == 4  # P1 kesilmedi

    def test_all_processes_complete(self):
        processes = [
            Process(pid=1, name="p1", burst_time=5, arrival_time=0, priority=3),
            Process(pid=2, name="p2", burst_time=2, arrival_time=1, priority=1),
            Process(pid=3, name="p3", burst_time=3, arrival_time=3, priority=2),
        ]
        _, stats = run(PreemptivePriority(), processes)
        assert stats.completed_processes == 3


# ---------------------------------------------------------------------------
# Algoritma karşılaştırma — aynı process seti, farklı algoritmalar
# ---------------------------------------------------------------------------

class TestAlgorithmComparison:
    """
    Klasik OS teorisindeki beklentileri doğrula.
    """

    PROCESSES = [
        (1, "p1", 10, 0, 3),  # pid, name, burst, arrival, priority
        (2, "p2", 1,  0, 1),
        (3, "p3", 2,  0, 2),
        (4, "p4", 5,  0, 4),
    ]

    def _make_processes(self):
        return [
            Process(pid=p[0], name=p[1], burst_time=p[2], arrival_time=p[3], priority=p[4])
            for p in self.PROCESSES
        ]

    def test_sjf_avg_wait_lte_fcfs(self):
        from algorithms.scheduling.fcfs import FCFS
        _, fcfs_stats = run(FCFS(), self._make_processes())
        _, sjf_stats  = run(SJF(),  self._make_processes())
        assert sjf_stats.avg_waiting_time <= fcfs_stats.avg_waiting_time

    def test_all_algorithms_complete_all_processes(self):
        algorithms = [
            SJF(), SRTF(),
            RoundRobin(quantum=3),
            PriorityScheduling(),
            PreemptivePriority(),
        ]
        for algo in algorithms:
            _, stats = run(algo, self._make_processes())
            assert stats.completed_processes == 4, f"{algo.name} tamamlayamadı"
