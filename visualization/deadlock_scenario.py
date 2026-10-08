"""
Deadlock görselleştirme senaryoları — adım adım RAG ve Banker's Algorithm.

Bu modül pygame'e bağlı değildir; tüm durum mantığı burada, çizim ise
deadlock_view.py içindedir. Böylece senaryolar headless test edilebilir.

Stepper'lar her adımda durumu baştan "replay" ederek kurar; bu sayede
geri adım (back) almak, olayları tersine çevirmeye gerek kalmadan
deterministik şekilde çalışır.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from core.deadlock import BankersAlgorithm, ResourceAllocationGraph

RAGAction = Literal["request", "assign", "release", "cancel"]
BankerVerdict = Literal["granted", "exceeds_need", "insufficient", "unsafe"]


# ---------------------------------------------------------------------------
# RAG senaryosu
# ---------------------------------------------------------------------------

@dataclass
class ProcessSpec:
    pid: int
    name: str


@dataclass
class ResourceSpec:
    rid: int
    name: str
    instances: int = 1


@dataclass
class RAGEvent:
    """
    Tek bir RAG olayı.

    action:
      - request: P → R istek kenarı eklenir
      - assign:  R → P atama kenarı eklenir, varsa istek kenarı kaldırılır
      - release: process kaynağı serbest bırakır
      - cancel:  istek kenarı geri çekilir (ör. process abort edildi)
    """
    action: RAGAction
    pid: int
    rid: int
    note: str = ""


@dataclass
class RAGScenario:
    name: str
    processes: list[ProcessSpec]
    resources: list[ResourceSpec]
    events: list[RAGEvent] = field(default_factory=list)
    description: str = ""


def _apply_rag_event(rag: ResourceAllocationGraph, ev: RAGEvent) -> None:
    if ev.pid not in rag.get_processes():
        raise ValueError(f"Bilinmeyen process: P{ev.pid}")
    if ev.rid not in rag.get_resources():
        raise ValueError(f"Bilinmeyen kaynak: R{ev.rid}")

    if ev.action == "request":
        rag.request_edge(ev.pid, ev.rid)
    elif ev.action == "assign":
        if rag.get_resource(ev.rid).available_instances <= 0:
            raise ValueError(f"R{ev.rid} için boş instance yok, P{ev.pid}'e atanamaz")
        if ev.rid in rag.get_held_resources(ev.pid):
            raise ValueError(f"P{ev.pid} zaten R{ev.rid}'yi tutuyor")
        rag.cancel_request(ev.pid, ev.rid)
        rag.assignment_edge(ev.pid, ev.rid)
    elif ev.action == "release":
        rag.release(ev.pid, ev.rid)
    elif ev.action == "cancel":
        rag.cancel_request(ev.pid, ev.rid)
    else:
        raise ValueError(f"Geçersiz aksiyon: {ev.action!r}")


class RAGStepper:
    """RAGScenario'yu olay olay oynatır; ileri/geri/sıfırla destekler."""

    def __init__(self, scenario: RAGScenario) -> None:
        self.scenario = scenario
        self.step = 0
        self.rag = self._build(0)
        # Senaryoyu baştan sona doğrula — hatalı olay erken yakalansın
        self._build(len(scenario.events))

    def _build(self, upto: int) -> ResourceAllocationGraph:
        rag = ResourceAllocationGraph()
        for p in self.scenario.processes:
            rag.add_process(p.pid)
        for r in self.scenario.resources:
            rag.add_resource(r.rid, r.name, r.instances)
        for ev in self.scenario.events[:upto]:
            _apply_rag_event(rag, ev)
        return rag

    @property
    def total_steps(self) -> int:
        return len(self.scenario.events)

    @property
    def at_end(self) -> bool:
        return self.step >= self.total_steps

    @property
    def last_event(self) -> RAGEvent | None:
        return self.scenario.events[self.step - 1] if self.step > 0 else None

    def forward(self) -> bool:
        if self.at_end:
            return False
        self.step += 1
        self.rag = self._build(self.step)
        return True

    def back(self) -> bool:
        if self.step == 0:
            return False
        self.step -= 1
        self.rag = self._build(self.step)
        return True

    def reset(self) -> None:
        self.step = 0
        self.rag = self._build(0)

    @property
    def deadlocked(self) -> list[int]:
        return self.rag.detect_deadlock()


