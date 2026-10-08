from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFormLayout, QGroupBox
from PyQt6.QtCore import Qt


def _fmt_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


class StatsWindow(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FlexionLock — Estadísticas de hoy")
        self.setMinimumWidth(300)

        stats  = config_manager.get_stats()
        config = config_manager.get_config()

        lock_count = stats["lock_count"]
        next_reps  = config["reps_base"] + lock_count * config["reps_increment"]

        layout = QVBoxLayout()
        group  = QGroupBox("Hoy")
        form   = QFormLayout()
        form.addRow("Tiempo activo:",         QLabel(_fmt_time(stats["active_seconds"])))
        form.addRow("Bloqueos activados:",    QLabel(str(lock_count)))
        form.addRow("Flexiones completadas:", QLabel(str(stats["pushups_total"])))
        form.addRow("Próximo bloqueo pedirá:", QLabel(f"{next_reps} flexiones"))
        group.setLayout(form)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)

        layout.addWidget(group)
        layout.addWidget(btn_close)
        self.setLayout(layout)
