import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def resolve_database_path(path: Path | str | None = None) -> Path:
    path = Path(path if path is not None else os.getenv("OSHI_DATABASE_PATH", "data/oshi.db"))
    path = path.expanduser()
    return (path if path.is_absolute() else ROOT_DIR / path).resolve()
