from __future__ import annotations

import argparse
import sys
from importlib.util import find_spec
from pathlib import Path

from .v02_action_contract import ensure_action_contract
from .v02_asset_expand import expand_project_assets
from .v02_assets import extract_assets
from .v02_batch_inference import attach_batch_inference
from .v02_constants import DOCUMENT_VERSION, SKILL_VERSION
from .v02_coverage_qa import attach_coverage_qa
from .v02_dialogue_bind import bind_dialogue_to_characters
from .v02_director_docs import write_director_docs
from .v02_exporters import export_project
from .v02_grid_strategy import attach_grid_strategy
from .v02_io import read_project, write_project, write_text
from .v02_models import Project
from .v02_preproduction import build_action_choreography, build_preproduction
from .v02_prompts import attach_sound_and_prompts
from .v02_qa_gate import evaluate, render_qa
from .v02_repair import repair_project
from .v02_shot_bindings import attach_required_shot_bindings
from .v02_shot_inference import attach_shot_inference
from .v02_source_segments import attach_source_coverage, build_source_segments
from .v02_storyboard import build_shots
from .v02_cli import render_assets, render_producer, render_prompts, render_script, render_sound, render_storyboard

CODEX_SKILL_PATH = Path(".agents/skills/ai-short-drama-controller/SKILL.md")


def build_project(text: str, title: str | None) -> Project:
    assets = extract_assets(text)
    dialogues = bind_dialogue_to_characters(text, assets["characters 角色列表"])
    project = Project({
        "project_name 项目名": title or "untitled_short_drama 未命名短剧",
        "skill_version 技能版本": SKILL_VERSION,
        "document_version 文档版本": DOCUMENT_VERSION,
        "source_text 原文": text,
        "scope_gate 范围闸门": {
            "production_mode 制作模式": "director_package 导演物料包模式",
            "preproduction_required 前期拆解必需": "chapter_intake / story_events / characters / scenes / props / world_bible / style_bible / asset_lock",
            "generation_clip_duration 生成片段时长": "4-15秒",
            "shot_count_rule 镜头数量规则": "由 event_blocks 和 clip_type 决定，不固定8-12镜",
        },
        "dialogue_lines 对白列表": dialogues,
        **assets,
    })
    build_source_segments(project)
    expand_project_assets(project)
    build_preproduction(project)
    build_shots(project)
    attach_required_shot_bindings(project)
    attach_sound_and_prompts(project)
    attach_grid_strategy(project)
    attach_shot_inference(project)
    attach_batch_inference(project)
    build_action_choreography(project)
    ensure_action_contract(project)
    attach_source_coverage(project)
    attach_coverage_qa(project)
    return project


