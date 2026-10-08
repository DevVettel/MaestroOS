"""
Deadlock görselleştirici — Resource Allocation Graph ve Banker's Algorithm.

İki mod:
  [1] RAG      — process'ler daire, kaynaklar kare (içinde instance noktaları).
                 İstek kenarı (P → R) kesikli, atama kenarı (R → P) düz çizilir.
                 Deadlock döngüsündeki düğüm ve kenarlar kırmızı vurgulanır.
  [2] Banker's — Allocation / Max / Need tablosu, Available vektörü,
                 güvenli sıra ve her talebin kabul/ret gerekçesi.

Kısayollar: SAĞ/SPACE ileri · SOL geri · R sıfırla · TAB sonraki senaryo ·
            1/2 mod · A otomatik oynat · ESC çıkış

Çalıştır: python main.py --deadlock [senaryo.json]
"""

from __future__ import annotations

import math
from pathlib import Path

try:
    import pygame
    import pygame.draw
    import pygame.font
except ImportError:
    raise ImportError(
        "pygame is required for visualization. Install with: pip install pygame"
    ) from None

from .deadlock_scenario import (
    BUILTIN_BANKER_SCENARIOS,
    BUILTIN_RAG_SCENARIOS,
    BankerScenario,
    BankerStepper,
    NodeKey,
    RAGScenario,
    RAGStepper,
    circular_layout,
    load_deadlock_scenario,
    scenario_node_order,
)

_W, _H = 1024, 768
_HEADER_H = 44
_HUD_H = 22
_PANEL_W = 360

_BG = (20, 20, 30)
_SURFACE = (28, 28, 38)
_HEADER_BG = (14, 14, 22)
_DIV = (50, 50, 65)
_FG = (210, 210, 225)
_MUTED = (120, 120, 140)
_ACCENT = (80, 140, 220)

_PROC = (70, 130, 180)
_RES = (130, 100, 60)
_RES_BORDER = (200, 160, 90)
_REQ_EDGE = (150, 150, 170)
_ASG_EDGE = (90, 190, 120)
_DEAD = (220, 70, 70)
_DEAD_GLOW = (110, 30, 30)
_SAFE = (80, 200, 120)
_WARN = (220, 170, 70)

_P_RADIUS = 30
_R_HALF = 30

_VERDICT_TEXT = {
    "granted": ("KABUL", _SAFE),
    "exceeds_need": ("RET: Max aşıldı", _WARN),
    "insufficient": ("RET: kaynak yetersiz, bekle", _WARN),
    "unsafe": ("RET: güvensiz durum", _DEAD),
}

_AUTOPLAY_MS = 1200


# ---------------------------------------------------------------------------
# Geometri yardımcıları
# ---------------------------------------------------------------------------

def _boundary_offset(key: NodeKey, dx: float, dy: float) -> float:
    """Düğüm merkezinden (dx, dy) yönünde kenarına olan uzaklık."""
    if key[0] == "P":
        return _P_RADIUS
    ax, ay = abs(dx), abs(dy)
    if ax < 1e-9 and ay < 1e-9:
        return _R_HALF
    return min(_R_HALF / ax if ax > 1e-9 else math.inf, _R_HALF / ay if ay > 1e-9 else math.inf)


