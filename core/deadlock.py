"""
Deadlock Detection & Avoidance — Hafta 8.

İki temel modül:
  - ResourceAllocationGraph: RAG tabanlı DFS döngü tespiti
  - BankersAlgorithm: Banker's Algorithm ile güvenli durum analizi
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Resource dataclass
# ---------------------------------------------------------------------------

@dataclass
class Resource:
    """
    Sistemdeki bir kaynak tipini temsil eder.

    Args:
        rid: Kaynak kimliği (benzersiz tam sayı)
        name: Okunabilir kaynak adı (ör. "Printer", "CPU")
        total_instances: Kaynağın toplam örnek sayısı
        available_instances: Şu an atanmamış, kullanılabilir örnek sayısı
    """
    rid: int
    name: str
    total_instances: int
    available_instances: int


# ---------------------------------------------------------------------------
# ResourceAllocationGraph
# ---------------------------------------------------------------------------

class ResourceAllocationGraph:
    """
    Kaynak Atama Grafiği (Resource Allocation Graph — RAG).

    Kenar türleri:
      - İstek kenarı (request edge):   P → R   (process kaynak istiyor)
      - Atama kenarı (assignment edge): R → P   (kaynak process'e atandı)

    Deadlock tespiti için wait-for grafiği üzerinde DFS ile döngü aranır.
    P1 → P2 wait-for kenarı: P1, P2'nin tuttuğu bir kaynağı bekliyor.
    """

    def __init__(self) -> None:
        """Boş bir RAG oluşturur."""
        self._processes: set[int] = set()
        self._resources: dict[int, Resource] = {}
        # pid → set of rids (process bu kaynakları talep ediyor)
        self._request_edges: dict[int, set[int]] = {}
        # pid → set of rids (process bu kaynakları elinde tutuyor)
        self._assignment_edges: dict[int, set[int]] = {}

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def add_resource(self, rid: int, name: str, total_instances: int) -> None:
        """
        Grafa yeni bir kaynak ekler.

        Args:
            rid: Kaynağa atanacak benzersiz kimlik
            name: Kaynağın okunabilir adı
            total_instances: Kaynağın toplam örnek sayısı
        """
        self._resources[rid] = Resource(
            rid=rid,
            name=name,
            total_instances=total_instances,
            available_instances=total_instances,
        )

    def add_process(self, pid: int) -> None:
        """
        Grafa yeni bir process ekler.

        Args:
            pid: Process kimliği (benzersiz tam sayı)
        """
        self._processes.add(pid)
        self._request_edges.setdefault(pid, set())
        self._assignment_edges.setdefault(pid, set())

    def request_edge(self, pid: int, rid: int) -> None:
        """
        P → R istek kenarı ekler: process, kaynağı talep ediyor.

        Args:
            pid: Kaynağı talep eden process kimliği
            rid: Talep edilen kaynak kimliği
        """
        self._request_edges[pid].add(rid)

    def assignment_edge(self, pid: int, rid: int) -> None:
        """
        R → P atama kenarı ekler: kaynak, process'e atandı.

        available_instances'ı 1 azaltır.

        Args:
            pid: Kaynağı alan process kimliği
            rid: Atanan kaynak kimliği
        """
        self._assignment_edges[pid].add(rid)
        self._resources[rid].available_instances -= 1

    def release(self, pid: int, rid: int) -> None:
        """
        Process'in elindeki kaynağı serbest bırakır.

        Atama kenarını kaldırır, available_instances'ı 1 artırır.

        Args:
            pid: Kaynağı serbest bırakan process kimliği
            rid: Serbest bırakılan kaynak kimliği
        """
        if rid in self._assignment_edges.get(pid, set()):
            self._assignment_edges[pid].discard(rid)
            self._resources[rid].available_instances += 1

    # ------------------------------------------------------------------
    # Deadlock detection
    # ------------------------------------------------------------------

    def _build_wait_for_graph(self) -> dict[int, set[int]]:
        """
        RAG'dan wait-for grafiği oluşturur.

        P1 → P2 kenarı: P1, P2'nin tuttuğu bir kaynağı bekliyor.

        Returns:
            pid → set[pid] wait-for komşuluk listesi
        """
        wait_for: dict[int, set[int]] = {pid: set() for pid in self._processes}

        for waiting_pid, requested_rids in self._request_edges.items():
            for rid in requested_rids:
                for holding_pid, held_rids in self._assignment_edges.items():
                    if rid in held_rids and holding_pid != waiting_pid:
                        wait_for[waiting_pid].add(holding_pid)

        return wait_for

    def detect_deadlock(self) -> list[int]:
        """
        Wait-for grafiğinde DFS ile döngü tespiti yapar.

        Deadlock'taki process'ler döngü içindeki process'lerdir.

        Returns:
            Deadlock'ta olan process pid'lerinin sıralı listesi.
            Deadlock yoksa boş liste döner.
        """
        wait_for = self._build_wait_for_graph()

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[int, int] = {pid: WHITE for pid in self._processes}
        deadlocked: set[int] = set()

        def dfs(pid: int, path: list[int]) -> None:
            color[pid] = GRAY
            path.append(pid)

            for neighbor in wait_for.get(pid, set()):
                if color[neighbor] == GRAY:
                    # Geri kenar bulundu → döngü tespit edildi
                    cycle_start = path.index(neighbor)
                    deadlocked.update(path[cycle_start:])
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path)

            path.pop()
            color[pid] = BLACK

        for pid in self._processes:
            if color[pid] == WHITE:
                dfs(pid, [])

        return sorted(deadlocked)

    def get_deadlocked_processes(self) -> list[int]:
        """
        detect_deadlock() için takma ad; döngüdeki process pid'lerini döner.

        Returns:
            Deadlock döngüsündeki process pid'lerinin sıralı listesi.
        """
        return self.detect_deadlock()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_resource(self, rid: int) -> Resource:
        """Kaynak nesnesini döner."""
        return self._resources[rid]

    def get_processes(self) -> set[int]:
        """Graftaki tüm process pid'lerini döner."""
        return set(self._processes)

    def get_held_resources(self, pid: int) -> set[int]:
        """Process'in elindeki kaynak rid'lerini döner."""
        return set(self._assignment_edges.get(pid, set()))

    def get_requested_resources(self, pid: int) -> set[int]:
        """Process'in talep ettiği kaynak rid'lerini döner."""
        return set(self._request_edges.get(pid, set()))


# ---------------------------------------------------------------------------
# BankersAlgorithm
# ---------------------------------------------------------------------------

class BankersAlgorithm:
    """
    Banker's Algorithm — Deadlock Avoidance.

    Sistem, bir kaynak talebini ancak talep sonrasında hâlâ güvenli bir
    durumda kalınıyorsa kabul eder. Güvenli durum: tüm process'lerin
    sonunda tamamlanabileceği en az bir yürütme sırası mevcuttur.

    Tüm işlemler saf Python liste/dict ile yapılır; numpy kullanılmaz.

    Args:
        processes:  Process pid'lerinin listesi (ör. [0, 1, 2])
        resources:  Her kaynak tipindeki toplam örnek sayısı
                    (ör. [10, 5, 7] → 3 kaynak tipi)
        allocation: pid → kaynak tipine göre tahsis miktarı
                    (ör. {0: [0,1,0], 1: [2,0,0]})
        max_demand: pid → maksimum talep miktarı
                    (ör. {0: [7,5,3], 1: [3,2,2]})
    """

    def __init__(
        self,
        processes: list[int],
        resources: list[int],
        allocation: dict[int, list[int]],
        max_demand: dict[int, list[int]],
    ) -> None:
        self.processes: list[int] = list(processes)
        self.resources: list[int] = list(resources)
        self.num_resources: int = len(resources)
        self.allocation: dict[int, list[int]] = {
            p: list(v) for p, v in allocation.items()
        }
        self.max_demand: dict[int, list[int]] = {
            p: list(v) for p, v in max_demand.items()
        }

        # Available = Total − Σ Allocation
        self.available: list[int] = list(resources)
        for pid in self.processes:
            for j in range(self.num_resources):
                self.available[j] -= self.allocation[pid][j]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _need(self, pid: int) -> list[int]:
        """
        pid'in ihtiyaç vektörünü hesaplar: Need = Max − Allocation.

        Args:
            pid: Process kimliği

        Returns:
            Her kaynak tipindeki ihtiyaç miktarı listesi
        """
        return [
            self.max_demand[pid][j] - self.allocation[pid][j]
            for j in range(self.num_resources)
        ]

    def _can_allocate(self, need: list[int], available: list[int]) -> bool:
        """need[j] <= available[j] tüm j için mi kontrol eder."""
        return all(need[j] <= available[j] for j in range(self.num_resources))

    # ------------------------------------------------------------------
    # Safety analysis
    # ------------------------------------------------------------------

    def is_safe_state(self) -> bool:
        """
        Sistemin şu anki durumunun güvenli olup olmadığını kontrol eder.

        Returns:
            True  → güvenli durum (en az bir güvenli sıra mevcut)
            False → güvensiz durum (deadlock riski var)
        """
        return self.find_safe_sequence() is not None

    def find_safe_sequence(self) -> Optional[list[int]]:
        """
        Banker's Safety Algorithm: güvenli bir yürütme sırası bulur.

        Simülasyonda available kaynakları artırarak hangi sırayla tüm
        process'lerin tamamlanabileceğini hesaplar.

        Returns:
            Güvenli sıralama mevcutsa pid listesi, yoksa None.
        """
        work: list[int] = list(self.available)
        finish: dict[int, bool] = {pid: False for pid in self.processes}
        sequence: list[int] = []

        while len(sequence) < len(self.processes):
            progress = False
            for pid in self.processes:
                if not finish[pid] and self._can_allocate(self._need(pid), work):
                    # Process tamamlanabilir; kaynaklarını geri ver
                    for j in range(self.num_resources):
                        work[j] += self.allocation[pid][j]
                    finish[pid] = True
                    sequence.append(pid)
                    progress = True
                    break  # Baştan tara (ilk uygun process yeterli)

            if not progress:
                return None  # Hiçbir process ilerleyemedi → güvensiz

        return sequence

    # ------------------------------------------------------------------
    # Resource request
    # ------------------------------------------------------------------

    def request_resources(self, pid: int, request: list[int]) -> bool:
        """
        Bir process'in kaynak talebini değerlendirir.

        Güvenlilik testi:
          1. request[j] ≤ need[j]     (maksimum talepten fazla isteyemez)
          2. request[j] ≤ available[j] (yeterli kaynak mevcut olmalı)
          3. Geçici tahsis sonrası sistem güvenli kalmalı

        Tüm koşullar sağlanırsa tahsis kalıcı olur; sağlanmazsa reddedilir.

        Args:
            pid:     Kaynak talep eden process kimliği
            request: Her kaynak tipinde talep edilen miktar listesi

        Returns:
            True  → tahsis onaylandı
            False → talep reddedildi
        """
        need = self._need(pid)

        # Koşul 1: request ≤ need
        for j in range(self.num_resources):
            if request[j] > need[j]:
                return False

        # Koşul 2: request ≤ available
        for j in range(self.num_resources):
            if request[j] > self.available[j]:
                return False

        # Geçici tahsis
        saved_allocation = list(self.allocation[pid])
        saved_available = list(self.available)

        for j in range(self.num_resources):
            self.allocation[pid][j] += request[j]
            self.available[j] -= request[j]

        # Koşul 3: güvenli durum testi
        if self.is_safe_state():
            return True

        # Güvensiz → geri al
        self.allocation[pid] = saved_allocation
        self.available = saved_available
        return False

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_need(self, pid: int) -> list[int]:
        """pid'in ihtiyaç vektörünü döner (Need = Max − Allocation)."""
        return self._need(pid)

    def get_available(self) -> list[int]:
        """Mevcut kullanılabilir kaynak vektörünü döner."""
        return list(self.available)

    def get_allocation(self, pid: int) -> list[int]:
        """pid'e atanmış kaynak vektörünü döner."""
        return list(self.allocation[pid])
