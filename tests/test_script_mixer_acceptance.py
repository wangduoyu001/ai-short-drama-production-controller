from __future__ import annotations

import runpy
from pathlib import Path


def test_acceptance_script_imports_without_running() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "script_mixer_acceptance.py"
    namespace = runpy.run_path(str(script), run_name="script_mixer_acceptance_test")
    assert callable(namespace["main"])
    assert callable(namespace["_parser"])
