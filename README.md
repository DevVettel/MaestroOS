# MaestroOS

**MaestroOS**, temel işletim sistemi kavramlarını — process scheduling, bellek yönetimi, sanal bellek/paging, deadlock detection & avoidance ve IPC senkronizasyonu — gerçek zamanlı olarak görselleştiren, saf Python ile yazılmış bir masaüstü işletim sistemi simülatörüdür.

Simülasyon motoru tamamen deterministik, tick tabanlı bir saat üzerine kuruludur; hiçbir algoritma gerçek zamana bağlı değildir. Bu sayede hem test edilebilir hem de saniyede binlerce tick hızında koşturulabilir, hem de `pygame` + `tkinter` arayüzü üzerinden adım adım izlenebilir.

---

## İçindekiler

- [Özellikler](#özellikler)
- [Ekran Görünümü](#ekran-görünümü)
- [Mimari](#mimari)
- [Proje Yapısı](#proje-yapısı)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Desteklenen Algoritmalar](#desteklenen-algoritmalar)
- [Hazır Senaryolar](#hazır-senaryolar)
- [Test](#test)
- [Tasarım Prensipleri](#tasarım-prensipleri)
- [Yol Haritası](#yol-haritası)
- [Katkıda Bulunma](#katkıda-bulunma)
- [Lisans](#lisans)

---

## Özellikler

### 🧮 Process Scheduling
- Process Control Block (PCB) modeli — durum makinesi ile valide edilen geçişler (`NEW → READY → RUNNING → WAITING → TERMINATED`)
- 6 zamanlama algoritması: **FCFS**, **SJF**, **SRTF**, **Round Robin**, **Priority (preemptive/non-preemptive)** — aging (starvation önleme) desteğiyle
- Strategy Pattern: Yeni bir algoritma eklemek yalnızca `SchedulingAlgorithm` arayüzünü implement etmeyi gerektirir
- Otomatik istatistik toplama: ortalama bekleme/turnaround/response süresi, CPU utilization, context switch sayısı

### 🧠 Bellek Yönetimi
- **Contiguous allocation**: First Fit, Best Fit, Worst Fit stratejileri
- Blok bölme (split) ve komşu boş blokları birleştirme (coalescing)
- Internal / external fragmentation metrikleri, fragmentation oranı hesaplama

### 📄 Sanal Bellek & Paging
- Page Table + TLB (FIFO eviction politikalı donanım önbelleği simülasyonu)
- Page fault mekanizması, sayfa yükleme ve eviction akışı
- 3 sayfa değiştirme (page replacement) algoritması: **FIFO**, **LRU**, **Optimal (Bélády)**
- TLB hit/miss oranı ve page fault istatistikleri

### 🔒 Deadlock Detection & Avoidance
- Resource Allocation Graph (RAG) — DFS tabanlı döngü (cycle) tespiti
- Banker's Algorithm — güvenli durum (safe state) analizi ve kaynak talebi değerlendirmesi

### 🔗 IPC & Senkronizasyon
- Pipe (POSIX benzeri EOF semantiği ile), öncelik destekli Message Queue
- Semaphore, Mutex (ownership semantiği ile), Monitor (Condition Variable)
- Klasik senkronizasyon problemleri: **Producer-Consumer**, **Readers-Writers**, **Dining Philosophers** (Chandy/Misra deadlock-free çözümü)

### 🎨 Gerçek Zamanlı Görselleştirme
- `pygame` tabanlı canlı **Gantt chart**, **bellek haritası** (renk kodlu fragmentation gösterimi) ve `matplotlib` destekli **istatistik paneli**
- `tkinter` tabanlı koyu temalı kontrol paneli: process tablosu, algoritma/parametre seçimi, hız kontrolü, başlat/duraklat/sıfırla
- Senaryo kaydet/yükle (JSON) ve rastgele senaryo üretici
- Thread-safe **SimulationBridge**: `tkinter` ana thread'de, `pygame` arka plan thread'inde çalışır (Windows COM/Tcl apartment threading kısıtına uyumlu tasarım)

---

## Ekran Görünümü

Uygulama açıldığında iki pencere ile karşılaşırsınız:

| Pencere | İçerik |
| :--- | :--- |
| **Kontrol Paneli** (`tkinter`) | Process tablosu, algoritma/quantum/bellek stratejisi seçimi, hazır senaryolar, Başlat/Duraklat/Sıfırla, hız ayarı |
| **Simülasyon Ekranı** (`pygame`) | Üstte gerçek zamanlı Gantt chart · sol altta bellek haritası · sağ altta CPU/bekleme istatistik grafikleri |

Simülasyon ekranı kısayolları: `SPACE` duraklat/devam · `+ / -` hız ayarı · `ESC` çıkış.

---

## Mimari

```
                     ┌─────────────────────┐
                     │     ControlPanel     │  (tkinter — ana thread)
                     │  parametreler, JSON   │
                     │  senaryo yönetimi     │
                     └──────────┬───────────┘
                                │ push_start / toggle_pause / set_speed
                                ▼
                     ┌─────────────────────┐
                     │  SimulationBridge     │  thread-safe kuyruk
                     └──────────┬───────────┘
                                │ pop_start / paused / speed
                                ▼
   ┌────────────────────────────────────────────────────┐
   │                    MainWindow (pygame — arka plan)   │
   │  ┌───────────┐   ┌────────────────┐   ┌───────────┐ │
   │  │ Scheduler │──▶│  MemoryManager  │   │  Gantt /   │ │
   │  │ (Strategy)│   │ (allocation +   │   │  MemMap /  │ │
   │  │           │   │  fragmentation) │   │  Stats     │ │
   │  └───────────┘   └────────────────┘   └───────────┘ │
   └────────────────────────────────────────────────────┘
```

Katmanlar net şekilde ayrılmıştır:

- **`core/`** — motor: `Process`, `Scheduler`, `MemoryManager`, `PageTable`/`TLB`, `VirtualMemoryManager`, `ResourceAllocationGraph`/`BankersAlgorithm`, IPC primitive'leri. Görselleştirmeden tamamen bağımsız, saf Python.
- **`algorithms/`** — `core` içindeki soyut arayüzlerin (`SchedulingAlgorithm`, `PageReplacementAlgorithm`) somut implementasyonları. Yeni bir algoritma eklemek `core`'a dokunmadan yapılabilir.
- **`visualization/`** — `pygame`/`tkinter`/`matplotlib` katmanı. Motoru sarmalar, render eder; simülasyon mantığına müdahale etmez.

---

## Proje Yapısı

```
MaestroOS/
├── core/
│   ├── process.py          # Process Control Block (PCB) + ProcessState
│   ├── scheduler.py        # Scheduler orkestratörü + SchedulerStats
│   ├── memory_manager.py   # Contiguous allocation (First/Best/Worst Fit)
│   ├── paging.py           # PageTable, PageTableEntry, TLB
│   ├── virtual_memory.py   # VirtualMemoryManager (page fault handling)
│   ├── deadlock.py         # ResourceAllocationGraph, BankersAlgorithm
│   ├── ipc.py               # Pipe, MessageQueue, Semaphore, Mutex, Monitor,
│   │                        # ProducerConsumer, ReadersWriters, DiningPhilosophers
│   └── clock.py            # Tick tabanlı SimulationClock
├── algorithms/
│   ├── scheduling/
│   │   ├── fcfs.py          # First Come First Served
│   │   ├── sjf.py           # SJF (non-preemptive) + SRTF (preemptive)
│   │   ├── round_robin.py   # Round Robin (parametrik quantum)
│   │   └── priority.py      # Priority (preemptive/non-preemptive) + aging
│   └── memory/
│       ├── page_replacement.py  # PageReplacementAlgorithm arayüzü
│       ├── fifo.py          # FIFO page replacement
│       ├── lru.py           # LRU page replacement
│       └── optimal.py       # Optimal / Bélády page replacement
├── visualization/
│   ├── main_window.py      # pygame ana pencere + SimulationBridge
│   ├── control_panel.py    # tkinter kontrol paneli
│   ├── gantt_chart.py      # Gerçek zamanlı Gantt chart render
│   ├── memory_map.py       # Bellek haritası render (fragmentation renkli)
│   ├── stats_dashboard.py  # matplotlib istatistik paneli
│   └── scenario.py         # JSON senaryo kaydet/yükle + hazır senaryolar
├── examples/                # Hazır JSON senaryolar (deadlock, RR, bellek stresi)
├── tests/                   # 280+ unit/integration testi (pytest)
├── docs/                    # Proje rehberi (CLAUDE.md) ve notlar
└── main.py                  # Giriş noktası
```

---

## Kurulum

**Gereksinimler:** Python 3.10+ (native generic type hints ve `X | Y` union sözdizimi kullanılıyor)

```bash
git clone https://github.com/DevVettel/MaestroOS.git
cd MaestroOS

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

> `tkinter` standart kütüphanenin parçasıdır; çoğu sistemde ekstra kurulum gerekmez. Eksikse (bazı minimal Linux dağıtımlarında) `sudo apt install python3-tk` ile kurabilirsiniz.

---

## Kullanım

### GUI ile çalıştırma

```bash
python3 main.py
```

Kontrol panelinden bir hazır senaryo seçin (veya kendi process setinizi oluşturun), algoritma/quantum/bellek stratejisini belirleyin ve **Başlat**'a basın. Simülasyon penceresi Gantt chart, bellek haritası ve istatistikleri gerçek zamanlı günceller.

### Programatik kullanım

Motor, GUI olmadan da doğrudan kullanılabilir — algoritma karşılaştırması, benchmark veya kendi scriptleriniz için idealdir:

```python
from core.process import Process
from core.scheduler import Scheduler
from algorithms.scheduling.round_robin import RoundRobin

processes = [
    Process(pid=1, name="Chrome",  burst_time=15, arrival_time=0, priority=2),
    Process(pid=2, name="VSCode",  burst_time=8,  arrival_time=2, priority=1),
    Process(pid=3, name="Firefox", burst_time=12, arrival_time=4, priority=3),
]

scheduler = Scheduler(algorithm=RoundRobin(quantum=3))
scheduler.load_processes(processes)
stats = scheduler.run_until_complete()

print(f"Ortalama bekleme süresi: {stats.avg_waiting_time:.2f}")
print(f"CPU kullanımı: {stats.cpu_utilization:.1f}%")
```

### Senaryo dosyaları

`examples/` klasöründeki JSON senaryolarını kontrol panelinden yükleyebilir ya da kendi senaryonuzu aynı şemaya göre kaydedebilirsiniz:

```json
{
  "name": "Round Robin Demo",
  "algorithm": "RoundRobin",
  "quantum": 3,
  "memory_size": 1024,
  "memory_strategy": "BEST_FIT",
  "processes": [
    {"pid": 1, "name": "Chrome", "burst_time": 20, "arrival_time": 0, "priority": 2}
  ]
}
```

---

## Desteklenen Algoritmalar

| Kategori | Algoritma | Tip | Notlar |
| :--- | :--- | :--- | :--- |
| Scheduling | FCFS | Non-preemptive | En basit, FIFO ready queue |
| Scheduling | SJF | Non-preemptive | Ortalama bekleme süresinde optimal (kanıtlanmış) |
| Scheduling | SRTF | Preemptive | SJF'in preemptive versiyonu |
| Scheduling | Round Robin | Preemptive | Parametrik quantum, starvation yok |
| Scheduling | Priority | Non-preemptive | Aging destekli (starvation önleme) |
| Scheduling | Preemptive Priority | Preemptive | Aging destekli |
| Bellek Tahsisi | First Fit / Best Fit / Worst Fit | — | Contiguous allocation stratejileri |
| Page Replacement | FIFO | — | İlk giren ilk çıkar |
| Page Replacement | LRU | — | En az yakın zamanda kullanılan |
| Page Replacement | Optimal (Bélády) | — | Teorik minimum page fault (benchmark amaçlı) |

Tüm scheduling algoritmaları `core.scheduler.SchedulingAlgorithm` soyut sınıfını, tüm page replacement algoritmaları `algorithms.memory.page_replacement.PageReplacementAlgorithm` soyut sınıfını implement eder — yeni bir algoritma eklemek mevcut kodu değiştirmeden mümkündür (Strategy Pattern).

---

## Hazır Senaryolar

`examples/` klasörü, farklı OS kavramlarını göstermek için tasarlanmış hazır senaryolar içerir:

| Dosya | Amaç |
| :--- | :--- |
| `round_robin_demo.json` | 6 process ile klasik Round Robin akışı |
| `deadlock_demo.json` | Yüksek öncelik çakışması senaryosu (Priority scheduling) |
| `memory_stress_demo.json` | 10 process, 256 byte'lık kısıtlı bellek — fragmentation'ı zorlar |

Kontrol paneli ayrıca dahili (`BUILTIN_SCENARIOS`) hazır senaryolar ve rastgele senaryo üretici (`random_scenario`) içerir.

---

## Test

Proje, 280'den fazla unit/integration testi ile geliştirme fazlarına göre organize edilmiştir:

```bash
pytest                     # tüm testler
pytest tests/test_phase1.py -v   # process & scheduling
pytest tests/test_phase2.py -v   # bellek yönetimi
pytest tests/test_phase3.py -v   # paging & sanal bellek
pytest tests/test_phase4.py -v   # deadlock & IPC
```

| Test dosyası | Kapsam |
| :--- | :--- |
| `test_phase1.py` | `Process`, `SimulationClock`, `FCFS` |
| `test_phase2.py` | `MemoryManager`, First/Best/Worst Fit, fragmentation |
| `test_phase3.py` | `PageTable`, `TLB`, FIFO/LRU/Optimal, `VirtualMemoryManager` |
| `test_phase4.py` | `SJF`, `SRTF`, `RoundRobin`, `Priority`, `PreemptivePriority` |
| `test_deadlock.py` | `ResourceAllocationGraph`, `BankersAlgorithm` |
| `test_ipc.py` | `Pipe`, `MessageQueue`, `Semaphore`, `Mutex`, `Monitor`, klasik IPC problemleri |

---

## Tasarım Prensipleri

- **Strategy Pattern** — scheduling ve page replacement algoritmaları birbirinin yerine geçebilir; `Scheduler` ve `VirtualMemoryManager` hangi algoritmayı kullandıklarını bilmez, yalnızca ortak arayüzle konuşurlar.
- **Deterministik simülasyon** — her şey `tick()` tabanlıdır, gerçek zamana (`time.sleep`) bağımlı değildir. Bu, testleri hızlı ve tekrarlanabilir kılar.
- **Katman ayrımı** — `core/` ve `algorithms/` görselleştirmeden habersizdir; `visualization/` yalnızca render eder. Motor, GUI olmadan da kullanılabilir/test edilebilir.
- **Validasyon içeren durum makinesi** — `Process.transition_to()` geçersiz state geçişlerini (`TERMINATED → RUNNING` gibi) çalışma zamanında engeller.
- **Thread-safety** — `SimulationBridge`, `tkinter` (ana thread) ile `pygame` (arka plan thread) arasında kilit korumalı, tek yönlü mesaj geçişi sağlar.

---

## Yol Haritası

- [x] **Faz 1** — Process modeli, `SimulationClock`, FCFS ve temel scheduler orkestrasyonu
- [x] **Faz 2** — Contiguous memory allocation (First/Best/Worst Fit), fragmentation metrikleri
- [x] **Faz 3** — Paging, TLB, page fault handling, FIFO/LRU/Optimal page replacement
- [x] **Faz 4** — SJF/SRTF, Round Robin, Priority (+ aging), deadlock detection (RAG), Banker's Algorithm, IPC & senkronizasyon primitive'leri
- [x] **Görselleştirme** — `pygame` Gantt chart & bellek haritası, `matplotlib` istatistik paneli, `tkinter` kontrol paneli, JSON senaryo kaydet/yükle
- [ ] Disk scheduling (FCFS, SSTF, SCAN, C-SCAN) ve basit dosya sistemi
- [ ] Segmentation (paging'e alternatif bellek modeli)
- [ ] Web dashboard (FastAPI + WebSocket + React/D3.js) — masaüstü GUI'ye alternatif
- [ ] CI/CD (GitHub Actions: test + lint) ve Docker containerization

Detaylı geliştirme günlüğü ve öğrenme notları için [`docs/CLAUDE.md`](docs/CLAUDE.md) dosyasına bakabilirsiniz.

---

## Katkıda Bulunma

Katkılar memnuniyetle karşılanır. Yeni bir scheduling ya da page replacement algoritması eklemek için:

1. İlgili soyut arayüzü (`SchedulingAlgorithm` veya `PageReplacementAlgorithm`) implement eden bir sınıf yazın
2. `tests/` altına algoritmanızı kapsayan testler ekleyin
3. Gerekiyorsa `visualization/scenario.py` içindeki algoritma haritasına (`_ALGO` / `_ALGORITHMS`) ekleyin

Pull request göndermeden önce `pytest` ile tüm testlerin geçtiğinden emin olun.

---

## Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.
