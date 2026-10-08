import enum
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False


class RepState(enum.Enum):
    IDLE = "idle"
    UP = "up"
    DOWN = "down"


def calculate_angle(a, b, c, min_visibility: float = 0.7):
    """
    Calculate the angle at point b given landmarks a, b, c.
    Returns None if any landmark has visibility below min_visibility.
    """
    if any(lm.visibility < min_visibility for lm in (a, b, c)):
        return None

    pa = np.array([a.x, a.y])
    pb = np.array([b.x, b.y])
    pc = np.array([c.x, c.y])

    ba = pa - pb
    bc = pc - pb

    norm = np.linalg.norm(ba) * np.linalg.norm(bc)
    if norm < 1e-6:
        return None

    cos_angle = np.dot(ba, bc) / norm
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))


class PushUpDetector(QThread):
    frame_ready = pyqtSignal(object)   # numpy BGR frame with landmarks drawn
    rep_counted = pyqtSignal(int)      # current rep count
    unlock_ready = pyqtSignal()        # emitted when target reps reached
    camera_error = pyqtSignal(str)     # emitted when camera cannot be opened

    ANGLE_UP = 150.0    # arms extended
    ANGLE_DOWN = 90.0   # chest near floor

    def __init__(self, target_reps: int, camera_index: int = 0):
        super().__init__()
        self.target_reps = target_reps
        self.camera_index = camera_index
        self._state = RepState.IDLE
        self._rep_count = 0
        self._running = True

    def run(self):
        if not MP_AVAILABLE:
            self.camera_error.emit("MediaPipe no está instalado.")
            return

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.camera_error.emit(
                f"No se pudo abrir la cámara {self.camera_index}. "
                "Conecta una cámara y reinicia."
            )
            return

        pose = mp.solutions.pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        drawing = mp.solutions.drawing_utils

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                if results.pose_landmarks:
                    drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp.solutions.pose.POSE_CONNECTIONS,
                    )
                    angle = self._get_elbow_angle(results.pose_landmarks.landmark)
                    if angle is not None:
                        new_state, new_count = self._update_state(
                            self._state, angle, self._rep_count
                        )
                        if new_count > self._rep_count:
                            self._rep_count = new_count
                            self.rep_counted.emit(self._rep_count)
                            if self._rep_count >= self.target_reps:
                                self.frame_ready.emit(frame)
                                self.unlock_ready.emit()
                                break
                        self._state = new_state

                self.frame_ready.emit(frame)
        finally:
            cap.release()
            pose.close()

    def _get_elbow_angle(self, landmarks) -> float | None:
        """Average elbow angle from both arms."""
        lm = landmarks
        left = calculate_angle(lm[11], lm[13], lm[15])
        right = calculate_angle(lm[12], lm[14], lm[16])

        if left is not None and right is not None:
            return (left + right) / 2
        return left if left is not None else right

    def _update_state(self, state: RepState, angle: float, count: int):
        if state == RepState.IDLE and angle > self.ANGLE_UP:
            return RepState.UP, count
        if state == RepState.UP and angle < self.ANGLE_DOWN:
            return RepState.DOWN, count
        if state == RepState.DOWN and angle > self.ANGLE_UP:
            return RepState.UP, count + 1
        return state, count

    def stop(self):
        self._running = False
        self.wait()
