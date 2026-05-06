from dataclasses import dataclass


@dataclass
class Memo:
    id: int
    date: str
    category: str
    title: str
    content: str


@dataclass
class Category:
    id: int
    name: str


@dataclass
class AppConfig:
    app_title: str = "My Diary"
    font_size_mode: str = "中"
    body_text_scale: float = 1.0
    home_background_path: str = ""
    home_background_opacity: int = 30
    editor_background_path: str = ""
    editor_background_opacity: int = 30
