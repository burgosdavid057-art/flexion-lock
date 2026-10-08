import time
import threading
import ctypes
import ctypes.wintypes
from PyQt6.QtCore import QThread, pyqtSignal


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class UsageTracker(QThread):
    lock_triggered = pyqtSignal(str)   # "session" or "daily"
    tick = pyqtSignal(int, int)        # session_seconds, daily_seconds

    IDLE_THRESHOLD_SECONDS = 60
    POLL_INTERVAL_SECONDS = 5

    def __init__(self, config_manager):
        super().__init__()
        self._config = config_manager
        self._session_seconds = 0
        self._daily_seconds = config_manager.get_stats()["active_seconds"]
        self._daily_limit_triggered = config_manager.get_stats()["daily_limit_triggered"]
        self._session_limit_triggered = False
        self._paused = False
        self._running = True
        self._stop_event = threading.Event()

    def run(self):
        while self._running:
            self._stop_event.wait(timeout=self.POLL_INTERVAL_SECONDS)
            if not self._running:
                break
            if not self._paused and self._is_user_active():
                self._session_seconds += self.POLL_INTERVAL_SECONDS
                self._daily_seconds += self.POLL_INTERVAL_SECONDS
                self._config.add_active_seconds(self.POLL_INTERVAL_SECONDS)
                self.tick.emit(self._session_seconds, self._daily_seconds)
                self._check_limits()

    def _is_user_active(self) -> bool:
        idle = self._get_idle_seconds()
        return idle < self.IDLE_THRESHOLD_SECONDS

    def _get_idle_seconds(self) -> float:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
        current_tick = ctypes.windll.kernel32.GetTickCount()
        idle_ms = current_tick - info.dwTime
        return idle_ms / 1000.0

    def _get_idle_seconds_mock(self, current_tick: int, last_input_tick: int) -> float:
        """Exposed for testing without Windows API."""
        return (current_tick - last_input_tick) / 1000.0

    def _check_limits(self):
        if self._paused:
            return
        config = self._config.get_config()
        session_limit = config["session_limit_min"] * 60
        daily_limit = config["daily_limit_min"] * 60

        if self._session_seconds >= session_limit and not self._session_limit_triggered:
            self._session_limit_triggered = True
            self.lock_triggered.emit("session")

        if self._daily_seconds >= daily_limit and not self._daily_limit_triggered:
            self._daily_limit_triggered = True
            self._config.set_daily_limit_triggered(True)
            self.lock_triggered.emit("daily")

    def reset_session(self):
        self._session_seconds = 0
        self._session_limit_triggered = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._stop_event.set()
        self._running = False
        self.wait()
