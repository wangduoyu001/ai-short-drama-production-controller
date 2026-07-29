from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from short_drama_controller.director_system import build_default_director_graph
from short_drama_controller.v06_unified_workflow import run_unified_workflow


def run_smoke(out_dir: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = run_unified_workflow(
        root / "examples" / "input_script.md",
        out_dir,
        title="director-system-smoke",
        resume=False,
    )
    required = (
        "workflow.json",
        "production_tasks.json",
        "assembly_plan.json",
        "project.yaml",
        "qa.md",
        "exports/video_prompts.md",
    )
    missing = [name for name in required if not (out_dir / name).is_file()]
    if missing:
        raise SystemExit(f"missing output files: {missing}")
    graph = build_default_director_graph()
    if graph.topological_order()[0] != "source":
        raise SystemExit("director graph ordering failed")
    if result.task_count <= 0:
        raise SystemExit("production task graph is empty")
    print("smoke PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="optional output directory")
    args = parser.parse_args()
    if args.out:
        run_smoke(Path(args.out))
        return
    with tempfile.TemporaryDirectory(prefix="director_smoke_") as temporary:
        run_smoke(Path(temporary))


if __name__ == "__main__":
    main()
