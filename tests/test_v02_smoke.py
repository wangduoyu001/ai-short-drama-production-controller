from pathlib import Path

from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_full_cli import build_project
from short_drama_controller.v02_qa_gate import evaluate


def test_v02_pipeline_smoke(tmp_path: Path) -> None:
    text = "少年来到镖局。镖头问：“凭什么留下？”少年说：“就凭我还站着。”"
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
