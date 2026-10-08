import sys
import cv2
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QRadioButton, QLabel, QSpinBox, QComboBox,
    QCheckBox, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt

PRESETS = {
    "suave":      {"session_limit_min": 60, "daily_limit_min": 180, "reps_base": 5,  "reps_increment": 3},
    "moderado":   {"session_limit_min": 45, "daily_limit_min": 120, "reps_base": 8,  "reps_increment": 5},
    "duro":       {"session_limit_min": 30, "daily_limit_min": 90,  "reps_base": 12, "reps_increment": 7},
}


class ConfigWindow(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self.setWindowTitle("FlexionLock — Configuración")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Presets
        preset_group = QGroupBox("Preset")
        preset_layout = QVBoxLayout()
        self._radio_suave    = QRadioButton("Suave    (60 min sesión / 3h diario / 5+3 flexiones)")
        self._radio_moderado = QRadioButton("Moderado (45 min sesión / 2h diario / 8+5 flexiones)")
        self._radio_duro     = QRadioButton("Duro     (30 min sesión / 1.5h diario / 12+7 flexiones)")
        self._radio_custom   = QRadioButton("Personalizado")
        for r in (self._radio_suave, self._radio_moderado, self._radio_duro, self._radio_custom):
            preset_layout.addWidget(r)
            r.toggled.connect(self._on_preset_toggled)
        preset_group.setLayout(preset_layout)

        # Custom fields
        self._custom_group = QGroupBox("Configuración personalizada")
        form = QFormLayout()
        self._spin_session = QSpinBox(); self._spin_session.setRange(1, 480); self._spin_session.setSuffix(" min")
        self._spin_daily   = QSpinBox(); self._spin_daily.setRange(1, 1440); self._spin_daily.setSuffix(" min")
        self._spin_reps    = QSpinBox(); self._spin_reps.setRange(1, 100)
        self._spin_incr    = QSpinBox(); self._spin_incr.setRange(0, 50)
        form.addRow("Límite por sesión:", self._spin_session)
        form.addRow("Límite diario:", self._spin_daily)
        form.addRow("Flexiones base:", self._spin_reps)
        form.addRow("Incremento por bloqueo:", self._spin_incr)
        self._custom_group.setLayout(form)

        # Camera
        cam_group = QGroupBox("Cámara")
        cam_layout = QHBoxLayout()
        cam_layout.addWidget(QLabel("Cámara:"))
        self._combo_camera = QComboBox()
        self._populate_cameras()
        cam_layout.addWidget(self._combo_camera)
        cam_group.setLayout(cam_layout)

        # Autostart
        self._chk_autostart = QCheckBox("Iniciar con Windows")

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save   = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")
        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        layout.addWidget(preset_group)
        layout.addWidget(self._custom_group)
        layout.addWidget(cam_group)
        layout.addWidget(self._chk_autostart)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _populate_cameras(self):
        self._combo_camera.clear()
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self._combo_camera.addItem(f"Cámara {i}", userData=i)
                cap.release()
        if self._combo_camera.count() == 0:
            self._combo_camera.addItem("Sin cámaras detectadas", userData=0)

    def _on_preset_toggled(self):
        is_custom = self._radio_custom.isChecked()
        self._custom_group.setEnabled(is_custom)

    def _load_current_config(self):
        cfg = self._config.get_config()
        preset = cfg.get("preset", "moderado")
        radio_map = {
            "suave": self._radio_suave,
            "moderado": self._radio_moderado,
            "duro": self._radio_duro,
            "personalizado": self._radio_custom,
        }
        radio_map.get(preset, self._radio_moderado).setChecked(True)
        self._spin_session.setValue(cfg.get("session_limit_min", 45))
        self._spin_daily.setValue(cfg.get("daily_limit_min", 120))
        self._spin_reps.setValue(cfg.get("reps_base", 8))
        self._spin_incr.setValue(cfg.get("reps_increment", 5))
        cam_idx = cfg.get("camera_index", 0)
        for i in range(self._combo_camera.count()):
            if self._combo_camera.itemData(i) == cam_idx:
                self._combo_camera.setCurrentIndex(i)
                break
        self._chk_autostart.setChecked(cfg.get("autostart", False))
        self._on_preset_toggled()

    def _save(self):
        if self._radio_suave.isChecked():
            preset = "suave"
        elif self._radio_moderado.isChecked():
            preset = "moderado"
        elif self._radio_duro.isChecked():
            preset = "duro"
        else:
            preset = "personalizado"

        if preset in PRESETS:
            cfg = self._config.get_config()
            cfg.update(PRESETS[preset])
            cfg["preset"] = preset
        else:
            cfg = self._config.get_config()
            cfg["preset"] = "personalizado"
            cfg["session_limit_min"] = self._spin_session.value()
            cfg["daily_limit_min"]   = self._spin_daily.value()
            cfg["reps_base"]         = self._spin_reps.value()
            cfg["reps_increment"]    = self._spin_incr.value()

        cfg["camera_index"] = self._combo_camera.currentData() or 0
        cfg["autostart"]    = self._chk_autostart.isChecked()
        self._config.save_config(cfg)
        self.accept()
