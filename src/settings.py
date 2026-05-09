from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings

from .runtime_paths import get_writable_app_root


class AppSettings:
    def __init__(self):
        config_path = get_writable_app_root()
        config_path.mkdir(parents=True, exist_ok=True)
        self.settings_file_path = config_path / "settings.ini"
        self.settings = QSettings(str(self.settings_file_path), QSettings.Format.IniFormat)

    def save_geometry(self, key: str, geometry: QByteArray) -> None:
        self.settings.setValue(f"{key}/geometry", geometry)

    def load_geometry(self, key: str) -> QByteArray:
        return self.settings.value(f"{key}/geometry", QByteArray())

    def save_state(self, key: str, state: QByteArray) -> None:
        self.settings.setValue(f"{key}/state", state)

    def load_state(self, key: str) -> QByteArray:
        return self.settings.value(f"{key}/state", QByteArray())

    def save_database_path(self, path: str) -> None:
        self.settings.setValue("database/path", path)

    def load_database_path(self) -> str:
        value = self.settings.value("database/path", "")
        return value if isinstance(value, str) else ""
