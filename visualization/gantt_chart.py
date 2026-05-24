try:
    import pygame
    import pygame.font
    import pygame.draw
except ImportError:
    raise ImportError(
        "pygame is required for visualization. Install with: pip install pygame"
    )

_PALETTE = [
    (220,  80,  80),
    ( 80, 140, 220),
    ( 80, 200, 120),
    (220, 160,  80),
    (180,  80, 220),
    ( 80, 210, 210),
    (220,  80, 160),
    (160, 220,  80),
    (220, 120,  80),
    ( 80, 180, 160),
    (160, 120, 220),
    (200, 180,  80),
]
_IDLE_COLOR = (100, 100, 110)
_BG = (28, 28, 38)
_CELL_EMPTY = (42, 42, 52)
_GRID_LINE = (44, 44, 56)


def _brighten(color, factor=1.35):
    return tuple(min(255, int(c * factor)) for c in color)


class GanttChart:
    WINDOW = 50  # visible tick count

    def __init__(self):
        self._entries = []       # list of (tick, pid, process_name)
        self._pid_order = []     # insertion-order unique pids
        self._pid_names = {}     # pid -> name
        self._font = None
        self._small_font = None

    def _init_fonts(self):
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", 12)
            self._small_font = pygame.font.SysFont("monospace", 10)

    def _color(self, pid, bright=False):
        base = _IDLE_COLOR if pid is None else _PALETTE[pid % len(_PALETTE)]
        return _brighten(base) if bright else base

    def add_entry(self, tick, pid, process_name):
        self._entries.append((tick, pid, process_name))
        if pid is not None and pid not in self._pid_names:
            self._pid_names[pid] = process_name
            self._pid_order.append(pid)

    def render(self, surface, x, y, width, height):
        if surface is None:
            return
        self._init_fonts()

        pygame.draw.rect(surface, _BG, (x, y, width, height))
        title = self._font.render("CPU Gantt Chart", True, (210, 210, 225))
        surface.blit(title, (x + width // 2 - 55, y + 3))

        if not self._entries:
            msg = self._small_font.render("Waiting for data...", True, (120, 120, 140))
            surface.blit(msg, (x + 10, y + height // 2))
            return

        latest = max(t for t, _, _ in self._entries)
        tick_start = max(0, latest - self.WINDOW + 1)

        has_idle = any(p is None for _, p, _ in self._entries)
        rows = [(pid, self._pid_names[pid]) for pid in self._pid_order]
        if has_idle:
            rows.append((None, "IDLE"))

        label_w = 72
        axis_h = 22
        cx0 = x + label_w
        cy0 = y + 20
        cw = width - label_w - 4
        ch = height - axis_h - 24

        n = max(len(rows), 1)
        row_h = max(ch // n, 8)
        cell_w = max(cw // self.WINDOW, 2)

        entry_set = {(t, p) for t, p, _ in self._entries}

        for ri, (pid, name) in enumerate(rows):
            ry = cy0 + ri * row_h
            lbl = self._small_font.render(name[:9], True, (190, 190, 200))
            surface.blit(lbl, (x + 2, ry + row_h // 2 - 5))
            pygame.draw.line(surface, _GRID_LINE, (cx0, ry), (cx0 + cw, ry), 1)

            for ci in range(self.WINDOW):
                tick = tick_start + ci
                tx = cx0 + ci * cell_w
                is_now = tick == latest
                active = (tick, pid) in entry_set

                if active:
                    color = _brighten(self._color(pid)) if is_now else self._color(pid)
                    pygame.draw.rect(surface, color,
                                     (tx + 1, ry + 2, cell_w - 2, row_h - 4))
                elif is_now:
                    pygame.draw.rect(surface, (55, 55, 72),
                                     (tx, ry, cell_w, row_h))

        # x-axis labels every 10 ticks
        ax_y = cy0 + len(rows) * row_h + 4
        for ci in range(self.WINDOW):
            if ci % 10 == 0:
                tick = tick_start + ci
                tx = cx0 + ci * cell_w
                lbl = self._small_font.render(str(tick), True, (130, 130, 150))
                surface.blit(lbl, (tx, ax_y))
