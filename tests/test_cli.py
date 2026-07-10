"""Tests for CLI entry point."""

import json

import pytest
from click.testing import CliRunner
from unittest.mock import patch

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
