"""Tests for CLI entry point."""

import json

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from transcribe_cli import __version__
from transcribe_cli.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Transcribe audio files" in result.output


def test_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_list_providers(runner):
    result = runner.invoke(cli, ["--list-providers"])
    assert result.exit_code == 0
    assert "assemblyai" in result.output


def test_list_providers_json(runner):
    result = runner.invoke(cli, ["--list-providers", "-f", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    names = [p["name"] for p in data]
    assert "assemblyai" in names


def test_no_args_shows_help_with_agent_note(runner):
    # Bare invocation prints full help + agent note (like `td`), exit 0
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Note for AI/LLM agents" in result.output


def test_help_includes_agent_note(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Note for AI/LLM agents" in result.output
    assert "--summary" in result.output


def test_missing_api_key_shows_error(runner):
    with patch.dict("os.environ", {}, clear=True):
        result = runner.invoke(cli, ["nonexistent.mp3"])
        assert result.exit_code != 0


def test_ndjson_format_outputs_segment_lines(runner, tmp_path):
    from transcribe_cli.base import Segment, TranscriptionResult

    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")
    result = TranscriptionResult(
        text="Hi. Hey.",
        segments=[
            Segment(text="Hi.", start=0.0, end=1.0, speaker="A"),
            Segment(text="Hey.", start=1.5, end=2.5, speaker="B"),
        ],
    )
    provider = MagicMock()
    provider.timed_transcribe.return_value = result
    with patch("transcribe_cli.providers.get_provider", return_value=provider):
        out = runner.invoke(cli, [str(audio), "-f", "ndjson", "--api-key", "test"])
    assert out.exit_code == 0
    lines = [json.loads(line) for line in out.output.strip().splitlines()]
    assert [line["speaker"] for line in lines] == ["A", "B"]


def test_dry_run_prints_config_without_api_key_or_network(runner, tmp_path):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")
    with patch.dict("os.environ", {}, clear=True):
        with patch("transcribe_cli.providers.get_provider") as mock_get:
            result = runner.invoke(cli, [str(audio), "--dry-run", "--speaker-labels"])
    assert result.exit_code == 0
    mock_get.assert_not_called()
    data = json.loads(result.output)
    assert data["provider"] == "assemblyai"
    assert data["audio"].endswith("audio.mp3")
    assert data["config"]["speaker_labels"] is True


def test_dry_run_resolves_redact_policy_defaults(runner, tmp_path):
    from transcribe_cli.providers.assemblyai import DEFAULT_REDACT_POLICIES

    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")
    result = runner.invoke(cli, [str(audio), "--dry-run", "--redact-pii"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["config"]["redact_pii_policies"] == DEFAULT_REDACT_POLICIES


def test_progress_jsonl_writes_events_to_file(runner, tmp_path):
    from transcribe_cli.base import TranscriptionResult

    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")
    events_file = tmp_path / "events.jsonl"

    provider = MagicMock()

    def fake_timed(audio_arg, **kwargs):
        kwargs["progress_callback"]({"event": "submitted", "id": "t1"})
        kwargs["progress_callback"]({"event": "completed"})
        return TranscriptionResult(text="hi")

    provider.timed_transcribe.side_effect = fake_timed
    with patch("transcribe_cli.providers.get_provider", return_value=provider):
        result = runner.invoke(cli, [
            str(audio), "--api-key", "k", "--progress-jsonl", str(events_file),
        ])
    assert result.exit_code == 0
    lines = [json.loads(line) for line in events_file.read_text().strip().splitlines()]
    assert [e["event"] for e in lines] == ["submitted", "completed"]


def test_doctor_offline_all_pass(runner):
    with patch.dict("os.environ", {"ASSEMBLYAI_API_KEY": "test"}):
        result = runner.invoke(cli, ["--doctor", "--offline", "-f", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    checks = {c["name"]: c for c in data["checks"]}
    assert checks["api_key"]["status"] == "pass"
    assert checks["sdk"]["status"] == "pass"
    assert checks["providers"]["status"] == "pass"
    # Network checks are skipped offline
    assert checks["key_valid"]["status"] == "skip"
    assert checks["update"]["status"] == "skip"
    assert data["summary"]["failed"] == 0


def test_doctor_missing_api_key_fails(runner):
    with patch.dict("os.environ", {}, clear=True):
        result = runner.invoke(cli, ["--doctor", "--offline", "-f", "json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    checks = {c["name"]: c for c in data["checks"]}
    assert checks["api_key"]["status"] == "fail"


def test_doctor_reports_invalid_key_online(runner):
    fake_resp = MagicMock(status_code=401)
    with patch.dict("os.environ", {"ASSEMBLYAI_API_KEY": "bad-key"}):
        with patch("httpx.get", return_value=fake_resp):
            result = runner.invoke(cli, ["--doctor", "-f", "json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    checks = {c["name"]: c for c in data["checks"]}
    assert checks["key_valid"]["status"] == "fail"


def test_doctor_human_output(runner):
    with patch.dict("os.environ", {"ASSEMBLYAI_API_KEY": "test"}):
        result = runner.invoke(cli, ["--doctor", "--offline"])
    assert result.exit_code == 0
    assert "api_key" in result.output
    assert "pass" in result.output


def test_speaker_expected_with_range_errors(runner):
    with patch.dict("os.environ", {"ASSEMBLYAI_API_KEY": "test"}):
        result = runner.invoke(cli, [
            "test.mp3",
            "--speakers-expected", "3",
            "--min-speakers", "2",
        ])
        assert result.exit_code != 0
        assert "Cannot use" in result.output


def test_min_without_max_errors(runner):
    with patch.dict("os.environ", {"ASSEMBLYAI_API_KEY": "test"}):
        result = runner.invoke(cli, [
            "test.mp3",
            "--min-speakers", "2",
        ])
        assert result.exit_code != 0
        assert "both" in result.output.lower()
