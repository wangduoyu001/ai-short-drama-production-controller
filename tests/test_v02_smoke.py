from pathlib import Path

from short_drama_controller.v02_assets import extract_assets
from short_drama_controller.v02_dialogue import extract_dialogue
from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_models import Project
from short_drama_controller.v02_prompts import attach_sound_and_prompts
from short_drama_controller.v02_qa import summary, validate
from short_drama_controller.v02_repair import repair_project
from short_drama_controller.v02_storyboard import build_shots


def test_v02_pipeline_smoke(tmp_path: Path) -> None:
    text = "少年来到镖局。镖头问：“凭什么留下？”少年说：“就凭我还站着。”"
    project = Project({
        "project_name 项目名": "smoke",
        "source_text 原文": text,
        "dialogue_lines 对白列表": extract_dialogue(text),
        **extract_assets(text),
    })
    build_shots(project)
    attach_sound_and_prompts(project)
    project = repair_project(project)
    qa = summary(validate(project))
    assert qa["qa_status 质检状态"] in {"PASS", "WARN"}
    assert project.shots
    assert "ambience_sfx 环境底音" in project.shots[0]
    assert "video_prompt 视频提示词" in project.shots[0]
    export_project(project, tmp_path)
    assert (tmp_path / "exports" / "v02_video_prompts.md").exists()
    assert (tmp_path / "exports" / "v02_sound_table.csv").exists()
