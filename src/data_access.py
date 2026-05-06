from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .models import AppConfig, Category, Memo
from .runtime_paths import get_resource_root


LEGACY_CATEGORY_NAME_MAP = {
    "譌･蟶ｸ": "日常",
    "莉穂ｺ・": "仕事",
    "螟ｩ豌・": "天気",
    "隱ｭ譖ｸ": "読書",
    "譌・｡・": "旅行",
    "髮題ｨ・": "雑記",
}

LEGACY_FONT_SIZE_MODE_MAP = {
    "蟆・": "小",
    "荳ｭ": "中",
    "螟ｧ": "大",
    "迚ｹ螟ｧ": "特大",
    "小さめ": "小",
    "標準": "中",
    "大きめ": "大",
}


class DataAccess:
    def __init__(self, db_path: str):
        self.resource_root = get_resource_root()
        self.project_root = self.resource_root

        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.writable_root = self.db_path.parent
        self.images_dir = self.db_path.parent / "img"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.connection: sqlite3.Connection | None = None
        self._connect()
        self._initialize_database()

    def _connect(self) -> None:
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        if self.connection is None:
            return
        self.connection.commit()
        self.connection.close()
        self.connection = None

    def reopen(self) -> None:
        self.close()
        self._connect()

    def _initialize_database(self) -> None:
        cursor = self.connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS Category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS Memo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS AppConfig (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        if cursor.execute("SELECT COUNT(*) FROM Category").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Category (name) VALUES (?)",
                [
                    ("日常",),
                    ("仕事",),
                    ("天気",),
                    ("読書",),
                    ("旅行",),
                    ("雑記",),
                ],
            )

        if cursor.execute("SELECT COUNT(*) FROM Memo").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Memo (date, category, title, content) VALUES (?, ?, ?, ?)",
                [
                    (
                        "2026-05-04",
                        "天気; 日常",
                        "天気 晴れ",
                        "<p>本日晴天なれど朝から風強し。</p>"
                        "<p><span style=\"font-size:16pt; font-weight:700; color:#1d4ed8;\">"
                        "大型連休後半、朝は東海道線が止まっていた"
                        "</span></p>",
                    ),
                    (
                        "2026-05-02",
                        "読書; 雑記",
                        "連休の読書記録",
                        "<p>図書館で借りた本を読み進めた。</p>"
                        "<p>主人公の視点が静かで、夜に読むのにちょうどよかった。</p>",
                    ),
                ],
            )

        defaults = {
            "app_title": "My Diary",
            "font_size_mode": "中",
            "body_text_scale": "1.0",
            "home_background_path": "",
            "home_background_opacity": "30",
            "editor_background_path": "",
            "editor_background_opacity": "30",
        }
        for key, value in defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO AppConfig (key, value) VALUES (?, ?)",
                (key, value),
            )

        self._repair_legacy_text_data(cursor)
        self.connection.commit()

    def get_app_config(self) -> AppConfig:
        cursor = self.connection.cursor()
        rows = cursor.execute("SELECT key, value FROM AppConfig").fetchall()
        values = {row["key"]: row["value"] for row in rows}
        return AppConfig(
            app_title=values.get("app_title", "My Diary"),
            font_size_mode=self._normalize_font_size_mode(values.get("font_size_mode", "中")),
            body_text_scale=self._to_float(values.get("body_text_scale", "1.0"), 1.0, minimum=0.9, maximum=3.0),
            home_background_path=values.get("home_background_path", ""),
            home_background_opacity=self._to_int(values.get("home_background_opacity", "30"), 30),
            editor_background_path=values.get("editor_background_path", ""),
            editor_background_opacity=self._to_int(values.get("editor_background_opacity", "30"), 30),
        )

    def save_app_config(self, config: AppConfig) -> None:
        cursor = self.connection.cursor()
        pairs = {
            "app_title": config.app_title,
            "font_size_mode": config.font_size_mode,
            "body_text_scale": str(config.body_text_scale),
            "home_background_path": config.home_background_path,
            "home_background_opacity": str(config.home_background_opacity),
            "editor_background_path": config.editor_background_path,
            "editor_background_opacity": str(config.editor_background_opacity),
        }
        for key, value in pairs.items():
            cursor.execute(
                """
                INSERT INTO AppConfig (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        self.connection.commit()

    def get_categories(self) -> list[Category]:
        cursor = self.connection.cursor()
        rows = cursor.execute("SELECT id, name FROM Category ORDER BY name COLLATE NOCASE").fetchall()
        return [Category(id=row["id"], name=row["name"]) for row in rows]

    def get_category_names(self) -> list[str]:
        return [category.name for category in self.get_categories()]

    def get_memos(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        category: str | None = None,
        keyword: str | None = None,
    ) -> list[Memo]:
        sql = "SELECT id, date, category, title, content FROM Memo"
        conditions: list[str] = []
        params: list[str] = []

        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        if category:
            conditions.append("(category = ? OR category LIKE ? OR category LIKE ? OR category LIKE ?)")
            params.extend([category, f"{category};%", f"%; {category};%", f"%; {category}"])
        if keyword:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            wildcard = f"%{keyword}%"
            params.extend([wildcard, wildcard])

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY date DESC, id DESC"

        cursor = self.connection.cursor()
        rows = cursor.execute(sql, params).fetchall()
        return [
            Memo(
                id=row["id"],
                date=row["date"],
                category=row["category"],
                title=row["title"],
                content=row["content"],
            )
            for row in rows
        ]

    def get_memo_by_id(self, memo_id: int) -> Memo | None:
        cursor = self.connection.cursor()
        row = cursor.execute(
            "SELECT id, date, category, title, content FROM Memo WHERE id = ?",
            (memo_id,),
        ).fetchone()
        if row is None:
            return None
        return Memo(
            id=row["id"],
            date=row["date"],
            category=row["category"],
            title=row["title"],
            content=row["content"],
        )

    def add_memo(self, memo: Memo) -> int:
        self._ensure_categories(memo.category)
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO Memo (date, category, title, content) VALUES (?, ?, ?, ?)",
            (memo.date, self.normalize_tags(memo.category), memo.title, memo.content),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def update_memo(self, memo: Memo) -> None:
        self._ensure_categories(memo.category)
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE Memo SET date = ?, category = ?, title = ?, content = ? WHERE id = ?",
            (memo.date, self.normalize_tags(memo.category), memo.title, memo.content, memo.id),
        )
        self.connection.commit()

    def delete_memo(self, memo_id: int) -> None:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM Memo WHERE id = ?", (memo_id,))
        self.connection.commit()

    def _ensure_categories(self, categories_text: str) -> None:
        cursor = self.connection.cursor()
        for category in self.parse_tags(categories_text):
            cursor.execute("INSERT OR IGNORE INTO Category (name) VALUES (?)", (category,))
        self.connection.commit()

    def _repair_legacy_text_data(self, cursor: sqlite3.Cursor) -> None:
        self._repair_font_size_mode(cursor)
        self._repair_category_names(cursor)

    def _repair_font_size_mode(self, cursor: sqlite3.Cursor) -> None:
        row = cursor.execute(
            "SELECT value FROM AppConfig WHERE key = ?",
            ("font_size_mode",),
        ).fetchone()
        if row is None:
            return

        normalized = self._normalize_font_size_mode(row["value"])
        if normalized != row["value"]:
            cursor.execute(
                "UPDATE AppConfig SET value = ? WHERE key = ?",
                (normalized, "font_size_mode"),
            )

    def _repair_category_names(self, cursor: sqlite3.Cursor) -> None:
        memo_rows = cursor.execute("SELECT id, category FROM Memo").fetchall()
        for row in memo_rows:
            normalized = self.normalize_tags_with_legacy_support(row["category"])
            if normalized != row["category"]:
                cursor.execute(
                    "UPDATE Memo SET category = ? WHERE id = ?",
                    (normalized, row["id"]),
                )

        existing_names = [
            self.normalize_category_name(row["name"])
            for row in cursor.execute("SELECT name FROM Category").fetchall()
        ]
        normalized_names = sorted({name for name in existing_names if name}, key=str.casefold)
        if not normalized_names:
            normalized_names = ["日常", "仕事", "天気", "読書", "旅行", "雑記"]

        cursor.execute("DELETE FROM Category")
        cursor.executemany(
            "INSERT INTO Category (name) VALUES (?)",
            [(name,) for name in normalized_names],
        )

    @staticmethod
    def parse_tags(categories_text: str) -> list[str]:
        normalized = categories_text.replace("\u3000", " ")
        return sorted(
            {
                part.strip().lstrip("#").strip()
                for part in re.split(r"[;\s]+", normalized)
                if part.strip().lstrip("#").strip()
            },
            key=str.casefold,
        )

    @classmethod
    def normalize_tags_with_legacy_support(cls, categories_text: str) -> str:
        repaired_tags = [cls.normalize_category_name(tag) for tag in cls.parse_tags(categories_text)]
        return "; ".join(sorted({tag for tag in repaired_tags if tag}, key=str.casefold))

    @staticmethod
    def normalize_category_name(category_name: str) -> str:
        return LEGACY_CATEGORY_NAME_MAP.get(category_name, category_name)

    @classmethod
    def normalize_tags(cls, categories_text: str) -> str:
        return cls.normalize_tags_with_legacy_support(categories_text)

    @staticmethod
    def _to_int(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(value: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        if minimum is not None:
            parsed = max(minimum, parsed)
        if maximum is not None:
            parsed = min(maximum, parsed)
        return parsed

    @staticmethod
    def _normalize_font_size_mode(value: str) -> str:
        normalized = LEGACY_FONT_SIZE_MODE_MAP.get(value, value)
        return normalized if normalized in {"小", "中", "大", "特大"} else "中"
