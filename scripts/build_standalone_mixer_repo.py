from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


MODULE_FILES = [
    "__init__.py",
    "audio.py",
    "catalog.py",
    "cli.py",
    "config.py",
    "edit_package.py",
    "embeddings.py",
    "enrichment.py",
    "environment.py",
    "integration.py",
    "intent.py",
    "jianying_draft.py",
    "media_probe.py",
    "models.py",
    "ollama_adapter.py",
    "pipeline.py",
    "planner.py",
    "render.py",
    "replan.py",
    "reporting.py",
    "retrieval.py",
    "review.py",
    "scanner.py",
    "scene_detection.py",
    "script_parser.py",
    "subtitles.py",
    "thumbnails.py",
    "transcription.py",
]

TEST_FILES = [
    "test_script_mixer.py",
    "test_script_mixer_acceptance.py",
    "test_script_mixer_audio.py",
    "test_script_mixer_edit_package.py",
    "test_script_mixer_embeddings.py",
    "test_script_mixer_integration.py",
    "test_script_mixer_jianying_cli.py",
    "test_script_mixer_jianying_draft.py",
    "test_script_mixer_ollama.py",
    "test_script_mixer_replan.py",
    "test_script_mixer_review.py",
    "test_script_mixer_review_cli.py",
    "test_script_mixer_scanner.py",
    "test_script_mixer_transcription.py",
]

DOC_FILES = [
    "jianying-edit-workflow.md",
    "script-driven-mixer.md",
    "script-mixer-integration-check.md",
    "script-mixer-next-development-plan.md",
    "script-mixer-review.md",
]

CONFIG_FILES = [
    "script_mixer.example.json",
    "script_mixer.integration-checklist.example.json",
]

SCRIPT_FILES = [
    "run_jianying_project.ps1",
    "script_mixer_acceptance.py",
    "setup_jianying_windows.ps1",
]

TEXT_REPLACEMENTS = {
    "short_drama_controller.script_mixer": "ai_local_video_mixer",
    "short_drama_controller/script_mixer": "ai_local_video_mixer",
    "ai-short-drama-production-controller": "ai-local-video-mixer",
    "AI Short Drama Production Controller": "AI Local Video Mixer",
    "AI短剧生产控制器": "AI本地视频混剪器",
}