def save_project(project: Project, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_project(out_dir / "project.yaml", project.data)
    write_text(out_dir / "script.md", render_script(project))
    write_text(out_dir / "assets.md", render_assets(project))
    write_text(out_dir / "storyboard.md", render_storyboard(project))
    write_text(out_dir / "producer.md", render_producer(project))
    write_text(out_dir / "sound.md", render_sound(project))
    write_text(out_dir / "prompts.md", render_prompts(project))
    write_director_docs(project, out_dir)
    write_text(out_dir / "qa.md", render_qa(evaluate(project)))


def load_project(project_dir: Path) -> Project:
    return Project(read_project(project_dir / "project.yaml"))


def cmd_init(args: argparse.Namespace) -> None:
    text = Path(args.input).read_text(encoding="utf-8").strip()
    save_project(build_project(text, args.title), Path(args.out))
    print(f"v02_project 已创建: {args.out}")


def cmd_qa(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    qa = evaluate(load_project(project_dir))
    write_text(project_dir / "qa.md", render_qa(qa))
    print(qa)


def cmd_repair(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = repair_project(load_project(project_dir), target_shot_id=args.shot)
    expand_project_assets(project)
    build_preproduction(project)
    attach_required_shot_bindings(project)
    attach_grid_strategy(project)
    attach_shot_inference(project)
    attach_batch_inference(project)
    build_action_choreography(project)
    ensure_action_contract(project)
    attach_source_coverage(project)
    attach_coverage_qa(project)
    save_project(project, project_dir)
    suffix = f" shot={args.shot}" if args.shot else ""
    print(f"v02_repair 返修替换完成: {project_dir}{suffix}")


def cmd_export(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    export_project(load_project(project_dir), project_dir)
    print(f"v02_export 导出完成: {project_dir / 'exports'}")


def cmd_grid(args: argparse.Namespace) -> None:
    shot = next((x for x in load_project(Path(args.project)).shots if x["shot_id 镜头编号"] == args.shot), None)
    if not shot:
        raise SystemExit(f"shot not found: {args.shot}")
    print(shot.get("grid_prompt 宫格提示词") or "该镜头未判定为宫格硬切高风险镜头。")


def cmd_prompt(args: argparse.Namespace) -> None:
    project = build_project(args.text.strip(), args.title or "single_prompt 单提示词")
    shot = next((x for x in project.shots if x["shot_id 镜头编号"] == args.shot), project.shots[0])
    print(render_single_prompt(shot))


def _candidate_repo_roots() -> list[Path]:
    starts = [Path.cwd(), Path(__file__).resolve().parent]
    roots: list[Path] = []
    for start in starts:
        for candidate in (start, *start.parents):
            if candidate not in roots:
                roots.append(candidate)
    return roots


def find_repo_root() -> Path:
    for candidate in _candidate_repo_roots():
        if (candidate / "pyproject.toml").is_file() and (candidate / "short_drama_controller").is_dir():
            return candidate
    return Path.cwd()


def _check_skill_frontmatter(skill_path: Path) -> tuple[bool, str]:
    if not skill_path.is_file():
        return False, str(skill_path)
    text = skill_path.read_text(encoding="utf-8")
    required = [
        text.startswith("---\n"),
        "name: ai-short-drama-controller" in text,
        "description:" in text,
    ]
    return all(required), str(skill_path)


def cmd_doctor(_args: argparse.Namespace) -> None:
    root = find_repo_root()
    skill_path = root / CODEX_SKILL_PATH
    skill_ok, skill_detail = _check_skill_frontmatter(skill_path)
    checks = [
        ("python_version Python版本", sys.version_info >= (3, 10), sys.version.split()[0]),
        ("entrypoint_module 主入口模块", find_spec("short_drama_controller.v02_full_cli") is not None, "short_drama_controller.v02_full_cli"),
        ("agents_md 项目规则", (root / "AGENTS.md").is_file(), str(root / "AGENTS.md")),
        ("codex_skill Codex技能", skill_ok, skill_detail),
        ("openai_yaml Skill界面元数据", (skill_path.parent / "agents/openai.yaml").is_file(), str(skill_path.parent / "agents/openai.yaml")),
    ]
    failed = []
    print(f"repository_root 仓库根目录: {root}")
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not ok:
            failed.append(name)
    if failed:
        raise SystemExit(f"doctor 检查失败: {', '.join(failed)}")
    print("doctor 检查通过：Codex Skill、项目规则和CLI入口均可用。")


def render_single_prompt(shot: dict) -> str:
    return "\n".join([
        f"shot_id 镜头编号：{shot.get('shot_id 镜头编号', '')}",
        f"clip_id 片段编号：{shot.get('clip_id 单段编号', '')}",
        f"clip_type 片段类型：{shot.get('clip_type 片段类型', '')}",
        f"clip_duration_seconds 片段时长秒数：{shot.get('clip_duration_seconds 片段时长秒数', '')}",
        f"event_id 事件编号：{shot.get('event_id 事件编号', '')}",
        f"beat_id 节拍编号：{shot.get('beat_id 节拍编号', '')}",
        f"scene_id 场景编号：{shot.get('scene_id 场景编号', '')}",
        f"character_id 角色编号：{shot.get('character_id 角色编号', '')}",
        f"prop_id 道具编号：{shot.get('prop_id 道具编号', '')}",
        f"source_quote 原文节拍证据：{shot.get('source_quote 原文节拍证据', '')}",
        "\nfirst_frame_prompt 首帧提示词：",
        shot.get("first_frame_prompt 首帧提示词", ""),
        "\nimage_prompt 图片提示词：",
        shot.get("image_prompt 图片提示词", ""),
        "\nvideo_prompt 视频提示词：",
        shot.get("video_prompt 视频提示词", ""),
        "\nend_frame_prompt 尾帧提示词：",
        shot.get("end_frame_prompt 尾帧提示词", ""),
        "\nsound_prompt 声音提示词：",
        f"发声模式：{shot.get('speaker_mode 发声模式', '')}；嘴型状态：{shot.get('mouth_state 嘴型状态', '')}；环境底音：{shot.get('ambience_sfx 环境底音', '')}；拟音：{shot.get('foley_sfx 拟音', '')}；音乐：{shot.get('music_note 音乐建议', '')}",
        "\nnegative_prompt 负面提示词：",
        shot.get("negative_prompt 负面提示词", "禁止换脸，禁止换服装，禁止跳轴，禁止复杂运镜，禁止道具消失，禁止字幕水印，禁止提前演完后续剧情"),
        "\nfallback_prompt 备用提示词：",
        shot.get("fallback_shot 备用镜头", ""),
    ])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="short-drama-controller-v02")
    sub = parser.add_subparsers(required=True)
    for name, func in [("qa", cmd_qa), ("export", cmd_export)]:
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.set_defaults(func=func)
    p = sub.add_parser("repair")
    p.add_argument("--project", required=True)
    p.add_argument("--shot", help="targeted repair / 定向返修，例如 SH003")
    p.set_defaults(func=cmd_repair)
    p = sub.add_parser("init")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("grid")
    p.add_argument("--project", required=True)
    p.add_argument("--shot", required=True)
    p.set_defaults(func=cmd_grid)
    p = sub.add_parser("prompt")
    p.add_argument("--text", required=True)
    p.add_argument("--shot", default="SH001")
    p.add_argument("--title")
    p.set_defaults(func=cmd_prompt)
    p = sub.add_parser("doctor")
    p.set_defaults(func=cmd_doctor)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
