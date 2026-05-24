try:
    import pygame
    import pygame.display
    import pygame.event
    import pygame.font
    import pygame.time
    import pygame.draw
except ImportError:
    raise ImportError(
        "pygame is required for visualization. Install with: pip install pygame"
    )

from core.process import ProcessState
from core.scheduler import SchedulerStats
from .gantt_chart import GanttChart
from .memory_map import MemoryMapView
from .stats_dashboard import StatsDashboard

_W, _H = 1024, 768
_BG = (20, 20, 30)
_HUD_BG = (14, 14, 22)
_HUD_FG = (170, 170, 195)
_DIV = (50, 50, 65)
_HUD_H = 20
_TOP_H = 384
_BOT_H = _H - _TOP_H - _HUD_H  # 364


def _compute_stats(processes, cpu_busy, total_ticks):
    completed = [p for p in processes if p.state == ProcessState.TERMINATED]
    return SchedulerStats(
        total_processes=len(processes),
        completed_processes=len(completed),
        total_waiting_time=sum(p.waiting_time for p in processes),
        total_turnaround_time=sum(
            p.turnaround_time for p in processes
            if p.state == ProcessState.TERMINATED
        ),
        total_response_time=sum(
            p.response_time for p in processes
            if p.response_time is not None
        ),
        cpu_busy_ticks=cpu_busy,
        total_ticks=max(total_ticks, 1),
        context_switches=0,
    )


class MainWindow:
    def __init__(self):
        self.tick_speed = 200  # ms between simulation steps
        self._gantt = GanttChart()
        self._memmap = MemoryMapView()
        self._stats = StatsDashboard()

    def run_simulation(self, processes, scheduler, memory_manager):
        pygame.init()
        screen = pygame.display.set_mode((_W, _H))
        pygame.display.set_caption("MaestroOS — Simulation")
        pg_clock = pygame.time.Clock()
        font = pygame.font.SysFont("monospace", 12)

        scheduler.load_processes(processes)

        total_mem = memory_manager.total_free + memory_manager.total_used
        mem_per_proc = max(16, total_mem // max(len(processes), 1))

        tick = 0
        paused = False
        cpu_busy = 0
        allocated = set()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.tick_speed = max(50, self.tick_speed - 50)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.tick_speed = min(2000, self.tick_speed + 50)

            if not paused and not scheduler.is_done:
                scheduler.tick(tick)

                # find the running process
                active = next(
                    (p for p in processes if p.state == ProcessState.RUNNING), None
                )
                if active:
                    self._gantt.add_entry(tick, active.pid, active.name)
                    cpu_busy += 1
                else:
                    self._gantt.add_entry(tick, None, "IDLE")

                # allocate memory for processes that just became ready/running
                for p in processes:
                    if p.pid not in allocated and p.state in (
                        ProcessState.READY, ProcessState.RUNNING
                    ):
                        res = memory_manager.allocate(p.pid, mem_per_proc)
                        if res.success:
                            allocated.add(p.pid)

                # deallocate terminated processes
                for p in processes:
                    if p.state == ProcessState.TERMINATED and p.pid in allocated:
                        memory_manager.deallocate(p.pid)
                        allocated.discard(p.pid)

                self._memmap.update(memory_manager.memory_map())
                self._stats.update(_compute_stats(processes, cpu_busy, tick + 1), processes)

                tick += 1
                pygame.time.wait(self.tick_speed)

            # --- render ---
            screen.fill(_BG)

            # dividers
            pygame.draw.line(screen, _DIV, (0, _TOP_H), (_W, _TOP_H), 1)
            pygame.draw.line(screen, _DIV, (_W // 2, _TOP_H), (_W // 2, _TOP_H + _BOT_H), 1)

            self._gantt.render(screen, 0, 0, _W, _TOP_H)
            self._memmap.render(screen, 0, _TOP_H, _W // 2, _BOT_H)
            self._stats.render(screen, _W // 2, _TOP_H, _W // 2, _BOT_H)

            # HUD
            if scheduler.is_done:
                status = "DONE — press ESC to exit"
            elif paused:
                status = "PAUSED"
            else:
                status = "RUNNING"

            hud_text = (
                f"Tick:{tick}  Speed:{self.tick_speed}ms  {status}  "
                f"[SPACE=pause  +/-=speed  ESC=quit]"
            )
            pygame.draw.rect(screen, _HUD_BG, (0, _TOP_H + _BOT_H, _W, _HUD_H))
            hud = font.render(hud_text, True, _HUD_FG)
            screen.blit(hud, (5, _TOP_H + _BOT_H + 4))

            pygame.display.flip()
            if paused or scheduler.is_done:
                pg_clock.tick(30)

        pygame.quit()


if __name__ == "__main__":
    from core.process import Process
    from core.scheduler import Scheduler
    from core.memory_manager import MemoryManager, AllocationStrategy
    from algorithms.scheduling.round_robin import RoundRobin

    processes = [
        Process(pid=1, name="Chrome",  burst_time=15, arrival_time=0, priority=2),
        Process(pid=2, name="VSCode",  burst_time=8,  arrival_time=2, priority=1),
        Process(pid=3, name="Firefox", burst_time=12, arrival_time=4, priority=3),
        Process(pid=4, name="Python",  burst_time=5,  arrival_time=1, priority=1),
    ]

    scheduler = Scheduler(algorithm=RoundRobin(quantum=3))
    scheduler.load_processes(processes)

    mm = MemoryManager(total_size=1024, strategy=AllocationStrategy.BEST_FIT)

    window = MainWindow()
    window.run_simulation(processes, scheduler, mm)
