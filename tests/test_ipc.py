"""
Hafta 9 testleri — IPC & Senkronizasyon.

Çalıştır: PYTHONPATH=. pytest tests/test_ipc.py -v
"""

import pytest

from core.ipc import (
    ConditionVariable,
    DiningPhilosophers,
    Message,
    MessageQueue,
    Monitor,
    Mutex,
    MutexError,
    PhilosopherState,
    Pipe,
    PipeClosedError,
    ProducerConsumer,
    ReadersWriters,
    Semaphore,
)


# ===========================================================================
# Pipe
# ===========================================================================

class TestPipe:
    def test_write_and_read(self):
        p = Pipe()
        p.write(b"hello")
        assert p.read() == b"hello"

    def test_fifo_order(self):
        p = Pipe()
        p.write(b"a")
        p.write(b"b")
        p.write(b"c")
        assert p.read() == b"a"
        assert p.read() == b"b"
        assert p.read() == b"c"

    def test_read_empty_returns_none(self):
        p = Pipe()
        assert p.read() is None

    def test_read_after_write_closed_returns_none_eof(self):
        p = Pipe()
        p.write(b"x")
        p.close_write()
        assert p.read() == b"x"
        assert p.read() is None  # EOF

    def test_write_after_close_raises(self):
        p = Pipe()
        p.close_write()
        with pytest.raises(PipeClosedError):
            p.write(b"fail")

    def test_write_to_closed_read_raises(self):
        p = Pipe()
        p.close_read()
        with pytest.raises(PipeClosedError):
            p.write(b"fail")

    def test_read_after_close_read_raises(self):
        p = Pipe()
        p.write(b"x")
        p.close_read()
        with pytest.raises(PipeClosedError):
            p.read()

    def test_capacity_limit(self):
        p = Pipe(capacity=2)
        p.write(b"1")
        p.write(b"2")
        with pytest.raises(BufferError):
            p.write(b"3")

    def test_size_property(self):
        p = Pipe()
        assert p.size == 0
        p.write(b"a")
        assert p.size == 1

    def test_is_empty(self):
        p = Pipe()
        assert p.is_empty
        p.write(b"x")
        assert not p.is_empty

    def test_repr(self):
        p = Pipe(capacity=5)
        assert "Pipe" in repr(p)
        assert "capacity=5" in repr(p)


# ===========================================================================
# MessageQueue
# ===========================================================================

class TestMessageQueue:
    def test_send_and_receive(self):
        mq = MessageQueue()
        mq.send(sender_pid=1, payload="hello")
        msg = mq.receive()
        assert msg is not None
        assert msg.payload == "hello"
        assert msg.sender_pid == 1

    def test_receive_empty_returns_none(self):
        mq = MessageQueue()
        assert mq.receive() is None

    def test_priority_ordering(self):
        mq = MessageQueue()
        mq.send(sender_pid=1, payload="low", priority=5)
        mq.send(sender_pid=2, payload="high", priority=0)
        mq.send(sender_pid=3, payload="mid", priority=3)
        assert mq.receive().payload == "high"
        assert mq.receive().payload == "mid"
        assert mq.receive().payload == "low"

    def test_same_priority_fifo(self):
        mq = MessageQueue()
        mq.send(1, "first", priority=1)
        mq.send(2, "second", priority=1)
        assert mq.receive().payload == "first"
        assert mq.receive().payload == "second"

    def test_capacity_limit(self):
        mq = MessageQueue(capacity=2)
        mq.send(1, "a")
        mq.send(1, "b")
        with pytest.raises(BufferError):
            mq.send(1, "c")

    def test_peek_does_not_remove(self):
        mq = MessageQueue()
        mq.send(1, "x")
        assert mq.peek().payload == "x"
        assert mq.size == 1

    def test_is_empty(self):
        mq = MessageQueue()
        assert mq.is_empty
        mq.send(1, "x")
        assert not mq.is_empty

    def test_message_dataclass_order(self):
        m1 = Message(priority=0, sender_pid=1, payload="high")
        m2 = Message(priority=5, sender_pid=2, payload="low")
        assert m1 < m2

    def test_repr(self):
        mq = MessageQueue(capacity=10)
        assert "MessageQueue" in repr(mq)


# ===========================================================================
# Semaphore
# ===========================================================================

