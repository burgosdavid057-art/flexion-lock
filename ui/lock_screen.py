import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QPalette


class LockScreen(QWidget):
    def __init__(self, target_reps: int):
        super().__init__()
        self.target_reps = target_reps
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet("background-color: #1a1a2e;")

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        self.title_label = QLabel("TIEMPO DE HACER FLEXIONES")
        font = QFont("Arial", 28, QFont.Weight.Bold)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #e94560;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Camera feed
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setText("Iniciando cámara...")
        self.camera_label.setStyleSheet(
            "background-color: #16213e; border: 2px solid #0f3460; color: #a8a8b3;"
        )

        # Counter
        self.counter_label = QLabel(f"0 / {self.target_reps}")
        counter_font = QFont("Arial", 36, QFont.Weight.Bold)
        self.counter_label.setFont(counter_font)
        self.counter_label.setStyleSheet("color: #ffffff;")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.target_reps)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #e94560;
                border-radius: 5px;
            }
        """)

        # Instruction
        self.instruction_label = QLabel(
            "Coloca la cámara de lado, a la altura del suelo"
        )
        self.instruction_label.setStyleSheet("color: #a8a8b3;")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e94560;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setVisible(False)

        layout.addWidget(self.title_label)
        layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.counter_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.error_label)

        self.setLayout(layout)

    def update_frame(self, frame: np.ndarray):
        """Called on every camera frame from PushUpDetector."""
        if frame is None or frame.size == 0:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(bytes(rgb.data), w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img).scaled(
            640, 480, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.camera_label.setPixmap(pixmap)

    def update_count(self, count: int):
        """Called when a rep is counted."""
        self.counter_label.setText(f"{count} / {self.target_reps}")
        self.progress_bar.setValue(count)

    def show_camera_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self.camera_label.setText("Sin cámara")
