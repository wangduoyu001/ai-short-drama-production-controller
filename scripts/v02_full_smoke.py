from pathlib import Path
from short_drama_controller.v02_full_cli import build_project, save_project

root = Path(__file__).resolve().parents[1]
text = (root / "examples" / "input_script.md").read_text(encoding="utf-8")
save_project(build_project(text, "v02_full_smoke"), root / "tmp_v02_full_smoke")
print("v02 full smoke PASS")
