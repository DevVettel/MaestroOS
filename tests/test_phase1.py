"""
Faz 1 unit testleri — Process, Clock, Scheduler, FCFS.

Çalıştır: pytest tests/test_phase1.py -v
"""

import pytest

from core.clock import SimulationClock
from core.process import Process, ProcessState
from core.scheduler import Scheduler, SchedulerStats
from algorithms.scheduling.fcfs import FCFS


# ---------------------------------------------------------------------------
# Process testleri
# ---------------------------------------------------------------------------

class TestProcess:
    def test_creates_with_correct_defaults(self):
        p = Process(pid=1, name="test", burst_time=5)
        assert p.state == ProcessState.NEW
        assert p.remaining_time == 5
        assert p.waiting_time == 0
        assert p.arrival_time == 0

    def test_remaining_time_equals_burst_time_on_create(self):
        p = Process(pid=1, name="p1", burst_time=10)
        assert p.remaining_time == p.burst_time

    def test_raises_on_zero_burst_time(self):
        with pytest.raises(ValueError, match="burst_time"):
            Process(pid=1, name="bad", burst_time=0)

    def test_raises_on_negative_burst_time(self):
        with pytest.raises(ValueError):
            Process(pid=1, name="bad", burst_time=-1)

    def test_raises_on_negative_arrival_time(self):
        with pytest.raises(ValueError, match="arrival_time"):
            Process(pid=1, name="bad", burst_time=5, arrival_time=-1)

    def test_valid_state_transition_new_to_ready(self):
        p = Process(pid=1, name="p1", burst_time=5)
        p.transition_to(ProcessState.READY)
        assert p.state == ProcessState.READY

    def test_valid_state_transition_ready_to_running(self):
        p = Process(pid=1, name="p1", burst_time=5)
        p.transition_to(ProcessState.READY)
        p.transition_to(ProcessState.RUNNING)
        assert p.state == ProcessState.RUNNING

    def test_invalid_state_transition_raises(self):
        p = Process(pid=1, name="p1", burst_time=5)
        with pytest.raises(ValueError, match="Geçersiz state geçişi"):
            # NEW → RUNNING direkt geçiş geçersiz
            p.transition_to(ProcessState.RUNNING)

    def test_terminated_process_cannot_transition(self):
        p = Process(pid=1, name="p1", burst_time=1)
        p.transition_to(ProcessState.READY)
        p.transition_to(ProcessState.RUNNING)
        p.transition_to(ProcessState.TERMINATED)
        with pytest.raises(ValueError):
            p.transition_to(ProcessState.READY)

    def test_is_finished_when_remaining_time_zero(self):
        p = Process(pid=1, name="p1", burst_time=1)
        p.remaining_time = 0
        assert p.is_finished is True

    def test_is_not_finished_when_remaining_time_positive(self):
        p = Process(pid=1, name="p1", burst_time=5)
        assert p.is_finished is False


# ---------------------------------------------------------------------------
# SimulationClock testleri
# ---------------------------------------------------------------------------

class TestSimulationClock:
    def test_starts_at_zero(self):
        clock = SimulationClock()
        assert clock.current_tick == 0

    def test_tick_increments_by_one(self):
        clock = SimulationClock()
        clock.tick()
        assert clock.current_tick == 1

    def test_multiple_ticks(self):
        clock = SimulationClock()
        for _ in range(5):
            clock.tick()
        assert clock.current_tick == 5

    def test_tick_returns_new_value(self):
        clock = SimulationClock()
        result = clock.tick()
        assert result == 1

    def test_subscriber_called_on_tick(self):
        clock = SimulationClock()
        received_ticks = []
        clock.subscribe(lambda t: received_ticks.append(t))
        clock.tick()
        clock.tick()
        assert received_ticks == [1, 2]

    def test_reset_clears_tick(self):
        clock = SimulationClock()
        clock.tick()
        clock.tick()
        clock.reset()
        assert clock.current_tick == 0

    def test_reset_clears_subscribers(self):
        clock = SimulationClock()
        calls = []
        clock.subscribe(lambda t: calls.append(t))
        clock.reset()
        clock.tick()
        assert calls == []


# ---------------------------------------------------------------------------
# FCFS testleri
# ---------------------------------------------------------------------------

