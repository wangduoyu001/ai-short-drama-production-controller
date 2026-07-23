from __future__ import annotations

from short_drama_controller.script_mixer.cli import _build_parser


def test_make_jianying_project_parser_contract() -> None:
    args = _build_parser().parse_args(
        [
            "--config",
            "local.json",
            "make-jianying-project",
            "--media-root",
            "D:/media",
            "--script",
            "input.txt",
            "--voice",
            "voice.wav",
            "--audio-mode",
            "mixed",
            "--draft-root",
            "D:/drafts",
            "--candidate-count",
            "4",
            "--handle-before",
            "1.5",
            "--handle-after",
            "2",
            "--fast-scan",
            "--skip-enrich",
            "--burn-subtitles",
        ]
    )
    assert args.command == "make-jianying-project"
    assert args.media_root == "D:/media"
    assert args.voice == "voice.wav"
    assert args.audio_mode == "mixed"
    assert args.draft_root == "D:/drafts"
    assert args.candidate_count == 4
    assert args.handle_before == 1.5
    assert args.handle_after == 2.0
    assert args.fast_scan is True
    assert args.skip_enrich is True
    assert args.skip_embeddings is False
    assert args.burn_subtitles is True
    assert args.no_draft is False
    assert args.require_draft is False


def test_export_jianying_package_parser_contract() -> None:
    args = _build_parser().parse_args(
        [
            "export-jianying-package",
            "--project",
            "demo",
            "--no-draft",
            "--force-package",
            "--package-dry-run",
            "--candidate-count",
            "0",
        ]
    )
    assert args.command == "export-jianying-package"
    assert args.project == "demo"
    assert args.no_draft is True
    assert args.force_package is True
    assert args.package_dry_run is True
    assert args.candidate_count == 0


def test_jianying_status_parser_contract() -> None:
    args = _build_parser().parse_args(["jianying-status"])
    assert args.command == "jianying-status"
