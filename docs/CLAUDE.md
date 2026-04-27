# [cite_start]Mini OS Simulator - CLAUDE.md [cite: 1]

[cite_start]**Proje Rehberi:** Yazılım mühendisliği öğrencisi için Python tabanlı, görselleştirilmiş işletim sistemi simülatörü. [cite: 2]

## [cite_start]Proje Özeti [cite: 3]
[cite_start]İşletim sisteminin çekirdek bileşenlerini (process scheduling, memory management, file system, IPC) simüle eden ve her algoritmayı gerçek zamanlı görselleştiren bir masaüstü uygulamasıdır. [cite: 4]
[cite_start]**Hedef:** GitHub'da "bu kişi OS kavramlarını gerçekten anlıyor" dedirtmek. [cite: 5]

---

## [cite_start]Tech Stack [cite: 6]

### [cite_start]Core / Backend [cite: 7]
| Katman | Teknoloji | Açıklama |
| :--- | :--- | :--- |
| Dil | [cite_start]Python 3.11+ [cite: 8] | [cite_start]Ana geliştirme dili [cite: 8] |
| Simülasyon motoru | [cite_start]Saf Python (OOP) [cite: 8] | [cite_start]Process, Memory, Scheduler sınıfları [cite: 8] |
| [cite_start]Eşzamanlılık | threading, asyncio [cite: 8] | [cite_start]Gerçek zamanlı simülasyon döngüsü [cite: 8] |
| [cite_start]Veri yapıları | collections, heapq [cite: 8] | [cite_start]Ready queue, page table, vs. [cite: 8] |
| [cite_start]Test | pytest [cite: 8] | [cite_start]Unit + integration testler [cite: 8] |
| [cite_start]Linting | ruff, mypy [cite: 8] | [cite_start]Kod kalitesi ve tip güvenliği [cite: 8] |

### [cite_start]Görselleştirme (2 seçenek - birini seç) [cite: 9]

#### [cite_start]Seçenek A: Masaüstü GUI (Önerilen başlangıç) [cite: 10]
| [cite_start]Teknoloji [cite: 11] | [cite_start]Açıklama [cite: 12] |
| :--- | :--- |
| [cite_start]**pygame** [cite: 13] | [cite_start]Gantt chart, bellek ızgarası, animasyonlar [cite: 13] |
| [cite_start]**tkinter** [cite: 13] | [cite_start]Kontrol paneli, parametre girişleri [cite: 13] |
| [cite_start]**matplotlib** [cite: 13] | [cite_start]Grafik çıktıları (CPU utilization, page faults, vs.) [cite: 13] |

#### [cite_start]Seçenek B: Web Dashboard (Daha etkileyici GitHub demo) [cite: 14]
| [cite_start]Teknoloji [cite: 15] | [cite_start]Açıklama [cite: 15] |
| :--- | :--- |
| [cite_start]**FastAPI** [cite: 15] | [cite_start]REST + WebSocket API (simülasyon backend) [cite: 15] |
| [cite_start]**React / Vite** [cite: 15] | [cite_start]Frontend dashboard [cite: 15] |
| [cite_start]**D3.js** [cite: 15] | [cite_start]Gantt chart, memory map görselleştirme [cite: 15] |
| [cite_start]**Chart.js** [cite: 15] | [cite_start]CPU/IO burst grafikleri [cite: 15] |

### [cite_start]DevOps / Proje Altyapısı [cite: 16]
| [cite_start]Araç [cite: 17] | [cite_start]Açıklama [cite: 17] |
| :--- | :--- |
| [cite_start]**Docker** [cite: 17] [cite_start]| docker-compose up ile çalışsın [cite: 17] |
| [cite_start]**GitHub Actions** [cite: 17] | [cite_start]CI/CD: test + lint otomatik çalışsın [cite: 17] |
| [cite_start]**pre-commit** [cite: 17] | [cite_start]Commit öncesi otomatik format/lint [cite: 17] |
| [cite_start]**Poetry** [cite: 17] | [cite_start]Dependency management [cite: 17] |

---

## [cite_start]Öğrenmen Gereken Kütüphaneler [cite: 18]

### [cite_start]Öncelik 1 - Simülasyon Temeli [cite: 19]
* [cite_start]**threading**: Eşzamanlı process simülasyonu [cite: 20]
* [cite_start]**asyncio**: Async I/O burst simülasyonu [cite: 20]
* [cite_start]**heapq**: Priority queue (Priority Scheduling için) [cite: 20]
* [cite_start]**collections**: deque (Round Robin queue), OrderedDict [cite: 20]
* [cite_start]**dataclasses**: Process, MemoryBlock, PageTable modelleri [cite: 20]
* [cite_start]**enum**: ProcessState (READY, RUNNING, WAITING, TERMINATED) [cite: 20]
* [cite_start]**time**: Simülasyon clock [cite: 20]

