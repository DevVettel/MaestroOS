"""
tkinter Kontrol Paneli — simülasyon parametrelerini yapılandır, senaryo kaydet/yükle.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .scenario import (
    BUILTIN_SCENARIOS,
    ProcessConfig,
    ScenarioConfig,
    load_scenario,
    random_scenario,
    save_scenario,
)

_ALGORITHMS = ["FCFS", "SJF", "SRTF", "RoundRobin", "Priority"]
_STRATEGIES  = ["FIRST_FIT", "BEST_FIT", "WORST_FIT"]

_BG      = "#1e1e2e"
_SURFACE = "#2a2a3e"
_ACCENT  = "#7aa2f7"
_FG      = "#cdd6f4"
_RED     = "#f38ba8"
_GREEN   = "#a6e3a1"
_ENTRY   = "#313244"
_BORDER  = "#45475a"


# ---------------------------------------------------------------------------
# Style helper
# ---------------------------------------------------------------------------

def _apply_dark_style(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",           background=_BG,      foreground=_FG,
                    font=("Consolas", 10))
    style.configure("TFrame",      background=_BG)
    style.configure("TLabel",      background=_BG,      foreground=_FG)
    style.configure("TLabelframe", background=_BG,      foreground=_ACCENT,
                    bordercolor=_BORDER)
    style.configure("TLabelframe.Label", background=_BG, foreground=_ACCENT,
                    font=("Consolas", 10, "bold"))
    style.configure("TButton",     background=_SURFACE, foreground=_FG,
                    bordercolor=_BORDER, focuscolor=_ACCENT)
    style.map("TButton",
              background=[("active", _ACCENT)],
              foreground=[("active", _BG)])
    style.configure("Accent.TButton", background=_ACCENT, foreground=_BG,
                    font=("Consolas", 11, "bold"))
    style.map("Accent.TButton",
              background=[("active", "#89b4fa")],
              foreground=[("active", _BG)])
    style.configure("TCombobox",   fieldbackground=_ENTRY, background=_SURFACE,
                    foreground=_FG, arrowcolor=_ACCENT, bordercolor=_BORDER)
    style.configure("TEntry",      fieldbackground=_ENTRY, foreground=_FG,
                    insertcolor=_FG, bordercolor=_BORDER)
    style.configure("TSpinbox",    fieldbackground=_ENTRY, foreground=_FG,
                    arrowcolor=_ACCENT, bordercolor=_BORDER)
    style.configure("TNotebook",   background=_BG,      bordercolor=_BORDER)
    style.configure("TNotebook.Tab", background=_SURFACE, foreground=_FG,
                    padding=[10, 4])
    style.map("TNotebook.Tab",
              background=[("selected", _BG)],
              foreground=[("selected", _ACCENT)])
    style.configure("Treeview",    background=_SURFACE, fieldbackground=_SURFACE,
                    foreground=_FG, bordercolor=_BORDER, rowheight=22)
    style.configure("Treeview.Heading", background=_ENTRY, foreground=_ACCENT,
                    font=("Consolas", 10, "bold"))
    style.map("Treeview", background=[("selected", _ACCENT)],
              foreground=[("selected", _BG)])
    return style


# ---------------------------------------------------------------------------
# Process table (processes tab)
# ---------------------------------------------------------------------------

class _ProcessTable(ttk.Frame):
    _COLS = ("pid", "name", "burst", "arrival", "priority")
    _HEADS = ("PID", "Ad", "Burst", "Arrival", "Priority")
    _WIDTHS = (40, 90, 60, 60, 65)

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        self._tree = ttk.Treeview(tree_frame, columns=self._COLS, show="headings",
                                   height=8, yscrollcommand=scroll.set)
        scroll.configure(command=self._tree.yview)
        scroll.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)

        for col, head, w in zip(self._COLS, self._HEADS, self._WIDTHS):
            self._tree.heading(col, text=head)
            self._tree.column(col, width=w, anchor="center")

        # edit frame
        ef = ttk.LabelFrame(self, text=" Process Ekle / Düzenle ")
        ef.pack(fill="x", pady=(6, 0))

        labels = ["Ad:", "Burst:", "Arrival:", "Priority:"]
        self._vars: dict[str, tk.StringVar] = {
            "name":    tk.StringVar(value="P"),
            "burst":   tk.StringVar(value="5"),
            "arrival": tk.StringVar(value="0"),
            "priority":tk.StringVar(value="1"),
        }
        for i, (lbl, key) in enumerate(zip(labels, self._vars)):
            ttk.Label(ef, text=lbl).grid(row=0, column=i*2, padx=(8,2), pady=4, sticky="e")
            ttk.Entry(ef, textvariable=self._vars[key], width=8).grid(
                row=0, column=i*2+1, padx=(0,6), pady=4)

        btn_frame = ttk.Frame(ef)
        btn_frame.grid(row=1, column=0, columnspan=8, pady=(0, 4))
        ttk.Button(btn_frame, text="+ Ekle",    command=self._add).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="✎ Güncelle", command=self._update).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="✕ Sil",     command=self._delete).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="↑ Seç",     command=self._load_selected).pack(side="left", padx=4)

        self._tree.bind("<<TreeviewSelect>>", lambda _: self._load_selected())
        self._next_pid = 1

    # ------------------------------------------------------------------

    def _add(self) -> None:
        try:
            name     = self._vars["name"].get().strip() or f"P{self._next_pid}"
            burst    = int(self._vars["burst"].get())
            arrival  = int(self._vars["arrival"].get())
            priority = int(self._vars["priority"].get())
        except ValueError:
            messagebox.showerror("Hata", "Burst / Arrival / Priority tam sayı olmalı.")
            return
        if burst <= 0:
            messagebox.showerror("Hata", "Burst süresi 0'dan büyük olmalı.")
            return

        self._tree.insert("", "end",
                          values=(self._next_pid, name, burst, arrival, priority))
        self._next_pid += 1

    def _update(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        try:
            name     = self._vars["name"].get().strip()
            burst    = int(self._vars["burst"].get())
            arrival  = int(self._vars["arrival"].get())
            priority = int(self._vars["priority"].get())
        except ValueError:
            messagebox.showerror("Hata", "Burst / Arrival / Priority tam sayı olmalı.")
            return
        item = sel[0]
        pid  = self._tree.item(item, "values")[0]
        self._tree.item(item, values=(pid, name, burst, arrival, priority))

    def _delete(self) -> None:
        for item in self._tree.selection():
            self._tree.delete(item)

    def _load_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        _, name, burst, arrival, priority = self._tree.item(sel[0], "values")
        self._vars["name"].set(name)
        self._vars["burst"].set(burst)
        self._vars["arrival"].set(arrival)
        self._vars["priority"].set(priority)

    # ------------------------------------------------------------------

    def get_processes(self) -> list[ProcessConfig]:
        result = []
        for item in self._tree.get_children():
            pid, name, burst, arrival, priority = self._tree.item(item, "values")
            result.append(ProcessConfig(
                pid=int(pid), name=str(name),
                burst_time=int(burst), arrival_time=int(arrival), priority=int(priority),
            ))
        return result

    def load_processes(self, processes: list[ProcessConfig]) -> None:
        self._tree.delete(*self._tree.get_children())
        max_pid = 0
        for p in processes:
            self._tree.insert("", "end",
                              values=(p.pid, p.name, p.burst_time, p.arrival_time, p.priority))
            max_pid = max(max_pid, p.pid)
        self._next_pid = max_pid + 1


# ---------------------------------------------------------------------------
# Main control panel window
# ---------------------------------------------------------------------------

class ControlPanel:
    """
    tkinter yapılandırma penceresi.

    Kullanım:
        panel = ControlPanel()
        config = panel.run()          # None → kullanıcı kapattı
        if config:
            launch_simulation(config)
    """

    def __init__(self, initial: Optional[ScenarioConfig] = None) -> None:
        self._result: Optional[ScenarioConfig] = None
        self._root = tk.Tk()
        self._root.title("MaestroOS — Kontrol Paneli")
        self._root.configure(bg=_BG)
        self._root.resizable(False, False)
        _apply_dark_style(self._root)
        self._build(initial or ScenarioConfig())

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self, cfg: ScenarioConfig) -> None:
        root = self._root

        # Title
        title = tk.Label(root, text="⚙  MaestroOS Simülatör",
                         bg=_BG, fg=_ACCENT, font=("Consolas", 14, "bold"))
        title.pack(pady=(12, 4))

        # Scenario name row
        name_frame = ttk.Frame(root)
        name_frame.pack(fill="x", padx=16, pady=(0, 4))
        ttk.Label(name_frame, text="Senaryo adı:").pack(side="left")
        self._scenario_name = tk.StringVar(value=cfg.name)
        ttk.Entry(name_frame, textvariable=self._scenario_name, width=32).pack(
            side="left", padx=8)

        # Notebook tabs
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=16, pady=4)

        self._build_process_tab(nb, cfg)
        self._build_scheduler_tab(nb, cfg)
        self._build_memory_tab(nb, cfg)
        self._build_scenario_tab(nb)

        # Bottom buttons
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", padx=16, pady=(4, 12))

        ttk.Button(btn_frame, text="Rastgele Üret",
                   command=self._random_scenario).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Sıfırla",
                   command=self._reset).pack(side="left", padx=4)

        ttk.Button(btn_frame, text="▶  Simülasyonu Başlat",
                   style="Accent.TButton",
                   command=self._start).pack(side="right", padx=4)

    def _build_process_tab(self, nb: ttk.Notebook, cfg: ScenarioConfig) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="  Processler  ")
        self._proc_table = _ProcessTable(frame)
        self._proc_table.pack(fill="both", expand=True, padx=8, pady=8)
        if cfg.processes:
            self._proc_table.load_processes(cfg.processes)

    def _build_scheduler_tab(self, nb: ttk.Notebook, cfg: ScenarioConfig) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="  Zamanlayıcı  ")

        lf = ttk.LabelFrame(frame, text=" Algoritma Seçimi ")
        lf.pack(fill="x", padx=16, pady=12)

        ttk.Label(lf, text="Algoritma:").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self._algo_var = tk.StringVar(value=cfg.algorithm)
        combo = ttk.Combobox(lf, textvariable=self._algo_var,
                             values=_ALGORITHMS, state="readonly", width=16)
        combo.grid(row=0, column=1, padx=8, pady=8, sticky="w")
        combo.bind("<<ComboboxSelected>>", self._on_algo_change)

        ttk.Label(lf, text="Quantum (RR):").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self._quantum_var = tk.IntVar(value=cfg.quantum)
        self._quantum_spin = ttk.Spinbox(lf, textvariable=self._quantum_var,
                                         from_=1, to=20, width=6)
        self._quantum_spin.grid(row=1, column=1, padx=8, pady=8, sticky="w")

        # Algo descriptions
        self._algo_desc_var = tk.StringVar()
        ttk.Label(lf, textvariable=self._algo_desc_var,
                  foreground="#6c7086", wraplength=340).grid(
            row=2, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        self._update_algo_desc()

    def _build_memory_tab(self, nb: ttk.Notebook, cfg: ScenarioConfig) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="  Bellek  ")

        lf = ttk.LabelFrame(frame, text=" Bellek Yapılandırması ")
        lf.pack(fill="x", padx=16, pady=12)

        ttk.Label(lf, text="Toplam boyut (byte):").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self._mem_size_var = tk.IntVar(value=cfg.memory_size)
        ttk.Spinbox(lf, textvariable=self._mem_size_var,
                    from_=128, to=16384, increment=128, width=8).grid(
            row=0, column=1, padx=8, pady=8, sticky="w")

        ttk.Label(lf, text="Strateji:").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self._strategy_var = tk.StringVar(value=cfg.memory_strategy)
        ttk.Combobox(lf, textvariable=self._strategy_var,
                     values=_STRATEGIES, state="readonly", width=14).grid(
            row=1, column=1, padx=8, pady=8, sticky="w")

        descs = {
            "FIRST_FIT": "İlk uygun bloğu seç — hızlı ama dağınık",
            "BEST_FIT":  "En küçük uygun bloğu seç — az iç parçalanma",
            "WORST_FIT": "En büyük uygun bloğu seç — kalan parça büyük kalır",
        }
        for i, (strat, desc) in enumerate(descs.items()):
            ttk.Label(lf, text=f"  {strat}: {desc}",
                      foreground="#6c7086").grid(
                row=2 + i, column=0, columnspan=2, padx=12, pady=1, sticky="w")

    def _build_scenario_tab(self, nb: ttk.Notebook) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="  Senaryolar  ")

        # Builtin scenarios
        bi_lf = ttk.LabelFrame(frame, text=" Hazır Senaryolar ")
        bi_lf.pack(fill="x", padx=16, pady=(12, 4))

        self._builtin_var = tk.StringVar(value=list(BUILTIN_SCENARIOS.keys())[0])
        combo = ttk.Combobox(bi_lf, textvariable=self._builtin_var,
                             values=list(BUILTIN_SCENARIOS.keys()),
                             state="readonly", width=30)
        combo.pack(side="left", padx=8, pady=8)
        ttk.Button(bi_lf, text="Yükle",
                   command=self._load_builtin).pack(side="left", padx=4)

        # File operations
        file_lf = ttk.LabelFrame(frame, text=" Dosya İşlemleri ")
        file_lf.pack(fill="x", padx=16, pady=4)

        ttk.Button(file_lf, text="💾 JSON'a Kaydet",
                   command=self._save_json).pack(side="left", padx=8, pady=8)
        ttk.Button(file_lf, text="📂 JSON Yükle",
                   command=self._load_json).pack(side="left", padx=4, pady=8)

        # Info
        info = ttk.Label(frame,
                         text="Senaryolar .json formatında kaydedilir.\n"
                              "Tüm process, zamanlayıcı ve bellek ayarları saklanır.",
                         foreground="#6c7086")
        info.pack(padx=16, pady=8, anchor="w")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_algo_change(self, _event=None) -> None:
        self._update_algo_desc()

    def _update_algo_desc(self) -> None:
        descs = {
            "FCFS":       "First Come First Served — en basit, non-preemptive",
            "SJF":        "Shortest Job First — en kısa burst önce, non-preemptive",
            "SRTF":       "Shortest Remaining Time First — SJF'in preemptive hali",
            "RoundRobin": "Round Robin — her process quantum kadar CPU alır, Quantum değeri aktif",
            "Priority":   "Priority Scheduling — düşük sayı = yüksek öncelik, preemptive",
        }
        self._algo_desc_var.set(descs.get(self._algo_var.get(), ""))
        is_rr = self._algo_var.get() == "RoundRobin"
        self._quantum_spin.configure(state="normal" if is_rr else "disabled")

    def _load_builtin(self) -> None:
        name = self._builtin_var.get()
        cfg  = BUILTIN_SCENARIOS[name]
        self._apply_config(cfg)

    def _random_scenario(self) -> None:
        cfg = random_scenario(n=5)
        self._apply_config(cfg)

    def _reset(self) -> None:
        self._apply_config(ScenarioConfig())

    def _apply_config(self, cfg: ScenarioConfig) -> None:
        self._scenario_name.set(cfg.name)
        self._proc_table.load_processes(cfg.processes)
        self._algo_var.set(cfg.algorithm)
        self._quantum_var.set(cfg.quantum)
        self._mem_size_var.set(cfg.memory_size)
        self._strategy_var.set(cfg.memory_strategy)
        self._update_algo_desc()

    def _save_json(self) -> None:
        cfg  = self._collect_config()
        if cfg is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tüm dosyalar", "*.*")],
            title="Senaryo kaydet",
            initialfile=cfg.name.replace(" ", "_") + ".json",
        )
        if path:
            save_scenario(cfg, path)
            messagebox.showinfo("Kaydedildi", f"Senaryo kaydedildi:\n{path}")

    def _load_json(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Tüm dosyalar", "*.*")],
            title="Senaryo yükle",
        )
        if path:
            try:
                cfg = load_scenario(path)
                self._apply_config(cfg)
            except Exception as exc:
                messagebox.showerror("Hata", f"Senaryo yüklenemedi:\n{exc}")

    def _collect_config(self) -> Optional[ScenarioConfig]:
        procs = self._proc_table.get_processes()
        if not procs:
            messagebox.showwarning("Uyarı", "En az 1 process ekleyin.")
            return None
        return ScenarioConfig(
            name=self._scenario_name.get().strip() or "Senaryo",
            processes=procs,
            algorithm=self._algo_var.get(),
            quantum=self._quantum_var.get(),
            memory_size=self._mem_size_var.get(),
            memory_strategy=self._strategy_var.get(),
        )

    def _start(self) -> None:
        cfg = self._collect_config()
        if cfg is not None:
            self._result = cfg
            self._root.destroy()

    # ------------------------------------------------------------------

    def run(self) -> Optional[ScenarioConfig]:
        self._root.mainloop()
        return self._result
