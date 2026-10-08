import os
import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QObject, pyqtSlot

from config_manager import ConfigManager
from usage_tracker import UsageTracker
from lock_manager import LockManager
from pushup_detector import PushUpDetector
from ui.lock_screen import LockScreen
from ui.config_window import ConfigWindow
from ui.stats_window import StatsWindow

ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def _icon(name: str) -> QIcon:
    return QIcon(os.path.join(ASSETS, name))


class TrayApp(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._config = ConfigManager()
        self._usage  = UsageTracker(self._config)
        self._lock_mgr = LockManager()
        self._detector: PushUpDetector | None = None
        self._lock_screen: LockScreen | None = None
        self._is_locked = False
        self._paused    = False

        self._setup_tray()
        self._usage.lock_triggered.connect(self._on_lock_triggered)
        self._usage.tick.connect(self._on_tick)
        self._usage.start()

    # ----------------------------------------------------------------- tray

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(_icon("icon_green.png"))
        menu = QMenu()
        menu.addAction("Configuración", self._open_config)
        menu.addAction("Estadísticas",  self._open_stats)
        self._pause_action = menu.addAction("Pausar", self._toggle_pause)
        menu.addSeparator()
        menu.addAction("Salir", self._quit)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip("FlexionLock — activo")
        self._tray.show()

    def _open_config(self):
        win = ConfigWindow(self._config)
        win.exec()
        if win.result():
            cfg = self._config.get_config()
            if cfg.get("autostart"):
                self._lock_mgr.set_autostart(True, sys.executable)
            else:
                self._lock_mgr.set_autostart(False, sys.executable)

    def _open_stats(self):
        StatsWindow(self._config).exec()

    def _toggle_pause(self):
        if self._paused:
            self._usage.resume()
            self._pause_action.setText("Pausar")
            self._tray.setToolTip("FlexionLock — activo")
            self._paused = False
        else:
            self._usage.pause()
            self._pause_action.setText("Reanudar")
            self._tray.setToolTip("FlexionLock — pausado")
            self._paused = True

    def _quit(self):
        self._usage.stop()
        self._lock_mgr.unlock()
        self._app.quit()

    # --------------------------------------------------------------- signals

    @pyqtSlot(str)
    def _on_lock_triggered(self, reason: str):
        if self._is_locked:
            return
        self._is_locked = True

        config = self._config.get_config()
        stats  = self._config.get_stats()
        # lock_count not yet incremented → current value = locks so far today
        target_reps = (
            config["reps_base"]
            + stats["lock_count"] * config["reps_increment"]
        )
        self._config.increment_lock_count()

        self._lock_screen = LockScreen(target_reps)
        self._detector    = PushUpDetector(target_reps, config["camera_index"])

        self._detector.frame_ready.connect(self._lock_screen.update_frame)
        self._detector.rep_counted.connect(self._lock_screen.update_count)
        self._detector.rep_counted.connect(self._on_rep_counted)
        self._detector.unlock_ready.connect(self._on_unlock)
        self._detector.camera_error.connect(self._lock_screen.show_camera_error)

        self._lock_mgr.lock(self._lock_screen)
        self._detector.start()
        self._tray.setIcon(_icon("icon_red.png"))
        self._tray.setToolTip("FlexionLock — bloqueado")

    @pyqtSlot(int)
    def _on_rep_counted(self, count: int):
        self._config.add_pushups(1)

    @pyqtSlot()
    def _on_unlock(self):
        if self._detector:
            self._detector.stop()
            self._detector = None
        self._lock_mgr.unlock()
        self._usage.reset_session()
        self._is_locked = False
        self._tray.setIcon(_icon("icon_green.png"))
        self._tray.setToolTip("FlexionLock — activo")
        self._lock_screen = None

    @pyqtSlot(int, int)
    def _on_tick(self, session_secs: int, _daily_secs: int):
        config = self._config.get_config()
        remaining = config["session_limit_min"] * 60 - session_secs
        if not self._is_locked and not self._paused and remaining <= 300:
            self._tray.setIcon(_icon("icon_yellow.png"))
            self._tray.setToolTip(f"FlexionLock — quedan {remaining // 60}m {remaining % 60}s")
        elif not self._is_locked and not self._paused:
            self._tray.setIcon(_icon("icon_green.png"))
