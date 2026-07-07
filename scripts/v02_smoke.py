from __future__ import annotations

import shutil
from pathlib import Path

from short_drama_controller.v02_cli import init_project, load, save
from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_quality import summary, validate
from short_drama_controller.v02_repair import repair_project


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "tmp_v02_smoke"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    init_project(root / "examples" / "input_script.md", out_dir, "v02_smoke")
    project = load(out_dir)
    before = summary(validate(project))
    if before["qa_status 质检状态"] == "BLOCKER":
        project = repair_project(project)
        save(project, out_dir)

    project = load(out_dir)
    after = summary(validate(project))
    if after["qa_status 质检状态"] == "BLOCKER":
        raise SystemExit(f"v02 smoke failed: {after}")

    export_project(project, out_dir)
    required = [
        out_dir / "project.yaml",
        out_dir / "script.md",
        out_dir / "assets.md",
        out_dir / "storyboard.md",
        out_dir / "producer.md",
        out_dir / "sound.md",
        out_dir / "prompts.md",
        out_dir / "qa.md",
        out_dir / "exports" / "video_prompts.md",
        out_dir / "exports" / "grid_prompts.md",
        out_dir / "exports" / "shot_table.csv",
        out_dir / "exports" / "sound_table.csv",
        out_dir / "exports" / "producer_table.csv",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(f"missing output files: {missing}")

    print("v02 smoke PASS")


if __name__ == "__main__":
    main()