# ---------------------------------------------------------------------------
# Banker's senaryosu
# ---------------------------------------------------------------------------

@dataclass
class BankerRequest:
    pid: int
    request: list[int]
    note: str = ""


@dataclass
class BankerScenario:
    name: str
    resource_names: list[str]
    total: list[int]
    allocation: dict[int, list[int]]
    max_demand: dict[int, list[int]]
    requests: list[BankerRequest] = field(default_factory=list)
    description: str = ""


@dataclass
class BankerOutcome:
    request: BankerRequest
    verdict: BankerVerdict

    @property
    def granted(self) -> bool:
        return self.verdict == "granted"


def evaluate_request(banker: BankersAlgorithm, req: BankerRequest) -> BankerVerdict:
    """
    Talebi BankersAlgorithm'e uygular ve neden kabul/ret edildiğini döner.

    BankersAlgorithm.request_resources yalnızca bool döndürdüğünden ret
    sebebi aynı üç koşul burada sırayla kontrol edilerek belirlenir.
    """
    need = banker.get_need(req.pid)
    available = banker.get_available()
    if any(r > n for r, n in zip(req.request, need, strict=True)):
        return "exceeds_need"
    if any(r > a for r, a in zip(req.request, available, strict=True)):
        return "insufficient"
    return "granted" if banker.request_resources(req.pid, req.request) else "unsafe"


class BankerStepper:
    """BankerScenario taleplerini sırayla değerlendirir."""

    def __init__(self, scenario: BankerScenario) -> None:
        self.scenario = scenario
        self.step = 0
        self.banker, self.outcomes = self._build(0)

    def _build(self, upto: int) -> tuple[BankersAlgorithm, list[BankerOutcome]]:
        sc = self.scenario
        banker = BankersAlgorithm(
            processes=sorted(sc.allocation),
            resources=sc.total,
            allocation=sc.allocation,
            max_demand=sc.max_demand,
        )
        outcomes = [BankerOutcome(r, evaluate_request(banker, r)) for r in sc.requests[:upto]]
        return banker, outcomes

    @property
    def total_steps(self) -> int:
        return len(self.scenario.requests)

    @property
    def at_end(self) -> bool:
        return self.step >= self.total_steps

    @property
    def last_outcome(self) -> BankerOutcome | None:
        return self.outcomes[-1] if self.outcomes else None

    def forward(self) -> bool:
        if self.at_end:
            return False
        self.step += 1
        self.banker, self.outcomes = self._build(self.step)
        return True

    def back(self) -> bool:
        if self.step == 0:
            return False
        self.step -= 1
        self.banker, self.outcomes = self._build(self.step)
        return True

    def reset(self) -> None:
        self.step = 0
        self.banker, self.outcomes = self._build(0)


# ---------------------------------------------------------------------------
# Yerleşim (layout)
# ---------------------------------------------------------------------------

NodeKey = tuple[str, int]  # ("P", pid) veya ("R", rid)


def _interleaved(pids: list[int], rids: list[int]) -> list[NodeKey]:
    order: list[NodeKey] = []
    for i in range(max(len(pids), len(rids))):
        if i < len(pids):
            order.append(("P", pids[i]))
        if i < len(rids):
            order.append(("R", rids[i]))
    return order


def scenario_node_order(scenario: RAGScenario) -> list[NodeKey]:
    """
    Senaryodaki tüm kenarları (her adımın birleşimi) takip ederek çember
    üzerindeki düğüm sırasını belirler.

    Her zincir, henüz yerleştirilmemiş ilk düğümden başlayıp ilk
    yerleştirilmemiş komşuya açgözlü (greedy) şekilde ilerler. Böylece
    P1 → R2 → P2 → ... gibi bir bekleme döngüsü çember üzerinde komşu
    düğümlere düşer ve kenarlar çemberin içinden çapraz geçmez.
    """
    succ: dict[NodeKey, list[NodeKey]] = {}
    for ev in scenario.events:
        p, r = ("P", ev.pid), ("R", ev.rid)
        if ev.action == "request":
            src, dst = p, r
        elif ev.action == "assign":
            src, dst = r, p
        else:
            continue
        if dst not in succ.setdefault(src, []):
            succ[src].append(dst)

    base = _interleaved([p.pid for p in scenario.processes], [r.rid for r in scenario.resources])
    order: list[NodeKey] = []
    placed: set[NodeKey] = set()
    for start in base:
        node: NodeKey | None = start
        while node is not None and node not in placed:
            order.append(node)
            placed.add(node)
            node = next((n for n in succ.get(node, []) if n not in placed), None)
    return order