class TestSemaphore:
    def test_initial_value(self):
        s = Semaphore(3)
        assert s.value == 3

    def test_wait_decrements(self):
        s = Semaphore(2)
        assert s.wait() is True
        assert s.value == 1

    def test_wait_blocks_at_zero(self):
        s = Semaphore(1)
        assert s.wait() is True
        result = s.wait(pid=42)
        assert result is False
        assert s.waiting_count == 1

    def test_signal_increments(self):
        s = Semaphore(0)
        s.signal()
        assert s.value == 1

    def test_signal_wakes_waiting_process(self):
        s = Semaphore(0)
        s.wait(pid=10)
        woken = s.signal()
        assert woken == 10
        assert s.value == 0  # Kaynak doğrudan geçti
        assert s.waiting_count == 0

    def test_signal_no_waiters_returns_none(self):
        s = Semaphore(1)
        assert s.signal() is None

    def test_negative_initial_raises(self):
        with pytest.raises(ValueError):
            Semaphore(-1)

    def test_fifo_wakeup_order(self):
        s = Semaphore(0)
        s.wait(pid=1)
        s.wait(pid=2)
        s.wait(pid=3)
        assert s.signal() == 1
        assert s.signal() == 2
        assert s.signal() == 3

    def test_binary_semaphore(self):
        s = Semaphore(1)
        assert s.wait() is True
        assert s.value == 0
        assert s.wait(pid=5) is False   # Bloklandı, kuyruğa eklendi
        woken = s.signal()
        assert woken == 5               # Kaynak doğrudan pid 5'e geçti
        assert s.value == 0             # Değer artmadı (waiter aldı)

    def test_repr(self):
        s = Semaphore(2)
        assert "Semaphore" in repr(s)
        assert "value=2" in repr(s)


# ===========================================================================
# Mutex
# ===========================================================================

class TestMutex:
    def test_initial_unlocked(self):
        m = Mutex()
        assert not m.is_locked
        assert m.owner is None

    def test_acquire_locks(self):
        m = Mutex()
        result = m.acquire(pid=1)
        assert result is True
        assert m.is_locked
        assert m.owner == 1

    def test_second_acquire_blocks(self):
        m = Mutex()
        m.acquire(pid=1)
        result = m.acquire(pid=2)
        assert result is False
        assert m.waiting_count == 1

    def test_release_unlocks(self):
        m = Mutex()
        m.acquire(pid=1)
        m.release(pid=1)
        assert not m.is_locked

    def test_release_wakes_next(self):
        m = Mutex()
        m.acquire(pid=1)
        m.acquire(pid=2)
        next_owner = m.release(pid=1)
        assert next_owner == 2
        assert m.owner == 2

    def test_release_by_non_owner_raises(self):
        m = Mutex()
        m.acquire(pid=1)
        with pytest.raises(MutexError):
            m.release(pid=99)

    def test_release_when_no_waiters_returns_none(self):
        m = Mutex()
        m.acquire(pid=1)
        result = m.release(pid=1)
        assert result is None

    def test_repr(self):
        m = Mutex(name="test_mutex")
        assert "test_mutex" in repr(m)


# ===========================================================================
# ConditionVariable
# ===========================================================================

class TestConditionVariable:
    def test_wait_adds_to_queue(self):
        cv = ConditionVariable()
        cv.wait(pid=1)
        assert cv.waiting_count == 1

    def test_notify_wakes_one(self):
        cv = ConditionVariable()
        cv.wait(pid=1)
        cv.wait(pid=2)
        woken = cv.notify()
        assert woken == 1
        assert cv.waiting_count == 1

    def test_notify_empty_returns_none(self):
        cv = ConditionVariable()
        assert cv.notify() is None

    def test_notify_all(self):
        cv = ConditionVariable()
        cv.wait(1)
        cv.wait(2)
        cv.wait(3)
        woken = cv.notify_all()
        assert sorted(woken) == [1, 2, 3]
        assert cv.waiting_count == 0


# ===========================================================================
# Monitor
# ===========================================================================

class TestMonitor:
    def test_enter_acquires_mutex(self):
        mon = Monitor("test")
        assert mon.enter(pid=1) is True
        assert mon.mutex.is_locked

    def test_exit_releases_mutex(self):
        mon = Monitor("test")
        mon.enter(pid=1)
        mon.exit(pid=1)
        assert not mon.mutex.is_locked

    def test_condition_created_on_demand(self):
        mon = Monitor("test")
        cv = mon.condition("not_empty")
        assert cv.name == "not_empty"

    def test_same_condition_returned(self):
        mon = Monitor("test")
        c1 = mon.condition("x")
        c2 = mon.condition("x")
        assert c1 is c2

    def test_monitor_repr(self):
        mon = Monitor("mymon")
        assert "mymon" in repr(mon)


# ===========================================================================
# ProducerConsumer
# ===========================================================================

class TestProducerConsumer:
    def test_basic_produce_consume(self):
        pc = ProducerConsumer(buffer_size=3)
        assert pc.produce(pid=1, item="item1") is True
        ok, item = pc.consume(pid=2)
        assert ok is True
        assert item == "item1"

    def test_full_buffer_blocks_producer(self):
        pc = ProducerConsumer(buffer_size=2)
        pc.produce(pid=1, item="a")
        pc.produce(pid=1, item="b")
        result = pc.produce(pid=1, item="c")
        assert result is False

    def test_empty_buffer_blocks_consumer(self):
        pc = ProducerConsumer(buffer_size=2)
        ok, item = pc.consume(pid=2)
        assert ok is False
        assert item is None

    def test_fifo_order(self):
        pc = ProducerConsumer(buffer_size=5)
        for i in range(3):
            pc.produce(pid=1, item=i)
        for i in range(3):
            _, item = pc.consume(pid=2)
            assert item == i

    def test_stats_tracking(self):
        pc = ProducerConsumer(buffer_size=5)
        pc.produce(1, "x")
        pc.produce(1, "y")
        pc.consume(2)
        s = pc.stats
        assert s["produced"] == 2
        assert s["consumed"] == 1
        assert s["in_buffer"] == 1

    def test_invalid_buffer_size(self):
        with pytest.raises(ValueError):
            ProducerConsumer(buffer_size=0)

    def test_buffer_contents(self):
        pc = ProducerConsumer(buffer_size=3)
        pc.produce(1, "a")
        pc.produce(1, "b")
        assert pc.buffer_contents == ["a", "b"]