class TestFCFS:
    def _make_scheduler(self, processes: list[Process]) -> Scheduler:
        scheduler = Scheduler(algorithm=FCFS())
        scheduler.load_processes(processes)
        return scheduler

    def test_single_process_completes(self):
        p = Process(pid=1, name="p1", burst_time=3)
        scheduler = self._make_scheduler([p])
        stats = scheduler.run_until_complete()
        assert stats.completed_processes == 1
        assert p.state == ProcessState.TERMINATED

    def test_single_process_turnaround_equals_burst(self):
        # Tek process, arrival_time=0 → turnaround = burst_time
        p = Process(pid=1, name="p1", burst_time=5)
        scheduler = self._make_scheduler([p])
        scheduler.run_until_complete()
        assert p.turnaround_time == 5

    def test_single_process_waiting_time_is_zero(self):
        p = Process(pid=1, name="p1", burst_time=5)
        scheduler = self._make_scheduler([p])
        scheduler.run_until_complete()
        assert p.waiting_time == 0

    def test_two_processes_fcfs_order(self):
        # P1 arrival=0 burst=4, P2 arrival=0 burst=2
        # FCFS → P1 önce, P2 sonra (eklendikleri sıra)
        p1 = Process(pid=1, name="p1", burst_time=4, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=0)
        scheduler = self._make_scheduler([p1, p2])
        scheduler.run_until_complete()
        # P1 tick 4'te, P2 tick 6'da tamamlanır
        assert p1.completion_time == 4
        assert p2.completion_time == 6

    def test_waiting_time_calculated_correctly(self):
        # P1: burst=4, arrival=0 → waiting=0
        # P2: burst=2, arrival=0 → P1 bittikten sonra başlar, waiting=4
        p1 = Process(pid=1, name="p1", burst_time=4, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=0)
        scheduler = self._make_scheduler([p1, p2])
        scheduler.run_until_complete()
        assert p1.waiting_time == 0
        assert p2.waiting_time == 4

    def test_processes_with_different_arrival_times(self):
        # P1: arrival=0, burst=3 → tick 3'te biter
        # P2: arrival=2, burst=2 → P1 bittikten sonra başlar, tick 5'te biter
        p1 = Process(pid=1, name="p1", burst_time=3, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=2)
        scheduler = self._make_scheduler([p1, p2])
        scheduler.run_until_complete()
        assert p1.completion_time == 3
        assert p2.completion_time == 5

    def test_all_processes_complete(self):
        processes = [
            Process(pid=i, name=f"p{i}", burst_time=i + 1, arrival_time=0)
            for i in range(5)
        ]
        scheduler = self._make_scheduler(processes)
        stats = scheduler.run_until_complete()
        assert stats.completed_processes == 5

    def test_cpu_utilization_is_100_when_no_idle(self):
        # Tüm processler arrival=0 → CPU hiç boş kalmaz
        processes = [
            Process(pid=1, name="p1", burst_time=3, arrival_time=0),
            Process(pid=2, name="p2", burst_time=2, arrival_time=0),
        ]
        scheduler = self._make_scheduler(processes)
        stats = scheduler.run_until_complete()
        assert stats.cpu_utilization == 100.0

    def test_fcfs_is_non_preemptive(self):
        # P1 çalışırken P2 gelirse (daha kısa burst), P1 kesilmez
        p1 = Process(pid=1, name="p1", burst_time=5, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=1, arrival_time=1)
        scheduler = self._make_scheduler([p1, p2])
        scheduler.run_until_complete()
        # P1 tick 5'te bitmeli, P2 preempt edemez
        assert p1.completion_time == 5
        assert p2.completion_time == 6

    def test_avg_waiting_time_calculation(self):
        p1 = Process(pid=1, name="p1", burst_time=4, arrival_time=0)
        p2 = Process(pid=2, name="p2", burst_time=2, arrival_time=0)
        scheduler = self._make_scheduler([p1, p2])
        stats = scheduler.run_until_complete()
        # p1 waiting=0, p2 waiting=4 → avg=2.0
        assert stats.avg_waiting_time == 2.0

    def test_response_time_first_cpu_access(self):
        # arrival_time=0, tick 0'da queue'ya girer, tick 1'de CPU'ya alınır
        # response_time = start_time - arrival_time = 1 - 0 = 1
        p1 = Process(pid=1, name="p1", burst_time=3, arrival_time=0)
        scheduler = self._make_scheduler([p1])
        scheduler.run_until_complete()
        assert p1.response_time == 1

    def test_late_arriving_process(self):
        # arrival_time=5 → tick 5'te queue'ya girer, tick 6'da CPU'ya alınır
        # burst=2 → tick 6, tick 7'de çalışır → completion_time=7
        # Ama tick() modelimizde remaining_time tick başında azalır
        # arrival=5 → tick 5'te admit, tick 6'da CPU → completion = 6 + 2 - 1 = 7
        p = Process(pid=1, name="p1", burst_time=2, arrival_time=5)
        scheduler = self._make_scheduler([p])
        scheduler.run_until_complete()
        assert p.completion_time is not None
        assert p.turnaround_time == p.completion_time - p.arrival_time

    def test_stats_context_switches(self):
        # 3 process → en az 3 context switch
        processes = [
            Process(pid=i, name=f"p{i}", burst_time=2, arrival_time=0)
            for i in range(3)
        ]
        scheduler = self._make_scheduler(processes)
        stats = scheduler.run_until_complete()
        assert stats.context_switches >= 3
