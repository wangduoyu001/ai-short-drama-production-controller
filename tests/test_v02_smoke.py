from pathlib import Path

from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_full_cli import build_project
from short_drama_controller.v02_qa_gate import evaluate


def test_v02_pipeline_smoke(tmp_path: Path) -> None:
    text = "夜里，少年在破庙门口握着木剑。老人递出一盏灯笼，说：“你终于来了。”少年转身，门外黑影停住。"
    project = build_project(text, "smoke")

    qa = evaluate(project)
    assert qa["qa_status 质检状态"] in {"PASS", "WARN"}
    assert project.shots
    assert "ambience_sfx 环境底音" in project.shots[0]
    assert "video_prompt 视频提示词" in project.shots[0]

    export_project(project, tmp_path)

    assert (tmp_path / "exports" / "video_prompts.md").exists()
    assert (tmp_path / "exports" / "sound_table.csv").exists()
    assert not (tmp_path / "exports" / "v02_video_prompts.md").exists()