def edge_endpoints(
    src_key: NodeKey,
    src: tuple[int, int],
    dst_key: NodeKey,
    dst: tuple[int, int],
    offset: float = 0.0,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    İki düğüm arasındaki okun başlangıç/bitiş noktalarını düğüm sınırlarına
    kırpar. `offset`, aynı çift arasındaki paralel kenarları ayırmak için
    dik yönde kaydırma miktarıdır.
    """
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy * offset, ux * offset
    s = _boundary_offset(src_key, ux, uy)
    e = _boundary_offset(dst_key, ux, uy)
    start = (src[0] + ux * s + px, src[1] + uy * s + py)
    end = (dst[0] - ux * e + px, dst[1] - uy * e + py)
    return start, end


def _draw_arrow(surface, color, start, end, width=2, dashed=False) -> None:
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    head = 12
    shaft_end = (ex - ux * head * 0.8, ey - uy * head * 0.8)

    if dashed:
        dash, gap = 8, 6
        pos = 0.0
        shaft_len = length - head * 0.8
        while pos < shaft_len:
            seg_end = min(pos + dash, shaft_len)
            pygame.draw.line(
                surface, color,
                (sx + ux * pos, sy + uy * pos),
                (sx + ux * seg_end, sy + uy * seg_end),
                width,
            )
            pos += dash + gap
    else:
        pygame.draw.line(surface, color, start, shaft_end, width)

    left = (ex - ux * head - uy * head * 0.5, ey - uy * head + ux * head * 0.5)
    right = (ex - ux * head + uy * head * 0.5, ey - uy * head - ux * head * 0.5)
    pygame.draw.polygon(surface, color, [end, left, right])


# ---------------------------------------------------------------------------
# Visualizer
# ---------------------------------------------------------------------------

class DeadlockVisualizer:
    """
    Durum + çizim. Pencere döngüsünden bağımsızdır: render() herhangi bir
    pygame.Surface'e çizer, handle_key() klavye olayını işler. Bu ayrım
    sayesinde headless testte doğrudan bir Surface üzerinde çalıştırılabilir.
    """

    def __init__(
        self,
        rag_scenarios: list[RAGScenario] | None = None,
        banker_scenarios: list[BankerScenario] | None = None,
        mode: str = "rag",
    ) -> None:
        self.rag_scenarios = rag_scenarios or list(BUILTIN_RAG_SCENARIOS)
        self.banker_scenarios = banker_scenarios or list(BUILTIN_BANKER_SCENARIOS)
        self.mode = mode
        self.rag_index = 0
        self.banker_index = 0
        self.rag = RAGStepper(self.rag_scenarios[0])
        self.banker = BankerStepper(self.banker_scenarios[0])
        self.autoplay = False
        self._since_step = 0
        self._fonts: dict[str, pygame.font.Font] = {}

    # ------------------------------------------------------------------
    # Girdi
    # ------------------------------------------------------------------

    @property
    def stepper(self) -> RAGStepper | BankerStepper:
        return self.rag if self.mode == "rag" else self.banker

    def next_scenario(self) -> None:
        if self.mode == "rag":
            self.rag_index = (self.rag_index + 1) % len(self.rag_scenarios)
            self.rag = RAGStepper(self.rag_scenarios[self.rag_index])
        else:
            self.banker_index = (self.banker_index + 1) % len(self.banker_scenarios)
            self.banker = BankerStepper(self.banker_scenarios[self.banker_index])
        self.autoplay = False

    def handle_key(self, key: int) -> bool:
        """Klavye olayını işler. Çıkış istenirse False döner."""
        if key == pygame.K_ESCAPE:
            return False
        if key in (pygame.K_RIGHT, pygame.K_SPACE):
            self.stepper.forward()
        elif key == pygame.K_LEFT:
            self.stepper.back()
            self.autoplay = False
        elif key == pygame.K_r:
            self.stepper.reset()
            self.autoplay = False
        elif key in (pygame.K_TAB, pygame.K_n):
            self.next_scenario()
        elif key == pygame.K_1:
            self.mode = "rag"
            self.autoplay = False
        elif key == pygame.K_2:
            self.mode = "banker"
            self.autoplay = False
        elif key == pygame.K_a:
            self.autoplay = not self.autoplay
            self._since_step = 0
        return True

    def update(self, dt_ms: int) -> None:
        """Otomatik oynatma açıksa belirli aralıklarla bir adım ilerler."""
        if not self.autoplay:
            return
        self._since_step += dt_ms
        if self._since_step >= _AUTOPLAY_MS:
            self._since_step = 0
            if not self.stepper.forward():
                self.autoplay = False

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def _font(self, name: str) -> pygame.font.Font:
        if not self._fonts:
            pygame.font.init()
            self._fonts = {
                "sm": pygame.font.SysFont("monospace", 12),
                "md": pygame.font.SysFont("monospace", 14),
                "md_b": pygame.font.SysFont("monospace", 14, bold=True),
                "lg": pygame.font.SysFont("monospace", 18, bold=True),
            }
        return self._fonts[name]

    def _text(self, surface, text, pos, color=_FG, font="md") -> int:
        img = self._font(font).render(text, True, color)
        surface.blit(img, pos)
        return img.get_height()

    def render(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(_BG)
        self._render_header(surface, w)
        body = pygame.Rect(0, _HEADER_H, w, h - _HEADER_H - _HUD_H)
        if self.mode == "rag":
            self._render_rag(surface, body)
        else:
            self._render_banker(surface, body)
        self._render_hud(surface, w, h)

    def _render_header(self, surface, w) -> None:
        pygame.draw.rect(surface, _HEADER_BG, (0, 0, w, _HEADER_H))
        x = 12
        for key, label in (("rag", "[1] RAG"), ("banker", "[2] Banker's")):
            color = _ACCENT if self.mode == key else _MUTED
            img = self._font("md_b").render(label, True, color)
            surface.blit(img, (x, 14))
            if self.mode == key:
                pygame.draw.line(surface, _ACCENT, (x, 36), (x + img.get_width(), 36), 2)
            x += img.get_width() + 24

        if self.mode == "rag":
            name, idx, total = self.rag.scenario.name, self.rag_index, len(self.rag_scenarios)
        else:
            name, idx, total = self.banker.scenario.name, self.banker_index, len(self.banker_scenarios)
        title = self._font("lg").render(f"{name}  ({idx + 1}/{total})", True, _FG)
        surface.blit(title, (w - title.get_width() - 12, 11))

    def _render_hud(self, surface, w, h) -> None:
        pygame.draw.rect(surface, _HEADER_BG, (0, h - _HUD_H, w, _HUD_H))
        step = self.stepper
        auto = "  >> AUTO" if self.autoplay else ""
        text = (
            f"Adım {step.step}/{step.total_steps}{auto}   "
            "[SAĞ/SPACE ileri  SOL geri  R sıfırla  TAB senaryo  1/2 mod  A oto  ESC çıkış]"
        )
        self._text(surface, text, (8, h - _HUD_H + 4), _MUTED, "sm")

    # --- RAG ---------------------------------------------------------

    def _render_rag(self, surface, body: pygame.Rect) -> None:
        graph = pygame.Rect(body.x, body.y, body.w - _PANEL_W, body.h)
        panel = pygame.Rect(graph.right, body.y, _PANEL_W, body.h)
        pygame.draw.line(surface, _DIV, (panel.x, panel.y), (panel.x, panel.bottom), 1)

        rag = self.rag.rag
        sc = self.rag.scenario
        pids = [p.pid for p in sc.processes]
        rids = [r.rid for r in sc.resources]
        radius = min(graph.w, graph.h) / 2 - 70
        pos = circular_layout(pids, rids, graph.centerx, graph.centery, radius, scenario_node_order(sc))

        deadlocked = set(self.rag.deadlocked)
        dead_edges = rag.get_deadlock_edges()
        last = self.rag.last_event

        # Kenarlar
        for pid in pids:
            for rid in rag.get_requested_resources(pid):
                hot = ("request", pid, rid) in dead_edges
                start, end = edge_endpoints(("P", pid), pos[("P", pid)], ("R", rid), pos[("R", rid)], -5)
                _draw_arrow(surface, _DEAD if hot else _REQ_EDGE, start, end, 3 if hot else 2, dashed=True)
            for rid in rag.get_held_resources(pid):
                hot = ("assignment", pid, rid) in dead_edges
                start, end = edge_endpoints(("R", rid), pos[("R", rid)], ("P", pid), pos[("P", pid)], 5)
                _draw_arrow(surface, _DEAD if hot else _ASG_EDGE, start, end, 3 if hot else 2)

        # Düğümler
        holders: dict[int, list[int]] = {rid: [] for rid in rids}
        for pid in pids:
            for rid in rag.get_held_resources(pid):
                holders[rid].append(pid)

        for res in sc.resources:
            cx, cy = pos[("R", res.rid)]
            in_cycle = any(e[2] == res.rid for e in dead_edges)
            rect = pygame.Rect(cx - _R_HALF, cy - _R_HALF, 2 * _R_HALF, 2 * _R_HALF)
            if in_cycle:
                pygame.draw.rect(surface, _DEAD_GLOW, rect.inflate(12, 12), border_radius=8)
            pygame.draw.rect(surface, _RES, rect, border_radius=6)
            pygame.draw.rect(surface, _DEAD if in_cycle else _RES_BORDER, rect, 2, border_radius=6)
            used = res.instances - rag.get_resource(res.rid).available_instances
            for i in range(res.instances):
                dot_x = cx - (res.instances - 1) * 7 + i * 14
                if i < used:
                    pygame.draw.circle(surface, _FG, (dot_x, cy + 10), 5)
                else:
                    pygame.draw.circle(surface, _FG, (dot_x, cy + 10), 5, 1)
            label = self._font("sm").render(f"R{res.rid}", True, _FG)
            surface.blit(label, (cx - label.get_width() // 2, cy - 18))
            name = self._font("sm").render(res.name, True, _MUTED)
            surface.blit(name, (cx - name.get_width() // 2, cy + _R_HALF + 6))

        for proc in sc.processes:
            cx, cy = pos[("P", proc.pid)]
            dead = proc.pid in deadlocked
            if dead:
                pygame.draw.circle(surface, _DEAD_GLOW, (cx, cy), _P_RADIUS + 8)
            pygame.draw.circle(surface, _DEAD if dead else _PROC, (cx, cy), _P_RADIUS)
            if last is not None and last.pid == proc.pid:
                pygame.draw.circle(surface, _WARN, (cx, cy), _P_RADIUS + 3, 2)
            label = self._font("md_b").render(f"P{proc.pid}", True, _FG)
            surface.blit(label, (cx - label.get_width() // 2, cy - label.get_height() // 2))
            name = self._font("sm").render(proc.name, True, _MUTED)
            surface.blit(name, (cx - name.get_width() // 2, cy + _P_RADIUS + 11))

        self._render_rag_panel(surface, panel, deadlocked)

    def _render_rag_panel(self, surface, panel: pygame.Rect, deadlocked: set[int]) -> None:
        x, y = panel.x + 14, panel.y + 12
        width = panel.w - 28

        # Durum kutusu
        status = pygame.Rect(x, y, width, 58)
        if deadlocked:
            pygame.draw.rect(surface, _DEAD_GLOW, status, border_radius=6)
            pygame.draw.rect(surface, _DEAD, status, 2, border_radius=6)
            self._text(surface, "DEADLOCK TESPİT EDİLDİ", (x + 10, y + 8), _DEAD, "md_b")
            procs = ", ".join(f"P{p}" for p in sorted(deadlocked))
            self._text(surface, f"Döngüdeki process'ler: {procs}", (x + 10, y + 32), _FG, "sm")
        else:
            pygame.draw.rect(surface, _SURFACE, status, border_radius=6)
            pygame.draw.rect(surface, _SAFE, status, 2, border_radius=6)
            self._text(surface, "Döngü yok — deadlock yok", (x + 10, y + 8), _SAFE, "md_b")
            self._text(surface, "Wait-for grafiği asiklik", (x + 10, y + 32), _MUTED, "sm")
        y += 72

        # Wait-for listesi
        y += self._text(surface, "Wait-for grafiği", (x, y), _FG, "md_b") + 4
        wait_for = self.rag.rag.get_wait_for_graph()
        any_edge = False
        for pid in sorted(wait_for):
            for target in sorted(wait_for[pid]):
                color = _DEAD if pid in deadlocked and target in deadlocked else _MUTED
                y += self._text(surface, f"  P{pid} -> P{target}", (x, y), color, "sm") + 2
                any_edge = True
        if not any_edge:
            y += self._text(surface, "  (boş)", (x, y), _MUTED, "sm") + 2
        y += 12

        # Olay günlüğü
        y += self._text(surface, "Olaylar", (x, y), _FG, "md_b") + 4
        events = self.rag.scenario.events
        visible = 12
        first = max(0, min(self.rag.step - visible // 2, len(events) - visible))
        for i in range(first, min(first + visible, len(events))):
            ev = events[i]
            done = i < self.rag.step
            current = i == self.rag.step - 1
            color = _WARN if current else (_FG if done else _DIV)
            prefix = ">" if current else ("+" if done else "-")
            text = ev.note or f"{ev.action} P{ev.pid} R{ev.rid}"
            for j, line in enumerate(self._wrap(text, width - 20, "sm")):
                self._text(surface, f"{prefix if j == 0 else ' '} {line}", (x, y), color, "sm")
                y += 15
            y += 3
        y = max(y, panel.bottom - 92)

        # Lejant
        lx, ly = x, panel.bottom - 84
        _draw_arrow(surface, _REQ_EDGE, (lx, ly + 6), (lx + 40, ly + 6), 2, dashed=True)
        self._text(surface, "istek  P -> R", (lx + 50, ly), _MUTED, "sm")
        _draw_arrow(surface, _ASG_EDGE, (lx, ly + 26), (lx + 40, ly + 26), 2)
        self._text(surface, "atama  R -> P", (lx + 50, ly + 20), _MUTED, "sm")
        pygame.draw.circle(surface, _FG, (lx + 6, ly + 48), 5)
        pygame.draw.circle(surface, _FG, (lx + 22, ly + 48), 5, 1)
        self._text(surface, "dolu / boş instance", (lx + 50, ly + 41), _MUTED, "sm")
        pygame.draw.circle(surface, _DEAD, (lx + 14, ly + 70), 7)
        self._text(surface, "deadlock döngüsü", (lx + 50, ly + 62), _MUTED, "sm")

    def _wrap(self, text: str, max_w: int, font: str) -> list[str]:
        f = self._font(font)
        lines: list[str] = []
        current = ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            if f.size(trial)[0] <= max_w or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    # --- Banker's ------------------------------------------------------

    def _render_banker(self, surface, body: pygame.Rect) -> None:
        sc = self.banker.scenario
        banker = self.banker.banker
        names = sc.resource_names
        n = len(names)
        x0, y = body.x + 24, body.y + 16

        y += self._text(surface, sc.description, (x0, y), _MUTED, "sm") + 14

        col_w = 34
        group_w = col_w * n + 24
        groups = ["Allocation", "Max", "Need"]
        header_x = x0 + 70

        for g, label in enumerate(groups):
            gx = header_x + g * group_w
            self._text(surface, label, (gx, y), _FG, "md_b")
            for j, rn in enumerate(names):
                self._text(surface, rn, (gx + j * col_w + 8, y + 20), _MUTED, "sm")
        y += 42

        safe_seq = banker.find_safe_sequence()
        last = self.banker.last_outcome
        for pid in banker.processes:
            row = pygame.Rect(x0 - 8, y - 4, 70 + group_w * 3, 24)
            if last is not None and last.request.pid == pid:
                color = _VERDICT_TEXT[last.verdict][1]
                pygame.draw.rect(surface, _SURFACE, row, border_radius=4)
                pygame.draw.rect(surface, color, row, 1, border_radius=4)
            self._text(surface, f"P{pid}", (x0, y), _FG, "md_b")
            vectors = [banker.get_allocation(pid), banker.max_demand[pid], banker.get_need(pid)]
            for g, vec in enumerate(vectors):
                gx = header_x + g * group_w
                for j, v in enumerate(vec):
                    self._text(surface, f"{v:>2}", (gx + j * col_w + 4, y), _FG, "md")
            y += 28

        y += 6
        self._text(surface, "Available", (x0, y), _ACCENT, "md_b")
        for j, v in enumerate(banker.get_available()):
            self._text(surface, f"{v:>2}", (header_x + j * col_w + 4, y), _ACCENT, "md")
        self._text(surface, "Total", (header_x + group_w, y), _MUTED, "md_b")
        for j, v in enumerate(sc.total):
            self._text(surface, f"{v:>2}", (header_x + group_w + 60 + j * col_w, y), _MUTED, "md")
        y += 40

        # Güvenli durum
        box = pygame.Rect(x0 - 8, y, body.w - 2 * (x0 - 8), 54)
        if safe_seq is not None:
            pygame.draw.rect(surface, _SURFACE, box, border_radius=6)
            pygame.draw.rect(surface, _SAFE, box, 2, border_radius=6)
            self._text(surface, "GÜVENLİ DURUM", (box.x + 12, box.y + 8), _SAFE, "md_b")
            seq = " -> ".join(f"P{p}" for p in safe_seq)
            self._text(surface, f"Güvenli sıra: {seq}", (box.x + 12, box.y + 30), _FG, "sm")
        else:
            pygame.draw.rect(surface, _DEAD_GLOW, box, border_radius=6)
            pygame.draw.rect(surface, _DEAD, box, 2, border_radius=6)
            self._text(surface, "GÜVENSİZ DURUM", (box.x + 12, box.y + 8), _DEAD, "md_b")
            self._text(surface, "Hiçbir güvenli yürütme sırası yok", (box.x + 12, box.y + 30), _FG, "sm")
        y = box.bottom + 18

        # Talep günlüğü
        y += self._text(surface, "Talepler", (x0, y), _FG, "md_b") + 6
        for i, req in enumerate(sc.requests):
            req_vec = "(" + ",".join(str(v) for v in req.request) + ")"
            if i < len(self.banker.outcomes):
                verdict, color = _VERDICT_TEXT[self.banker.outcomes[i].verdict]
                current = i == len(self.banker.outcomes) - 1
                prefix = ">" if current else "+"
                self._text(surface, f"{prefix} P{req.pid} {req_vec:<10} {verdict}", (x0, y), color, "md")
                self._text(surface, req.note, (x0 + 470, y + 2), _FG if current else _MUTED, "sm")
            else:
                self._text(surface, f"- P{req.pid} {req_vec}", (x0, y), _DIV, "md")
            y += 24


# ---------------------------------------------------------------------------
# Pencere döngüsü
# ---------------------------------------------------------------------------

def run(scenario_path: str | Path | None = None) -> None:
    """Deadlock görselleştiricisini kendi pygame penceresinde başlatır."""
    rag_list = list(BUILTIN_RAG_SCENARIOS)
    banker_list = list(BUILTIN_BANKER_SCENARIOS)
    mode = "rag"
    if scenario_path is not None:
        sc = load_deadlock_scenario(scenario_path)
        if isinstance(sc, RAGScenario):
            rag_list.insert(0, sc)
        else:
            banker_list.insert(0, sc)
            mode = "banker"

    viz = DeadlockVisualizer(rag_list, banker_list, mode=mode)

    pygame.init()
    screen = pygame.display.set_mode((_W, _H))
    pygame.display.set_caption("MaestroOS — Deadlock Görselleştirici")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                running = viz.handle_key(event.key)
        viz.update(clock.get_time())
        viz.render(screen)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    import sys

    run(sys.argv[1] if len(sys.argv) > 1 else None)
