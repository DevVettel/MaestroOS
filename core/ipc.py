"""
IPC & Senkronizasyon — Hafta 9.

Modüller:
  - Pipe:            Tek yönlü byte kanalı (producer → consumer)
  - MessageQueue:    Mesaj bazlı kuyruk (öncelik destekli)
  - Semaphore:       Sayaç tabanlı senkronizasyon primitive
  - Mutex:           Binary semaphore (karşılıklı dışlama)
  - Monitor:         Condition variable + mutex birleşimi
  - ClassicProblems: Producer-Consumer, Readers-Writers, Dining Philosophers
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Pipe
# ---------------------------------------------------------------------------

class PipeClosedError(Exception):
    """Kapalı bir pipe'a yazma/okuma girişiminde fırlatılır."""


class Pipe:
    """
    Tek yönlü, senkron pipe.

    Gerçek POSIX pipe semantiği: write ucu kapanınca okuma EOF döner,
    read ucu kapanınca yazma hata verir.

    Args:
        capacity: Pipe'ın tutabileceği maksimum eleman sayısı (0 = sınırsız)
    """

    def __init__(self, capacity: int = 0) -> None:
        self._buffer: deque[bytes] = deque()
        self._capacity = capacity
        self._write_closed = False
        self._read_closed = False

    # ------------------------------------------------------------------
    # Write ucu
    # ------------------------------------------------------------------

    def write(self, data: bytes) -> None:
        """
        Pipe'a veri yazar.

        Args:
            data: Yazılacak byte verisi

        Raises:
            PipeClosedError: Read veya write ucu kapalıysa
            BufferError: Pipe kapasitesi doluysa
        """
        if self._write_closed:
            raise PipeClosedError("Write ucu kapalı")
        if self._read_closed:
            raise PipeClosedError("Read ucu kapalı; hiç kimse okumayacak")
        if self._capacity > 0 and len(self._buffer) >= self._capacity:
            raise BufferError(f"Pipe kapasitesi dolu ({self._capacity})")
        self._buffer.append(data)

    def close_write(self) -> None:
        """Write ucunu kapatır. Artık veri yazılamaz."""
        self._write_closed = True

    # ------------------------------------------------------------------
    # Read ucu
    # ------------------------------------------------------------------

    def read(self) -> Optional[bytes]:
        """
        Pipe'tan bir eleman okur.

        Returns:
            Bytes verisi, ya da pipe boşsa ve write ucu kapalıysa None (EOF).

        Raises:
            PipeClosedError: Read ucu kapalıysa
        """
        if self._read_closed:
            raise PipeClosedError("Read ucu kapalı")
        if self._buffer:
            return self._buffer.popleft()
        if self._write_closed:
            return None  # EOF
        return None  # Henüz veri yok (non-blocking)

    def close_read(self) -> None:
        """Read ucunu kapatır."""
        self._read_closed = True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    @property
    def size(self) -> int:
        return len(self._buffer)

    def __repr__(self) -> str:
        return (
            f"Pipe(size={self.size}, capacity={self._capacity}, "
            f"write_closed={self._write_closed}, read_closed={self._read_closed})"
        )


# ---------------------------------------------------------------------------
# MessageQueue
# ---------------------------------------------------------------------------

@dataclass(order=True)
class Message:
    """
    Mesaj kuyruğu öğesi.

    priority alanı sıralama için kullanılır; düşük sayı = yüksek öncelik.
    payload sıralamayı etkilemez.
    """
    priority: int
    sender_pid: int = field(compare=False)
    payload: Any = field(compare=False)


class MessageQueue:
    """
    Öncelik destekli mesaj kuyruğu.

    Aynı öncelik seviyesindeki mesajlar FIFO sırasıyla okunur.

    Args:
        capacity: Maksimum mesaj sayısı (0 = sınırsız)
    """

    def __init__(self, capacity: int = 0) -> None:
        self._queue: list[Message] = []
        self._capacity = capacity
        self._sequence = 0  # FIFO dengesi için tiebreaker

    def send(self, sender_pid: int, payload: Any, priority: int = 0) -> None:
        """
        Kuyruğa mesaj ekler.

        Args:
            sender_pid: Gönderen process PID
            payload:    Mesaj içeriği (herhangi bir Python nesnesi)
            priority:   Mesaj önceliği (0 = en yüksek)

        Raises:
            BufferError: Kapasite doluysa
        """
        if self._capacity > 0 and len(self._queue) >= self._capacity:
            raise BufferError(f"MessageQueue kapasitesi dolu ({self._capacity})")
        # (priority, sequence) tuple'ı FIFO + priority düzenini sağlar
        msg = Message(priority=priority, sender_pid=sender_pid, payload=payload)
        # Manuel insertion sort (küçük kuyruklar için yeterli)
        inserted = False
        for i, existing in enumerate(self._queue):
            if (msg.priority, self._sequence) < (existing.priority, i):
                self._queue.insert(i, msg)
                inserted = True
                break
        if not inserted:
            self._queue.append(msg)
        self._sequence += 1

    def receive(self) -> Optional[Message]:
        """
        En yüksek öncelikli mesajı kuyruktan çıkarır.

        Returns:
            Message nesnesi, ya da kuyruk boşsa None.
        """
        if not self._queue:
            return None
        return self._queue.pop(0)

    def peek(self) -> Optional[Message]:
        """Kuyruktaki ilk mesajı çıkarmadan döner."""
        return self._queue[0] if self._queue else None

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def size(self) -> int:
        return len(self._queue)

    def __repr__(self) -> str:
        return f"MessageQueue(size={self.size}, capacity={self._capacity})"


