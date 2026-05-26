from .scenario import ScenarioConfig, ProcessConfig, save_scenario, load_scenario

__all__ = [
    "ScenarioConfig", "ProcessConfig", "save_scenario", "load_scenario",
    "GanttChart", "MemoryMapView", "StatsDashboard", "MainWindow", "ControlPanel",
]


def __getattr__(name: str):
    if name in ("GanttChart",):
        from .gantt_chart import GanttChart
        return GanttChart
    if name in ("MemoryMapView",):
        from .memory_map import MemoryMapView
        return MemoryMapView
    if name in ("StatsDashboard",):
        from .stats_dashboard import StatsDashboard
        return StatsDashboard
    if name in ("MainWindow",):
        from .main_window import MainWindow
        return MainWindow
    if name in ("ControlPanel",):
        from .control_panel import ControlPanel
        return ControlPanel
    raise AttributeError(f"module 'visualization' has no attribute {name!r}")