### [cite_start]Öncelik 2 - Görselleştirme [cite: 21]
* [cite_start]**pygame**: Gantt chart animasyonu, real-time görsel [cite: 22]
* [cite_start]**matplotlib**: Grafik çıktıları, istatistik gösterimi [cite: 22]
* [cite_start]**tkinter**: Form/kontrol paneli (basit GUI) [cite: 22]

### [cite_start]Öncelik 3 - Web Arayüzü (Seçenek B) [cite: 23]
* [cite_start]**fastapi**: REST API + WebSocket [cite: 24, 25]
* [cite_start]**uvicorn**: ASGI server [cite: 26, 27]
* [cite_start]**pydantic**: Veri validasyonu [cite: 28, 29]
* [cite_start]**websockets**: Real-time frontend güncellemeleri [cite: 30, 31]

### [cite_start]Öncelik 4 - Kalite & Test [cite: 32]
* [cite_start]**pytest**: Test framework [cite: 33, 34]
* [cite_start]**pytest-cov**: Coverage raporu [cite: 35, 36]
* [cite_start]**mypy**: Statik tip kontrolü [cite: 37, 38]
* [cite_start]**ruff**: Linter + formatter [cite: 39, 40]

---

## [cite_start]Proje Klasör Yapısı [cite: 41, 42]

```text
mini-os-simulator/
[cite_start]├── core/ [cite: 43]                    # [cite_start]Simülasyon motoru [cite: 43]
[cite_start]│   ├── _init_.py [cite: 43]
[cite_start]│   ├── process.py [cite: 43]           # [cite_start]Process modeli (PCB) [cite: 43]
[cite_start]│   ├── scheduler.py [cite: 43]         # [cite_start]Scheduling algoritmaları [cite: 43]
[cite_start]│   ├── memory_manager.py [cite: 43]    # [cite_start]Bellek yönetimi [cite: 43]
[cite_start]│   ├── file_system.py [cite: 43]       # [cite_start]Basit dosya sistemi [cite: 43]
[cite_start]│   ├── ipc.py [cite: 43]               # [cite_start]IPC (pipe, semaphore) [cite: 43]
[cite_start]│   └── clock.py [cite: 43]             # [cite_start]Simülasyon saati [cite: 43]
[cite_start]├── algorithms/ [cite: 43]
[cite_start]│   ├── scheduling/ [cite: 43]
[cite_start]│   │   ├── fcfs.py [cite: 43]          # [cite_start]First Come First Served [cite: 43]
[cite_start]│   │   ├── sjf.py [cite: 43]           # [cite_start]Shortest Job First [cite: 43]
[cite_start]│   │   ├── round_robin.py [cite: 43]   # [cite_start]Round Robin [cite: 43]
[cite_start]│   │   ├── priority.py [cite: 43]      # [cite_start]Priority Scheduling [cite: 43]
[cite_start]│   │   └── multilevel_queue.py [cite: 43] # [cite_start]Multilevel Queue [cite: 43]
[cite_start]│   ├── memory/ [cite: 46]
[cite_start]│   │   ├── paging.py [cite: 47]        # [cite_start]Paging + TLB simülasyonu [cite: 44]
[cite_start]│   │   ├── segmentation.py [cite: 52]  # [cite_start]Segmentation [cite: 44]
[cite_start]│   │   └── virtual_memory.py [cite: 53] # [cite_start]Virtual memory + page fault [cite: 50]
[cite_start]│   └── allocation/ [cite: 54]
[cite_start]│       ├── first_fit.py [cite: 55]
[cite_start]│       ├── best_fit.py [cite: 55]
[cite_start]│       └── worst_fit.py [cite: 57]
[cite_start]├── visualization/ [cite: 59]           # [cite_start]Görselleştirme katmanı [cite: 58]
[cite_start]│   ├── gantt_chart.py [cite: 60]
[cite_start]│   ├── memory_map.py [cite: 62]
[cite_start]│   └── stats_dashboard.py [cite: 62]
[cite_start]├── api/ [cite: 63]                     # (Seçenek B) [cite_start]Web API [cite: 64]
[cite_start]│   ├── main.py [cite: 65]
[cite_start]│   └── routes/ [cite: 67]
[cite_start]│       └── websocket_handler.py [cite: 68]
[cite_start]├── frontend/ [cite: 70]                # (Seçenek B) [cite_start]React app [cite: 71]
[cite_start]│   ├── src/ [cite: 72]
[cite_start]│   └── package.json [cite: 74]
[cite_start]├── tests/ [cite: 75]
[cite_start]│   ├── test_scheduler.py [cite: 78]
[cite_start]│   ├── test_memory.py [cite: 79]
[cite_start]│   └── test_process.py [cite: 80]
[cite_start]├── examples/ [cite: 82]                # [cite_start]Örnek senaryolar [cite: 83]
[cite_start]│   ├── deadlock_demo.py [cite: 84]
[cite_start]│   ├── page_fault_demo.py [cite: 88]
[cite_start]│   └── scheduling_comparison.py [cite: 89]
[cite_start]├── docs/ [cite: 90]                    # [cite_start]Mimari diyagramlar, notlar [cite: 91]
[cite_start]│   └── architecture.md [cite: 92]
[cite_start]├── Dockerfile [cite: 94]
[cite_start]├── docker-compose.yml [cite: 96]
[cite_start]├── pyproject.toml [cite: 97]           # [cite_start]Poetry config [cite: 98]
[cite_start]├── .github/ [cite: 99]
[cite_start]│   └── workflows/ [cite: 100]
[cite_start]│       └── ci.yml [cite: 102]
[cite_start]├── README.md [cite: 103]
[cite_start]└── CLAUDE.md [cite: 105]               # (Bu dosya) [cite_start][cite: 106]
```