# ---------------------------------------------------------------------------
# Semaphore
# ---------------------------------------------------------------------------

class Semaphore:
    """
    Sayaç tabanlı senkronizasyon primitive.

    Edsger Dijkstra'nın P/V (wait/signal) operasyonları.
    Bu implementasyon non-blocking: wait() başarısızsa False döner.

    Args:
        initial_value: Başlangıç sayaç değeri (≥ 0)
    """

    def __init__(self, initial_value: int = 1) -> None:
        if initial_value < 0:
            raise ValueError(f"Semaphore başlangıç değeri negatif olamaz: {initial_value}")
        self._value = initial_value
        self._waiting: deque[int] = deque()  # Bekleyen process pid'leri

    def wait(self, pid: int = -1) -> bool:
        """
        P (proberen) operasyonu: değeri azalt, 0'daysa blokla.

        Args:
            pid: İşlemi yapan process PID (-1 = anonim)

        Returns:
            True → kaynak edinildi; False → bloklandı (kuyruğa eklendi)
        """
        if self._value > 0:
            self._value -= 1
            return True
        if pid != -1:
            self._waiting.append(pid)
        return False

    def signal(self) -> Optional[int]:
        """
        V (verhogen) operasyonu: değeri artır ya da bekleyen process'i uyandır.

        Returns:
            Uyandırılan process'in PID'i, yoksa None.
        """
        if self._waiting:
            woken = self._waiting.popleft()
            # Değer artmaz; kaynak doğrudan uyandırılan process'e geçer
            return woken
        self._value += 1
        return None

    @property
    def value(self) -> int:
        return self._value

    @property
    def waiting_count(self) -> int:
        return len(self._waiting)

    def __repr__(self) -> str:
        return f"Semaphore(value={self._value}, waiting={self.waiting_count})"


# ---------------------------------------------------------------------------
# Mutex
# ---------------------------------------------------------------------------

class MutexError(Exception):
    """Mutex protokolü ihlalinde fırlatılır."""


class Mutex:
    """
    Binary semaphore — karşılıklı dışlama kilidi.

    Mutex'i kilitleyen process onu açmak zorundadır (ownership semantiği).

    Args:
        name: Mutex'in okunabilir adı (debug için)
    """

    def __init__(self, name: str = "mutex") -> None:
        self.name = name
        self._owner: Optional[int] = None  # Kilidi tutan process PID
        self._waiting: deque[int] = deque()

    def acquire(self, pid: int) -> bool:
        """
        Kilidi edinmeye çalışır.

        Args:
            pid: Kilidi isteyen process PID

        Returns:
            True → kilit edinildi; False → bloklandı
        """
        if self._owner is None:
            self._owner = pid
            return True
        self._waiting.append(pid)
        return False

    def release(self, pid: int) -> Optional[int]:
        """
        Kilidi serbest bırakır.

        Args:
            pid: Kilidi bırakan process PID

        Returns:
            Kilidi devralan process PID, yoksa None.

        Raises:
            MutexError: Kilidi tutmayan process release yapmaya çalışırsa
        """
        if self._owner != pid:
            raise MutexError(
                f"PID {pid} mutex'i serbest bırakamaz; sahibi PID {self._owner}"
            )
        if self._waiting:
            self._owner = self._waiting.popleft()
            return self._owner
        self._owner = None
        return None

    @property
    def is_locked(self) -> bool:
        return self._owner is not None

    @property
    def owner(self) -> Optional[int]:
        return self._owner

    @property
    def waiting_count(self) -> int:
        return len(self._waiting)

    def __repr__(self) -> str:
        return f"Mutex(name='{self.name}', owner={self._owner}, waiting={self.waiting_count})"


# ---------------------------------------------------------------------------
# Monitor (Condition Variable + Mutex)
# ---------------------------------------------------------------------------

