from pathlib import Path


def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
