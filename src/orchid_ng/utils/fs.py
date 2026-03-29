from pathlib import Path


def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def ensure_file(path: Path):
    ensure_dir(path.parent)
    if not path.exists():
        path.touch()