class ConditionVariable:
    """
    Monitor'ün bileşeni: condition variable.

    Process'ler bir koşul gerçekleşene kadar wait() ile beklemeye alınır,
    notify()/notify_all() ile uyandırılır.
    """

    def __init__(self, name: str = "cond") -> None:
        self.name = name
        self._waiting: deque[int] = deque()

    def wait(self, pid: int) -> None:
        """Process'i bekleme kuyruğuna ekler."""
        self._waiting.append(pid)

    def notify(self) -> Optional[int]:
        """Tek bir bekleyen process'i uyandırır."""
        if self._waiting:
            return self._waiting.popleft()
        return None

    def notify_all(self) -> list[int]:
        """Tüm bekleyen process'leri uyandırır."""
        woken = list(self._waiting)
        self._waiting.clear()
        return woken

    @property
    def waiting_count(self) -> int:
        return len(self._waiting)

    def __repr__(self) -> str:
        return f"ConditionVariable(name='{self.name}', waiting={self.waiting_count})"


class Monitor:
    """
    Monitor senkronizasyon yapısı.

    Bir mutex + bir ya da daha fazla condition variable.
    Critical section'a girilmesi için mutex edinilmesi gerekir.

    Args:
        name: Monitor adı
    """

    def __init__(self, name: str = "monitor") -> None:
        self.name = name
        self.mutex = Mutex(name=f"{name}_mutex")
        self._conditions: dict[str, ConditionVariable] = {}

    def condition(self, name: str) -> ConditionVariable:
        """İsme göre condition variable döner; yoksa oluşturur."""
        if name not in self._conditions:
            self._conditions[name] = ConditionVariable(name=name)
        return self._conditions[name]

    def enter(self, pid: int) -> bool:
        """Monitor'e girmeye çalışır (mutex acquire)."""
        return self.mutex.acquire(pid)

    def exit(self, pid: int) -> Optional[int]:
        """Monitor'den çıkar (mutex release)."""
        return self.mutex.release(pid)

    def __repr__(self) -> str:
        return f"Monitor(name='{self.name}', locked={self.mutex.is_locked})"


# ---------------------------------------------------------------------------
# Klasik IPC Problemleri
# ---------------------------------------------------------------------------

class ProducerConsumer:
    """
    Sınırlı tampon Producer-Consumer problemi.

    Bir semaphore (empty), bir semaphore (full) ve bir mutex ile
    N slotlu shared buffer yönetilir.

    Args:
        buffer_size: Shared buffer kapasitesi
    """

    def __init__(self, buffer_size: int) -> None:
        if buffer_size <= 0:
            raise ValueError("buffer_size pozitif olmalı")
        self.buffer_size = buffer_size
        self._buffer: deque[Any] = deque()
        self.empty = Semaphore(buffer_size)   # Boş slot sayısı
        self.full = Semaphore(0)              # Dolu slot sayısı
        self.mutex = Mutex("pc_mutex")
        self._produced = 0
        self._consumed = 0

    def produce(self, pid: int, item: Any) -> bool:
        """
        Buffer'a öğe ekler.

        Returns:
            True → başarılı; False → buffer dolu (producer bloklandı)
        """
        if not self.empty.wait(pid):
            return False  # Buffer dolu

        acquired = self.mutex.acquire(pid)
        if not acquired:
            # Critical section meşgul — gerçek OS'ta bloklanırdı
            self.empty.signal()
            return False

        self._buffer.append(item)
        self._produced += 1
        self.mutex.release(pid)
        self.full.signal()
        return True

    def consume(self, pid: int) -> tuple[bool, Any]:
        """
        Buffer'dan öğe çıkarır.

        Returns:
            (True, item) → başarılı; (False, None) → buffer boş (consumer bloklandı)
        """
        if not self.full.wait(pid):
            return False, None  # Buffer boş

        acquired = self.mutex.acquire(pid)
        if not acquired:
            self.full.signal()
            return False, None

        item = self._buffer.popleft()
        self._consumed += 1
        self.mutex.release(pid)
        self.empty.signal()
        return True, item

    @property
    def buffer_contents(self) -> list[Any]:
        return list(self._buffer)

    @property
    def stats(self) -> dict[str, int]:
        return {
            "produced": self._produced,
            "consumed": self._consumed,
            "in_buffer": len(self._buffer),
        }