# ===========================================================================
# ReadersWriters
# ===========================================================================

class TestReadersWriters:
    def test_single_reader(self):
        rw = ReadersWriters()
        assert rw.start_read(pid=1) is True
        assert 1 in rw.active_readers
        assert rw.end_read(pid=1) is True

    def test_multiple_readers_concurrent(self):
        rw = ReadersWriters()
        assert rw.start_read(pid=1) is True
        assert rw.start_read(pid=2) is True
        assert len(rw.active_readers) == 2

    def test_single_writer(self):
        rw = ReadersWriters()
        assert rw.start_write(pid=10) is True
        assert rw.writer_active is True
        rw.end_write(pid=10)
        assert rw.writer_active is False

    def test_writer_blocks_second_writer(self):
        rw = ReadersWriters()
        rw.start_write(pid=10)
        result = rw.start_write(pid=11)
        assert result is False

    def test_end_read_unknown_pid_returns_false(self):
        rw = ReadersWriters()
        result = rw.end_read(pid=999)
        assert result is False

    def test_read_count_tracks_readers(self):
        rw = ReadersWriters()
        rw.start_read(1)
        rw.start_read(2)
        assert rw.read_count == 2
        rw.end_read(1)
        assert rw.read_count == 1

    def test_end_write_signals_semaphore(self):
        rw = ReadersWriters()
        rw.start_write(pid=1)
        rw.end_write(pid=1)
        # Bir sonraki writer başlayabilmeli
        assert rw.start_write(pid=2) is True


# ===========================================================================
# DiningPhilosophers
# ===========================================================================

class TestDiningPhilosophers:
    def test_initial_all_thinking(self):
        dp = DiningPhilosophers(5)
        assert all(s == PhilosopherState.THINKING for s in dp.states)

    def test_philosopher_eats(self):
        dp = DiningPhilosophers(5)
        result = dp.pick_up_forks(0)
        assert result is True
        assert dp.states[0] == PhilosopherState.EATING

    def test_adjacent_philosophers_cannot_eat_simultaneously(self):
        dp = DiningPhilosophers(5)
        dp.pick_up_forks(0)
        # Komşu filozoflar (1 ve 4) aynı çatalı paylaşıyor
        result_1 = dp.pick_up_forks(1)
        result_4 = dp.pick_up_forks(4)
        # En az biri bloklanmalı
        assert not (result_1 and result_4), (
            "Komşu filozoflar aynı anda yemek yiyemez"
        )

    def test_non_adjacent_philosophers_can_eat(self):
        dp = DiningPhilosophers(5)
        ok_0 = dp.pick_up_forks(0)
        ok_2 = dp.pick_up_forks(2)
        assert ok_0 and ok_2

    def test_put_down_releases_forks(self):
        dp = DiningPhilosophers(5)
        dp.pick_up_forks(0)
        dp.put_down_forks(0)
        assert dp.states[0] == PhilosopherState.THINKING
        # Komşu artık alabilmeli
        assert dp.pick_up_forks(1) is True

    def test_think_sets_state(self):
        dp = DiningPhilosophers(5)
        dp.states[0] = PhilosopherState.EATING
        dp.think(0)
        assert dp.states[0] == PhilosopherState.THINKING

    def test_history_recorded(self):
        dp = DiningPhilosophers(5)
        dp.pick_up_forks(0)
        dp.put_down_forks(0)
        events = [e for _, e in dp.history]
        assert "eat" in events
        assert "put_down" in events

    def test_eating_philosophers_list(self):
        dp = DiningPhilosophers(5)
        dp.pick_up_forks(0)
        dp.pick_up_forks(2)
        eating = dp.eating_philosophers
        assert 0 in eating
        assert 2 in eating

    def test_minimum_philosophers(self):
        dp = DiningPhilosophers(2)
        assert dp.n == 2

    def test_invalid_philosopher_count(self):
        with pytest.raises(ValueError):
            DiningPhilosophers(1)

    def test_no_deadlock_sequential_meals(self):
        """5 filozofun sırayla yemek yiyip bırakması deadlock olmadan tamamlanmalı."""
        dp = DiningPhilosophers(5)
        for i in range(5):
            ok = dp.pick_up_forks(i)
            if ok:
                dp.put_down_forks(i)
        # Sonunda tüm filozoflar düşünüyor olmalı
        eating = dp.eating_philosophers
        assert len(eating) == 0