def _copy_file(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Required source file is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _rewrite_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in TEXT_REPLACEMENTS.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _standalone_pyproject() -> str:
    return """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-local-video-mixer"
version = "0.1.0"
description = "Local script-driven video mixer with editable Jianying delivery"
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
jianying = ["pyJianYingDraft>=0.3,<0.4"]
dev = ["pytest>=8"]

[project.scripts]
ai-local-video-mixer = "ai_local_video_mixer.cli:main"
script-driven-mixer = "ai_local_video_mixer.cli:main"

[tool.setuptools.packages.find]
include = ["ai_local_video_mixer*"]
"""


def _standalone_readme() -> str:
    return """# AI Local Video Mixer / AI本地视频混剪器

独立的本地文案驱动混剪项目，不包含AI短剧导演、资产或分镜生产模块。

输入：

```text
本地视频素材目录
文案txt
可选真实配音
```

输出：

```text
自动粗剪预览final.mp4
固定帧率独立镜头
独立原声和配音
SRT/ASS字幕
每个镜头的备用候选
剪映可编辑素材包
可选剪映草稿
```

## Windows安装

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_jianying_windows.ps1 -InstallMissingTools
```

## 一键生成剪映项目

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 `
  -MediaRoot "D:\\视频素材" `
  -Script "input.txt" `
  -Voice "voice.wav" `
  -DraftRoot "D:\\JianyingPro Drafts"
```

没有配音时删除`-Voice`参数。

## 直接CLI

```bash
ai-local-video-mixer init-config --out script_mixer.local.json
ai-local-video-mixer --config script_mixer.local.json init-db
ai-local-video-mixer --config script_mixer.local.json doctor
ai-local-video-mixer --config script_mixer.local.json jianying-status
```

一键生产：

```bash
ai-local-video-mixer --config script_mixer.local.json make-jianying-project \\
  --media-root "D:/视频素材" \\
  --script input.txt \\
  --voice voice.wav \\
  --audio-mode mixed \\
  --draft-root "D:/JianyingPro Drafts" \\
  --candidate-count 3 \\
  --handle-before 1 \\
  --handle-after 1
```

## 核心规则

- 原始素材只读。
- 每个原视频默认只处理前40秒。
- Whisper只提供时间证据，不覆盖用户原文。
- 编辑代理使用固定帧率、H.264、统一分辨率和yuv420p。
- 默认保留前后各1秒余量，且不突破40秒窗口。
- 剪映草稿失败时，标准MP4、WAV、SRT和CSV编辑包仍然可用。
- 自动粗剪必须经过人工审核，不能假装概率模型突然获得导演执照。

## 输出目录

```text
outputs/script_mixer/<project_id>/exports/
├─ final.mp4
└─ jianying_package/
   ├─ video/
   ├─ audio/
   ├─ subtitles/
   ├─ candidates/
   ├─ metadata/
   └─ 剪映导入与修改说明.txt
```

## 测试

```bash
python -m pip install -e ".[dev]"
pytest -q
ai-local-video-mixer --help
```

## 文档

```text
docs/jianying-edit-workflow.md
docs/script-driven-mixer.md
docs/script-mixer-integration-check.md
docs/script-mixer-review.md
docs/script-mixer-next-development-plan.md
```

## 当前边界

- 真实Windows、FFmpeg、素材和剪映版本需要在本机验收。
- 剪映草稿格式为私有格式，版本升级可能影响兼容性。
- 固定帧率代理减少技术性卡帧，但不能修复原素材已损坏的帧。
- 背景音乐、音效自动选择和TTS仍属于后续开发。
- 多来源混剪不等于获得版权授权。
"""


def _standalone_agents() -> str:
    return """# Repository instructions / 独立混剪仓库规则

## 目标

本仓库只负责本地文案驱动视频混剪、时间线返修和剪映可编辑交付，不包含短剧剧本、人物资产、场景资产、分镜或生成提示词生产链。

## 固定规则

1. 原始视频、配音和文案只读，不删除、不移动、不覆盖。
2. 每个原视频默认只处理`0`到`min(duration, 40.0)`秒。
3. 40秒后的内容不得进入镜头、缩略图、视觉分析、向量、候选、时间线或编辑包。
4. 本机路径只进入被Git忽略的本地配置。
5. Whisper只提供时间证据，不得用识别文本覆盖用户原文。
6. 预览可以带警告，但阻塞项必须在报告中可见。
7. 剪映编辑包必须始终生成；直接草稿只是可选入口。
8. 编辑代理必须精确解码并重新编码为CFR、H.264、yuv420p和项目帧率。
9. 前后余量不得突破源时长和40秒处理窗口。
10. 原声、配音和字幕保持独立可编辑资产。
11. 草稿失败时保留标准MP4、WAV、SRT和CSV包。
12. 新测试不得依赖网络、真实模型、真实FFmpeg、剪映或私人素材。
13. 修改后运行`pytest -q`和`ai-local-video-mixer --help`。
"""


def _gitignore() -> str:
    return """__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
dist/
build/
*.egg-info/
.runtime/
outputs/
script_mixer.local.json
script_mixer.config.json
*.local.json
.DS_Store
Thumbs.db
"""


def _workflow() -> str:
    return """name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install
        run: python -m pip install -e ".[dev]"
      - name: Tests
        run: pytest -q
      - name: CLI import
        run: ai-local-video-mixer --help
"""


def build_repository(source_root: Path, target_root: Path, force: bool = False) -> dict:
    source_root = source_root.resolve()
    target_root = target_root.resolve()
    if target_root == source_root or source_root in target_root.parents:
        raise ValueError("Target repository must not be inside the source repository")
    if target_root.exists():
        if not force:
            raise FileExistsError(f"Target already exists: {target_root}")
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)

    source_package = source_root / "short_drama_controller" / "script_mixer"
    target_package = target_root / "ai_local_video_mixer"
    for filename in MODULE_FILES:
        _copy_file(source_package / filename, target_package / filename)

    for filename in TEST_FILES:
        _copy_file(source_root / "tests" / filename, target_root / "tests" / filename)

    for filename in DOC_FILES:
        _copy_file(source_root / "docs" / filename, target_root / "docs" / filename)

    for filename in CONFIG_FILES:
        _copy_file(source_root / "config" / filename, target_root / "config" / filename)

    for filename in SCRIPT_FILES:
        _copy_file(source_root / "scripts" / filename, target_root / "scripts" / filename)

    license_path = source_root / "LICENSE"
    if license_path.is_file():
        _copy_file(license_path, target_root / "LICENSE")

    for path in target_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".py", ".md", ".ps1", ".json", ".yml", ".yaml", ".toml"}:
            _rewrite_text(path)

    _write(target_root / "pyproject.toml", _standalone_pyproject())
    _write(target_root / "README.md", _standalone_readme())
    _write(target_root / "AGENTS.md", _standalone_agents())
    _write(target_root / ".gitignore", _gitignore())
    _write(target_root / ".github" / "workflows" / "ci.yml", _workflow())
    _write(target_package / "py.typed", "")

    manifest = {
        "source_repository": "wangduoyu001/ai-short-drama-production-controller",
        "source_branch": "feature/script-driven-local-mixer",
        "standalone_repository": "wangduoyu001/ai-local-video-mixer",
        "package": "ai_local_video_mixer",
        "cli": ["ai-local-video-mixer", "script-driven-mixer"],
        "module_files": MODULE_FILES,
        "test_files": TEST_FILES,
        "docs": DOC_FILES,
    }
    _write(target_root / "STANDALONE_MIGRATION.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def _run_validation(target_root: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(target_root / "ai_local_video_mixer")],
        check=True,
        cwd=target_root,
    )
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        check=True,
        cwd=target_root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the standalone AI local video mixer repository")
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--target", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)

    source = Path(args.source)
    target = Path(args.target)
    manifest = build_repository(source, target, force=args.force)
    if args.validate:
        _run_validation(target)
    print(json.dumps({"target": str(target.resolve()), **manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