class ReadersWriters:
    """
    Readers-Writers problemi (Reader-öncelikli çözüm).

    Birden fazla reader eş zamanlı okuyabilir; writer exclusive erişim ister.
    Bu çözüm writer starvation'a yol açabilir (kasıtlı — klasik varyant).

    Attributes:
        read_count:    Şu an okuyan reader sayısı
        writer_active: Writer aktif mi
    """

    def __init__(self) -> None:
        self.read_count = 0
        self.writer_active = False
        self._mutex = Mutex("rw_count_mutex")   # read_count koruması
        self._write_sem = Semaphore(1)           # Writer exclusive erişim
        self._readers: set[int] = set()
        self._waiting_writers: deque[int] = deque()

    def start_read(self, pid: int) -> bool:
        """
        Reader okumaya başlar.

        Returns:
            True → okuma başladı; False → mutex meşgul (bloklandı)
        """
        if not self._mutex.acquire(pid):
            return False

        self.read_count += 1
        self._readers.add(pid)

        if self.read_count == 1:
            # İlk reader — writer'ları blokla
            if not self._write_sem.wait(pid):
                self.read_count -= 1
                self._readers.discard(pid)
                self._mutex.release(pid)
                return False

        self._mutex.release(pid)
        return True

    def end_read(self, pid: int) -> bool:
        """
        Reader okumayı bitirir.

        Returns:
            True → başarılı; False → bu pid okumada değildi
        """
        if pid not in self._readers:
            return False

        if not self._mutex.acquire(pid):
            return False

        self._readers.discard(pid)
        self.read_count -= 1

        if self.read_count == 0:
            # Son reader — writer'ları serbest bırak
            self._write_sem.signal()

        self._mutex.release(pid)
        return True

    def start_write(self, pid: int) -> bool:
        """
        Writer exclusive erişim ister.

        Returns:
            True → yazma başladı; False → bloklandı
        """
        acquired = self._write_sem.wait(pid)
        if acquired:
            self.writer_active = True
        else:
            self._waiting_writers.append(pid)
        return acquired

    def end_write(self, pid: int) -> Optional[int]:
        """
        Writer exclusive erişimi bırakır.

        Returns:
            Uyandırılan process PID, yoksa None.
        """
        self.writer_active = False
        return self._write_sem.signal()

    @property
    def active_readers(self) -> set[int]:
        return set(self._readers)


class PhilosopherState(Enum):
    THINKING = auto()
    HUNGRY   = auto()
    EATING   = auto()


class DiningPhilosophers:
    """
    Dining Philosophers problemi (Chandy/Misra token-ring çözümü).

    N filozof, N çatal. Deadlock'tan kaçınmak için:
    - Çift numaralı filozoflar önce sol, sonra sağ çatalı alır.
    - Tek numaralı filozoflar önce sağ, sonra sol çatalı alır.
    (Asimetrik çözüm — deadlock-free, starvation-free değil ama pratikte yeterli)

    Args:
        n: Filozof (ve çatal) sayısı
    """

    def __init__(self, n: int) -> None:
        if n < 2:
            raise ValueError("En az 2 filozof gerekli")
        self.n = n
        self.states: list[PhilosopherState] = [PhilosopherState.THINKING] * n
        # Her çatal için mutex
        self._forks: list[Mutex] = [Mutex(f"fork_{i}") for i in range(n)]
        self._history: list[tuple[int, str]] = []  # (philosopher_id, event)

    def _fork_order(self, i: int) -> tuple[int, int]:
        """Deadlock-free çatal alma sırası."""
        left = i
        right = (i + 1) % self.n
        if i % 2 == 0:
            return left, right   # Çift: sol önce
        return right, left       # Tek: sağ önce

    def think(self, i: int) -> None:
        """Filozof i düşünüyor."""
        self.states[i] = PhilosopherState.THINKING
        self._history.append((i, "think"))

    def pick_up_forks(self, i: int) -> bool:
        """
        Filozof i çatal almaya çalışır.

        Returns:
            True → her iki çatal alındı, yemek başlayabilir.
            False → bir çatal meşgul, bekleniyor.
        """
        self.states[i] = PhilosopherState.HUNGRY
        first, second = self._fork_order(i)

        if not self._forks[first].acquire(i):
            return False

        if not self._forks[second].acquire(i):
            self._forks[first].release(i)
            self.states[i] = PhilosopherState.THINKING
            return False

        self.states[i] = PhilosopherState.EATING
        self._history.append((i, "eat"))
        return True

    def put_down_forks(self, i: int) -> None:
        """Filozof i çatalları bırakır."""
        first, second = self._fork_order(i)
        self._forks[second].release(i)
        self._forks[first].release(i)
        self.states[i] = PhilosopherState.THINKING
        self._history.append((i, "put_down"))

    @property
    def eating_philosophers(self) -> list[int]:
        return [i for i, s in enumerate(self.states) if s == PhilosopherState.EATING]

    @property
    def history(self) -> list[tuple[int, str]]:
        return list(self._history)
