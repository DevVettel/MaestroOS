"""
MaestroOS — Giriş noktası.

Threading modeli (Windows COM uyumlu):
  - tkinter ana thread'de çalışır (Tcl apartment threading zorunluluğu)
  - pygame arka plan thread'de çalışır (SDL2 bunu destekler)
  - SimulationBridge ikisi arasında thread-safe iletişimi sağlar
"""

from __future__ import annotations

import threading

from visualization.control_panel import ControlPanel
from visualization.main_window import MainWindow, SimulationBridge


def main() -> None:
    bridge = SimulationBridge()

    # ControlPanel.__init__ burada çağrılır — tk.Tk() ana thread'de oluşturulur
    panel = ControlPanel()
    panel.on_start(bridge.push_start)
    panel.on_pause(bridge.toggle_pause)
    panel.on_reset(bridge.push_reset)
    panel.on_speed_change(bridge.set_speed)

    window = MainWindow()
    pygame_thread = threading.Thread(
        target=window.run_with_bridge,
        args=(bridge,),
        daemon=True,
        name="pygame-sim",
    )
    pygame_thread.start()

    panel.run()  # tkinter mainloop — ana thread'de bloklar, pencere kapanınca döner

    bridge.request_quit()        # pygame döngüsüne çıkış sinyali
    pygame_thread.join(timeout=3)


if __name__ == "__main__":
    main()
