from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_path = root / "skills" / "ai_short_drama_production_controller" / "SKILL.md"
    required = [
        root / "README.md",
        root / "CODEX_INSTALL.md",
        skill_path,
        root / "short_drama_controller" / "v02_full_cli.py",
        root / "short_drama_controller" / "v02_quality.py",
        root / "examples" / "input_script.md",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        print("codex_install_status 安装状态: FAIL")
        print("missing_files 缺失文件:")
        for item in missing:
            print("- " + item)
        raise SystemExit(1)

    print("codex_install_status 安装状态: PASS")
    print("skill_entry Skill入口: " + str(skill_path.relative_to(root)))
    print("recommended_command 推荐命令:")
    print("python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo")
    print("python -m short_drama_controller.v02_full_cli qa --project demo_v02")
    print("python -m short_drama_controller.v02_full_cli repair --project demo_v02")
    print("python -m short_drama_controller.v02_full_cli export --project demo_v02")


if __name__ == "__main__":
    sys.exit(main())
