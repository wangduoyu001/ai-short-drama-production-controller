from __future__ import annotations

from pathlib import Path

from short_drama_controller.v02_action_contract import ensure_action_contract
from short_drama_controller.v02_full_cli import build_parser, cmd_doctor
from short_drama_controller.v02_models import Project

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents/skills/ai-short-drama-controller"
SKILL_FILE = SKILL_DIR / "SKILL.md"


def test_codex_skill_has_required_frontmatter() -> None:
    text = SKILL_FILE.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: ai-short-drama-controller" in text
    assert "description:" in text


def test_codex_skill_references_exist() -> None:
    for name in ["asset-contract.md", "storyboard-contract.md", "action-contract.md"]:
        assert (SKILL_DIR / "references" / name).is_file()


def test_codex_skill_metadata_disables_implicit_invocation() -> None:
    text = (SKILL_DIR / "agents/openai.yaml").read_text(encoding="utf-8")
    assert "display_name:" in text
    assert "allow_implicit_invocation: false" in text


def test_repository_agents_file_exists() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "episode 单集" in text
    assert "generation_clip 生成片段" in text
    assert "BLOCKER" in text


def test_doctor_subcommand_is_registered() -> None:
    args = build_parser().parse_args(["doctor"])
    assert args.func is cmd_doctor


def test_action_contract_builds_grid_fallback() -> None:
    project = Project({
        "shots 分镜列表": [{
            "shot_id 镜头编号": "SH030",
            "action_detail 动作细节": "角色向前一步推开木门",
            "screen_direction 画面方向": "由左向右",
        }],
        "action_choreography 动作编排表": [{
            "action_id 动作编号": "ACT_030",
            "related_shot_id 对应镜头编号": "SH030",
            "start_state 起始姿态": "站在门外，右手贴近门板",
            "end_state 结束姿态": "木门打开，角色停在门槛前",
            "attack_line 攻击线": "沿门板法线向前",
            "movement_line 移动线": "向前半步",
            "contact_point 接触点": "右掌与门板",
            "speed 速度": "controlled 克制",
            "result 结果": "木门打开",
            "risk_level 风险等级": "low 低",
            "backup_shot 备用镜头": "手掌特写接门开结果全景",
            "grid_cut_prompt 宫格硬切提示词": "",
        }],
    })

    ensure_action_contract(project)

    prompt = project.data["action_choreography 动作编排表"][0]["grid_cut_prompt 宫格硬切提示词"]
    assert "四格硬切动作方案" in prompt
    assert "角色向前一步推开木门" in prompt
    assert "禁止跳轴" in prompt