---

## [cite_start]Roadmap [cite: 107]

### [cite_start]Faz 1: Temel Simülasyon (2-3 Hafta) [cite: 108]
[cite_start]**Hafta 1: Process & Scheduler** [cite: 109]
* [cite_start]Process sınıfı yaz (PCB: PID, state, priority, burst time, arrival time) [cite: 110]
* [cite_start]ProcessState enum'u tanımla (NEW → READY → RUNNING → WAITING → TERMINATED) [cite: 111]
* [cite_start]Scheduler base class + FCFS implementasyonu [cite: 112]
* [cite_start]Simülasyon clock mekanizması (tick() tabanlı) [cite: 113]
* [cite_start]İlk unit testleri yaz [cite: 114]

[cite_start]**Hafta 2: Scheduling Algoritmaları** [cite: 115]
* [cite_start]SJF (preemptive + non-preemptive) [cite: 116]
* [cite_start]Round Robin (quantum süresi parametrik) [cite: 117]
* [cite_start]Priority Scheduling [cite: 118]
* [cite_start]Algoritmalar arası istatistik karşılaştırması (avg waiting time, avg turnaround time, CPU utilization) [cite: 119]

[cite_start]**Hafta 3: Memory Management** [cite: 120]
* [cite_start]MemoryBlock ve MemoryManager sınıfları [cite: 121]
* [cite_start]Contiguous allocation: First Fit, Best Fit, Worst Fit [cite: 122]
* [cite_start]Fragmentation hesaplaması [cite: 123]

### [cite_start]Faz 2: Gelişmiş Bellek & Görselleştirme (3-4 Hafta) [cite: 124]
[cite_start]**Hafta 4: Paging & Virtual Memory** [cite: 125]
* [cite_start]Page table implementasyonu [cite: 126]
* [cite_start]TLB simülasyonu (hit/miss oranı) [cite: 127]
* [cite_start]Page fault mekanizması [cite: 128]
* [cite_start]LRU, FIFO, Optimal page replacement algoritmaları [cite: 129]

[cite_start]**Hafta 5: İlk Görselleştirme** [cite: 130]
* [cite_start]pygame ile Gantt chart (gerçek zamanlı) [cite: 131]
* [cite_start]Bellek ızgarası (yeşil=boş, renkli=dolu, kırmızı=fragmentation) [cite: 132]
* [cite_start]matplotlib ile istatistik grafikleri [cite: 133]

[cite_start]**Hafta 6-7: GUI Kontrol Paneli** [cite: 134]
* [cite_start]tkinter ile parametre girişi (process sayısı, quantum, vs.) [cite: 135]
* [cite_start]Simülasyonu durdur/başlat/hızlandır [cite: 136]
* [cite_start]Senaryo kaydet/yükle (JSON) [cite: 137]