def circular_layout(
    pids: list[int],
    rids: list[int],
    cx: float,
    cy: float,
    radius: float,
    order: list[NodeKey] | None = None,
) -> dict[NodeKey, tuple[int, int]]:
    """
    Process ve kaynakları tek bir çember üzerine dizer.

    `order` verilmezse P, R, P, R... şeklinde sırayla dizilir; sayılar eşit
    değilse fazlalar sona eklenir. Senaryo için scenario_node_order()
    kullanmak döngüleri çember üzerinde komşu düğümler olarak gösterir.
    """
    if order is None:
        order = _interleaved(pids, rids)

    n = len(order)
    pos: dict[NodeKey, tuple[int, int]] = {}
    for i, key in enumerate(order):
        angle = -math.pi / 2 + 2 * math.pi * i / max(n, 1)
        pos[key] = (round(cx + radius * math.cos(angle)), round(cy + radius * math.sin(angle)))
    return pos


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def save_rag_scenario(scenario: RAGScenario, path: str | Path) -> None:
    data = {"type": "rag", **asdict(scenario)}
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def rag_scenario_from_dict(data: dict) -> RAGScenario:
    return RAGScenario(
        name=data["name"],
        description=data.get("description", ""),
        processes=[ProcessSpec(**p) for p in data["processes"]],
        resources=[ResourceSpec(**r) for r in data["resources"]],
        events=[RAGEvent(**e) for e in data.get("events", [])],
    )


def save_banker_scenario(scenario: BankerScenario, path: str | Path) -> None:
    data = {"type": "banker", **asdict(scenario)}
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def banker_scenario_from_dict(data: dict) -> BankerScenario:
    return BankerScenario(
        name=data["name"],
        description=data.get("description", ""),
        resource_names=list(data["resource_names"]),
        total=list(data["total"]),
        # JSON anahtarları string olur → int'e çevir
        allocation={int(k): list(v) for k, v in data["allocation"].items()},
        max_demand={int(k): list(v) for k, v in data["max_demand"].items()},
        requests=[BankerRequest(**r) for r in data.get("requests", [])],
    )


