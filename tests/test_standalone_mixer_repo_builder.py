from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _load_builder(root: Path):
    path = root / "scripts" / "build_standalone_mixer_repo.py"
    spec = importlib.util.spec_from_file_location("standalone_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_standalone_repository_without_short_drama_modules(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1]
    target = tmp_path / "ai-local-video-mixer"
    builder = _load_builder(source)

    manifest = builder.build_repository(source, target)

    assert manifest["package"] == "ai_local_video_mixer"
    assert (target / "ai_local_video_mixer" / "cli.py").is_file()
    assert (target / "ai_local_video_mixer" / "edit_package.py").is_file()
    assert (target / "scripts" / "setup_jianying_windows.ps1").is_file()
    assert (target / "docs" / "jianying-edit-workflow.md").is_file()
    assert (target / ".github" / "workflows" / "ci.yml").is_file()
    assert not (target / "short_drama_controller").exists()
    assert not (target / "tests" / "test_v02_full_cli.py").exists()

    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "ai-local-video-mixer"' in pyproject
    assert 'ai-local-video-mixer = "ai_local_video_mixer.cli:main"' in pyproject
    assert "short_drama_controller" not in pyproject

    for path in [
        target / "tests" / "test_script_mixer.py",
        target / "scripts" / "script_mixer_acceptance.py",
    ]:
        text = path.read_text(encoding="utf-8")
        assert "short_drama_controller.script_mixer" not in text
        assert "ai_local_video_mixer" in text

    result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "ai_local_video_mixer"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_builder_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1]
    target = tmp_path / "existing"
    target.mkdir()
    builder = _load_builder(source)

    try:
        builder.build_repository(source, target)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Builder should refuse to overwrite an existing target")
