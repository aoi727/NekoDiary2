from __future__ import annotations

import sys
from pathlib import Path


def get_resource_root() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_writable_app_root(app_name: str = "NekoDiary") -> Path:
    _ = app_name
    if getattr(sys, "frozen", False):
        writable_root = Path(sys.executable).resolve().parent
        writable_root.mkdir(parents=True, exist_ok=True)
        return writable_root
    return get_resource_root()
