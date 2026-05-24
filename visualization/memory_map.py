try:
    import pygame
    import pygame.font
    import pygame.draw
except ImportError:
    raise ImportError(
        "pygame is required for visualization. Install with: pip install pygame"
    )

_BG = (28, 28, 38)
_FREE = (60, 180, 80)
_FRAG = (190, 60, 60)
_BORDER = (18, 18, 28)
_PID_COLORS = [
    ( 70, 130, 180),
    ( 30, 100, 210),
    (  0, 160, 160),
    ( 90,  90, 200),
    ( 50, 150, 200),
    (130,  80, 180),
    ( 80, 170, 130),
    (160, 100, 150),
    (100, 160,  80),
    (180, 120,  60),
]
_FRAG_RATIO = 0.05  # free blocks smaller than 5% of total are "fragmented"


class MemoryMapView:
    def __init__(self):
        self._blocks = []
        self._font = None
        self._small_font = None

    def _init_fonts(self):
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", 12)
            self._small_font = pygame.font.SysFont("monospace", 9)

    def _pid_color(self, pid):
        return _PID_COLORS[pid % len(_PID_COLORS)]

    def update(self, blocks):
        self._blocks = list(blocks)

    def render(self, surface, x, y, width, height):
        if surface is None:
            return
        self._init_fonts()

        pygame.draw.rect(surface, _BG, (x, y, width, height))
        title = self._font.render("Memory Map", True, (210, 210, 225))
        surface.blit(title, (x + width // 2 - 40, y + 3))

        if not self._blocks:
            msg = self._small_font.render("No blocks", True, (120, 120, 140))
            surface.blit(msg, (x + 10, y + height // 2))
            return

        total = sum(b.size for b in self._blocks)
        if total == 0:
            return

        frag_thresh = total * _FRAG_RATIO
        pad = 5
        map_x = x + pad
        map_y = y + 20
        map_w = width - pad * 2
        map_h = height - 44

        cursor = map_x
        for block in self._blocks:
            bw = max(1, int((block.size / total) * map_w))
            if block.is_free:
                color = _FRAG if block.size < frag_thresh else _FREE
            else:
                color = self._pid_color(block.pid)

            pygame.draw.rect(surface, color, (cursor, map_y, bw, map_h))
            pygame.draw.rect(surface, _BORDER, (cursor, map_y, bw, map_h), 1)

            if bw > 28:
                if block.is_free:
                    l1 = self._small_font.render("FREE", True, (230, 230, 230))
                    l2 = self._small_font.render(f"{block.size}B", True, (200, 200, 200))
                else:
                    l1 = self._small_font.render(f"P{block.pid}", True, (230, 230, 230))
                    l2 = self._small_font.render(f"{block.size}B", True, (200, 200, 200))
                mid = map_y + map_h // 2
                surface.blit(l1, (cursor + 2, mid - 11))
                surface.blit(l2, (cursor + 2, mid + 1))

            cursor += bw

        # legend
        leg_y = map_y + map_h + 6
        items = [(_FREE, "Free"), (_FRAG, "Frag"), (_PID_COLORS[0], "Alloc'd")]
        lx = x + pad
        for color, label in items:
            pygame.draw.rect(surface, color, (lx, leg_y, 10, 10))
            pygame.draw.rect(surface, _BORDER, (lx, leg_y, 10, 10), 1)
            txt = self._small_font.render(label, True, (170, 170, 185))
            surface.blit(txt, (lx + 13, leg_y))
            lx += 60