### [cite_start]Faz 3: İleri Özellikler (3-4 Hafta) [cite: 138]
[cite_start]**Hafta 8: Deadlock** [cite: 139]
* [cite_start]Deadlock detection (Resource Allocation Graph) [cite: 140]
* [cite_start]Banker's Algorithm (deadlock avoidance) [cite: 141]
* [cite_start]Görsel deadlock gösterimi [cite: 142]

[cite_start]**Hafta 9: IPC & Senkronizasyon** [cite: 143]
* [cite_start]Pipe ve message queue simülasyonu [cite: 144]
* [cite_start]Semaphore ve mutex implementasyonu [cite: 145]
* [cite_start]Producer-Consumer, Readers-Writers, Dining Philosophers demoları [cite: 146]

[cite_start]**Hafta 10: Dosya Sistemi** [cite: 147]
* [cite_start]FAT tabanlı basit dosya sistemi [cite: 148]
* [cite_start]Disk scheduling: FCFS, SSTF, SCAN, C-SCAN [cite: 149]
* [cite_start]İnode yapısı simülasyonu [cite: 150]

### [cite_start]Faz 4: Web Dashboard & Polish (2-3 Hafta) [cite: 151]
[cite_start]**Hafta 11-12: Web Arayüzü (Seçenek B)** [cite: 152]
* [cite_start]FastAPI backend + WebSocket [cite: 153]
* [cite_start]React dashboard: Gantt chart (D3.js), memory map [cite: 154]
* [cite_start]Algoritma karşılaştırma modu (yan yana) [cite: 155]
* [cite_start]Export: PNG grafik, CSV istatistik [cite: 156]

[cite_start]**Hafta 13: Son Hazırlık** [cite: 157]
* [cite_start]Docker containerize [cite: 158]
* [cite_start]GitHub Actions CI/CD [cite: 159]
* [cite_start]README'yi zenginleştir (GIF demo, mimari diyagram) [cite: 160]
* [cite_start]examples/ klasörüne 3-4 hazır senaryo ekle [cite: 161]

---

## [cite_start]Öğrenilecek Core OS Kavramları [cite: 162]
* [cite_start]Process Control Block (PCB) [cite: 163]
* [cite_start]Context Switching [cite: 164]
* [cite_start]Scheduling Criteria (CPU burst, I/O burst, waiting time) [cite: 165]
* [cite_start]Preemptive vs Non-preemptive scheduling [cite: 166]
* [cite_start]Internal & External Fragmentation [cite: 167]
* [cite_start]Logical vs Physical Address Space [cite: 168]
* [cite_start]Page Table, TLB, Multi-level Paging [cite: 169]
* [cite_start]Thrashing & Working Set [cite: 170]
* [cite_start]Deadlock: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait [cite: 171]
* [cite_start]Banker's Algorithm [cite: 172]
* [cite_start]Semaphore & Mutex [cite: 173]
* [cite_start]Monitor [cite: 174]
* [cite_start]Disk Scheduling Algorithms [cite: 175]

---

## [cite_start]GitHub'da Fark Yaratacak Detaylar [cite: 176]
1.  [cite_start]**README'ye GIF ekle:** terminalizer veya asciinema ile simülasyon kaydı. [cite: 177]
2.  [cite_start]**Algoritma karşılaştırma tablosu:** Aynı process seti için FCFS vs RR vs SJF. [cite: 178]
3.  [cite_start]**Badge'ler:** pytest coverage, CI status, Python version. [cite: 179, 180]
4.  [cite_start]**Examples/ klasörü:** Deadlock, thrashing, starvation senaryoları. [cite: 181]
5.  [cite_start]**Wiki:** Her algoritmanın kısa teorik açıklaması + kodun hangi satırı neyi yapar. [cite: 182]
6.  [cite_start]**Releases:** v0.1, v0.2 etiketleriyle milestone'ları işaretle. [cite: 183]

---

## [cite_start]Faydalı Kaynaklar [cite: 184]
* [cite_start]**Operating System Concepts** - Silberschatz, Galvin, Gagne (Dinozor Kitap) [cite: 185]
* [cite_start]**Modern Operating Systems** - Andrew Tanenbaum [cite: 186, 187]
* [cite_start]**OSDev Wiki** - Gerçek OS kavramları [cite: 188]
* [cite_start]**Pygame Docs** [cite: 189]
* [cite_start]**FastAPI Docs** [cite: 190]
* [cite_start]**D3.js Gallery** - Gantt chart örnekleri [cite: 191]

> Bu dosya projenin yaşayan rehberidir. [cite_start]Her faz tamamlandıkça güncellenmelidir. [cite: 192]