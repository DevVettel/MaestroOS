try:
    import pygame
    import pygame.font
except ImportError:
    raise ImportError(
        "pygame is required for visualization. Install with: pip install pygame"
    )

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

_BG_HEX = "#1c1c26"
_FG = "#c8c8dc"
_PLOT_BG = "#28283a"
_BLUE = "#5aafff"
_BAR_COLORS = [
    "#5a9fff", "#ff7a5a", "#5aff9f",
    "#ffd05a", "#c05aff", "#ff5a9f",
    "#9fff5a", "#5affff",
]


class StatsDashboard:
    def __init__(self):
        self._cpu_history = []
        self._process_waiting = {}  # name -> waiting_time
        self._fig = Figure(figsize=(5, 3.2), facecolor=_BG_HEX)
        self._ax1 = self._fig.add_subplot(121)
        self._ax2 = self._fig.add_subplot(122)
        self._canvas = FigureCanvasAgg(self._fig)
        self._cached = None
        self._dirty = True

    def update(self, stats, processes=None):
        self._cpu_history.append(stats.cpu_utilization * 100)
        if len(self._cpu_history) > 200:
            self._cpu_history = self._cpu_history[-200:]

        if processes:
            self._process_waiting = {p.name: p.waiting_time for p in processes}

        self._dirty = True

    def _redraw(self, width, height):
        dpi = 80
        self._fig.set_size_inches(width / dpi, height / dpi)
        self._ax1.clear()
        self._ax2.clear()

        for ax in (self._ax1, self._ax2):
            ax.set_facecolor(_PLOT_BG)
            ax.tick_params(colors=_FG, labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#3a3a4e")

        # CPU utilization line chart
        data = self._cpu_history
        if data:
            xs = list(range(len(data)))
            self._ax1.plot(xs, data, color=_BLUE, linewidth=1.5,
                           solid_capstyle="round")
            self._ax1.fill_between(xs, data, alpha=0.25, color=_BLUE)
        self._ax1.set_ylim(0, 105)
        self._ax1.set_title("CPU Util %", color=_FG, fontsize=8, pad=2)
        self._ax1.set_xlabel("Tick", color=_FG, fontsize=7)

        # Waiting time per process bar chart
        if self._process_waiting:
            names = list(self._process_waiting.keys())
            waits = [self._process_waiting[n] for n in names]
            colors = [_BAR_COLORS[i % len(_BAR_COLORS)] for i in range(len(names))]
            self._ax2.bar(names, waits, color=colors, width=0.6,
                          edgecolor="#1c1c26", linewidth=0.5)
            if len(names) > 3:
                self._ax2.tick_params(axis="x", rotation=30, labelsize=6)
        else:
            self._ax2.text(0.5, 0.5, "No data", transform=self._ax2.transAxes,
                           ha="center", va="center", color=_FG, fontsize=9)
        self._ax2.set_title("Wait Time", color=_FG, fontsize=8, pad=2)
        self._ax2.set_xlabel("Process", color=_FG, fontsize=7)

        self._fig.tight_layout(pad=1.2)
        self._canvas.draw()

        buf = self._canvas.buffer_rgba()
        w, h = self._canvas.get_width_height()
        return pygame.image.frombuffer(bytes(buf), (w, h), "RGBA")

    def render(self, surface, x, y, width, height):
        if surface is None:
            return

        if self._dirty or self._cached is None:
            self._cached = self._redraw(width, height)
            self._dirty = False

        scaled = pygame.transform.scale(self._cached, (width, height))
        surface.blit(scaled, (x, y))