def load_deadlock_scenario(path: str | Path) -> RAGScenario | BankerScenario:
    """JSON dosyasındaki "type" alanına göre RAG veya Banker senaryosu yükler."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    kind = data.pop("type", "rag")
    if kind == "rag":
        return rag_scenario_from_dict(data)
    if kind == "banker":
        return banker_scenario_from_dict(data)
    raise ValueError(f"Bilinmeyen senaryo tipi: {kind!r}")


# ---------------------------------------------------------------------------
# Yerleşik senaryolar
# ---------------------------------------------------------------------------

def _dining_philosophers(n: int = 4) -> RAGScenario:
    procs = [ProcessSpec(i, f"Filozof{i}") for i in range(1, n + 1)]
    forks = [ResourceSpec(i, f"Çatal{i}") for i in range(1, n + 1)]
    events: list[RAGEvent] = []
    for i in range(1, n + 1):
        events.append(RAGEvent("assign", i, i, f"Filozof{i} sol çatalı (Çatal{i}) aldı"))
    for i in range(1, n + 1):
        right = i % n + 1
        events.append(RAGEvent("request", i, right, f"Filozof{i} sağ çatalı (Çatal{right}) istiyor"))
    # Kurtarma: Filozof1 abort edilir, çatalını bırakır
    events += [
        RAGEvent("cancel", 1, 2, "Kurtarma: Filozof1 kurban seçildi, isteğini geri çekti"),
        RAGEvent("release", 1, 1, "Filozof1 Çatal1'i bıraktı, döngü kırıldı"),
        RAGEvent("assign", n, 1, f"Filozof{n} Çatal1'i aldı ve yemeye başlayabilir"),
    ]
    return RAGScenario(
        name=f"Dining Philosophers ({n})",
        description="Herkes sol çatalı alıp sağı bekler: dairesel bekleme, deadlock; ardından kurtarma.",
        processes=procs,
        resources=forks,
        events=events,
    )


def _chain_no_deadlock() -> RAGScenario:
    return RAGScenario(
        name="Bekleme zinciri (deadlock yok)",
        description="P1 -> P2 -> P3 bekleme zinciri var ama döngü yok; P3 bitince zincir çözülür.",
        processes=[ProcessSpec(1, "P1"), ProcessSpec(2, "P2"), ProcessSpec(3, "P3")],
        resources=[ResourceSpec(1, "Disk"), ResourceSpec(2, "Printer"), ResourceSpec(3, "Tape")],
        events=[
            RAGEvent("assign", 1, 1, "P1 Disk'i aldı"),
            RAGEvent("assign", 2, 2, "P2 Printer'ı aldı"),
            RAGEvent("assign", 3, 3, "P3 Tape'i aldı"),
            RAGEvent("request", 1, 2, "P1 Printer'ı bekliyor"),
            RAGEvent("request", 2, 3, "P2 Tape'i bekliyor — zincir var, döngü yok"),
            RAGEvent("release", 3, 3, "P3 işini bitirip Tape'i bıraktı"),
            RAGEvent("assign", 2, 3, "P2 Tape'i aldı"),
            RAGEvent("release", 2, 2, "P2 bitti, Printer serbest"),
            RAGEvent("release", 2, 3, "P2 Tape'i bıraktı"),
            RAGEvent("assign", 1, 2, "P1 Printer'ı aldı — herkes ilerleyebildi"),
        ],
    )


def _two_process_cycle() -> RAGScenario:
    return RAGScenario(
        name="İki process, iki kilit",
        description="Klasik A-B / B-A kilit sırası hatası.",
        processes=[ProcessSpec(1, "Thread-A"), ProcessSpec(2, "Thread-B")],
        resources=[ResourceSpec(1, "MutexX"), ResourceSpec(2, "MutexY")],
        events=[
            RAGEvent("assign", 1, 1, "Thread-A MutexX'i kilitledi"),
            RAGEvent("assign", 2, 2, "Thread-B MutexY'yi kilitledi"),
            RAGEvent("request", 1, 2, "Thread-A MutexY'yi bekliyor"),
            RAGEvent("request", 2, 1, "Thread-B MutexX'i bekliyor: DEADLOCK"),
        ],
    )


def _silberschatz_banker() -> BankerScenario:
    return BankerScenario(
        name="Banker's — Silberschatz örneği",
        description="Ders kitabındaki 5 process / 3 kaynak tipi (A=10, B=5, C=7) örneği.",
        resource_names=["A", "B", "C"],
        total=[10, 5, 7],
        allocation={0: [0, 1, 0], 1: [2, 0, 0], 2: [3, 0, 2], 3: [2, 1, 1], 4: [0, 0, 2]},
        max_demand={0: [7, 5, 3], 1: [3, 2, 2], 2: [9, 0, 2], 3: [2, 2, 2], 4: [4, 3, 3]},
        requests=[
            BankerRequest(1, [1, 0, 2], "P1 (1,0,2) ister — güvenli kalır"),
            BankerRequest(4, [3, 3, 0], "P4 (3,3,0) ister — yeterli kaynak yok"),
            BankerRequest(0, [0, 2, 0], "P0 (0,2,0) ister — güvensiz duruma götürür"),
            BankerRequest(2, [0, 0, 1], "P2 (0,0,1) ister — beyan ettiği Max'ı aşıyor"),
            BankerRequest(1, [0, 2, 0], "P1 (0,2,0) ister — güvenli kalır"),
        ],
    )


BUILTIN_RAG_SCENARIOS: list[RAGScenario] = [
    _dining_philosophers(4),
    _two_process_cycle(),
    _chain_no_deadlock(),
]

BUILTIN_BANKER_SCENARIOS: list[BankerScenario] = [
    _silberschatz_banker(),
]
