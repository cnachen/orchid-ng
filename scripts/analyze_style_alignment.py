from __future__ import annotations

import argparse
import json
from pathlib import Path

from orchid_ng.config import Settings
from orchid_ng.services.alignment import build_alignment_report
from orchid_ng.storage import RunStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze how closely a run aligns with the fixed Orchid style contract."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings(project_root=args.project_root)
    run_store = RunStore(settings.runs_dir)
    run_session = run_store.open_run(args.run_id)
    ideas = run_session.load_latest_ideas()
    report = build_alignment_report(run_id=args.run_id, ideas=ideas)
    output_path = settings.runs_dir / args.run_id / "reports" / "style_alignment.json"
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
