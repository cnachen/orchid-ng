from orchid_ng.utils.singleton import SingletonMeta
from datetime import datetime
from pathlib import Path
from orchid_ng.utils.fs import ensure_dir


class ConfigService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.runs_dir: Path = Path(".runs")
        self.iterations: int = 100
        self.action_limits: int = 4

        now = datetime.now().strftime("%Y%m%dT%H%M%S")

        # Should be readonly
        self.current_run_dir: Path = self.runs_dir / f"{now}"

        ensure_dir(self.current_run_dir)
