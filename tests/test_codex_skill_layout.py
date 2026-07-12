from __future__ import annotations

from pathlib import Path

from short_drama_controller.v02_full_cli import build_parser, cmd_doctor

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
