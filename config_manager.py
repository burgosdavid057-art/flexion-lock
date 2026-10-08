import json
import os
from datetime import date

PRESETS = {
    "suave":    {"session_limit_min": 60, "daily_limit_min": 180, "reps_base": 5,  "reps_increment": 3},
    "moderado": {"session_limit_min": 45, "daily_limit_min": 120, "reps_base": 8,  "reps_increment": 5},
    "duro":     {"session_limit_min": 30, "daily_limit_min": 90,  "reps_base": 12, "reps_increment": 7},
}

DEFAULT_CONFIG = {
    "preset": "moderado",
    "session_limit_min": 45,
    "daily_limit_min": 120,
    "reps_base": 8,
    "reps_increment": 5,
    "camera_index": 0,
    "autostart": False,
}

DEFAULT_STATS = {
    "active_seconds": 0,
    "lock_count": 0,
    "pushups_total": 0,
    "daily_limit_triggered": False,
}


class ConfigManager:
    def __init__(self, config_path: str = None, stats_path: str = None):
        base = os.path.join(os.path.dirname(__file__), "data")
        self._config_path = config_path or os.path.join(base, "config.json")
        self._stats_path = stats_path or os.path.join(base, "stats.json")

    # --- Config ---

    def get_config(self) -> dict:
        if not os.path.exists(self._config_path):
            self.save_config(DEFAULT_CONFIG.copy())
        try:
            with open(self._config_path, "r") as f:
                loaded = json.load(f)
            # Merge with defaults to ensure all keys are present
            config = DEFAULT_CONFIG.copy()
            config.update(loaded)
            return config
        except json.JSONDecodeError:
            # Corrupted JSON — fall back to defaults
            self.save_config(DEFAULT_CONFIG.copy())
            return DEFAULT_CONFIG.copy()

    def save_config(self, config: dict) -> None:
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(config, f, indent=2)

    def apply_preset(self, preset_name: str) -> None:
        """Apply a named preset, preserving camera_index and autostart."""
        config = self.get_config()
        if preset_name in PRESETS:
            config.update(PRESETS[preset_name])
            config["preset"] = preset_name
        else:
            config["preset"] = "personalizado"
        self.save_config(config)

    # --- Stats ---

    def get_stats(self) -> dict:
        today = date.today().isoformat()
        if os.path.exists(self._stats_path):
            try:
                with open(self._stats_path, "r") as f:
                    stats = json.load(f)
                if stats.get("date") == today:
                    # Merge with defaults to ensure all keys are present
                    merged = DEFAULT_STATS.copy()
                    merged.update(stats)
                    merged["date"] = today
                    return merged
            except json.JSONDecodeError:
                # Corrupted JSON — fall back to fresh defaults
                pass
        # New day or missing file or corrupted JSON — reset
        fresh = DEFAULT_STATS.copy()
        fresh["date"] = today
        self._save_stats(fresh)
        return fresh

    def _save_stats(self, stats: dict) -> None:
        os.makedirs(os.path.dirname(self._stats_path), exist_ok=True)
        with open(self._stats_path, "w") as f:
            json.dump(stats, f, indent=2)

    def increment_lock_count(self) -> None:
        stats = self.get_stats()
        stats["lock_count"] += 1
        self._save_stats(stats)

    def add_pushups(self, count: int) -> None:
        stats = self.get_stats()
        stats["pushups_total"] += count
        self._save_stats(stats)

    def set_daily_limit_triggered(self, value: bool) -> None:
        stats = self.get_stats()
        stats["daily_limit_triggered"] = value
        self._save_stats(stats)

    def add_active_seconds(self, seconds: int) -> None:
        stats = self.get_stats()
        stats["active_seconds"] += seconds
        self._save_stats(stats)
