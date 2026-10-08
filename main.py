import sys
import os
import ctypes

# Request single instance (optional — prevents running twice)
# Ensure we run as administrator
if os.name == "nt":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # Re-launch as admin
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from tray_app import TrayApp


def main():
    # Required for system tray on Windows
    QApplication.setQuitOnLastWindowClosed(False)
    app = QApplication(sys.argv)
    app.setApplicationName("FlexionLock")
    tray = TrayApp(app)  # noqa: F841 — kept alive via app event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
