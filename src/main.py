from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QFileDialog, QMessageBox

if __package__:
    from .ui_mainwindow import MainWindow
    from .runtime_paths import get_resource_root
    from .settings import AppSettings
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.ui_mainwindow import MainWindow
    from src.runtime_paths import get_resource_root
    from src.settings import AppSettings


def choose_database_path(app: QApplication, saved_path: str = "") -> str | None:
    _ = app
    saved_path = saved_path.strip()
    if saved_path and Path(saved_path).exists():
        return saved_path

    prompt = (
        "前回のDBファイルが見つかりません。\n"
        "既存のDBファイルを選ぶか、新しく作成してください。"
        if saved_path
        else "DBファイルが設定されていません。\n既存のDBファイルを選ぶか、新しく作成してください。"
    )

    while True:
        dialog = QMessageBox()
        dialog.setWindowTitle("DBファイルの選択")
        dialog.setText(prompt)
        open_button = dialog.addButton("既存ファイルを選ぶ", QMessageBox.ButtonRole.AcceptRole)
        create_button = dialog.addButton("新規作成する", QMessageBox.ButtonRole.ActionRole)
        cancel_button = dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(open_button)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == cancel_button:
            return None

        if clicked == open_button:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "DBファイルを選択",
                str(Path(saved_path).parent if saved_path else get_resource_root()),
                "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*)",
            )
            if file_path and Path(file_path).exists():
                return str(Path(file_path).resolve())
            prompt = "DBファイルが選択されなかったか、指定したファイルが見つかりませんでした。もう一度選んでください。"
            continue

        if clicked == create_button:
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "新しいDBファイルを作成",
                str(Path(saved_path).parent / "nekoMemo.db" if saved_path else get_resource_root() / "nekoMemo.db"),
                "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*)",
            )
            if file_path:
                selected = Path(file_path)
                if not selected.suffix:
                    selected = selected.with_suffix(".db")
                return str(selected.resolve())
            prompt = "新しいDBファイルの保存先が選択されませんでした。もう一度選んでください。"


def main() -> int:
    app = QApplication(sys.argv)
    style_path = get_resource_root() / "src" / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    settings = AppSettings()
    db_path = choose_database_path(app, settings.load_database_path())
    if not db_path:
        return 0

    settings.save_database_path(db_path)

    window = MainWindow(db_path, settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
