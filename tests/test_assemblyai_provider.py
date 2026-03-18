"""Tests for AssemblyAI provider."""

import pytest
from unittest.mock import MagicMock, patch

from transcribe_cli.providers.assemblyai import AssemblyAIProvider


def test_init_requires_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="API key required"):
            AssemblyAIProvider()


def test_init_from_env():
    with patch.dict("os.environ", {"ASSEMBLYAI_API_KEY": "test-key"}):
        provider = AssemblyAIProvider()
        assert provider.api_key == "test-key"


def test_init_explicit_key():
    provider = AssemblyAIProvider(api_key="explicit-key")
    assert provider.api_key == "explicit-key"


def test_is_available():
    assert AssemblyAIProvider.is_available() is True


def test_required_extras():
    assert AssemblyAIProvider.required_extras() == "assemblyai"


def test_name():
    assert AssemblyAIProvider.name == "assemblyai"


@patch("transcribe_cli.providers.assemblyai.aai")
def test_transcribe_basic(mock_aai):
    """Test basic transcription maps API response to TranscriptionResult."""
    mock_transcript = MagicMock()
    mock_transcript.status = MagicMock()
    mock_transcript.status.value = "completed"
    mock_transcript.text = "Hello world"
    mock_transcript.id = "test-id"
    mock_transcript.language_code = "en_us"
    mock_transcript.audio_duration = 5000
    mock_transcript.confidence = 0.95
    mock_transcript.utterances = None
    mock_transcript.entities = None
    mock_transcript.iab_categories = None
    mock_transcript.chapters = None
    mock_transcript.summary = None
    mock_transcript.sentiment_analysis = None

    # Mock get_sentences() for segment extraction
    mock_sentence = MagicMock()
    mock_sentence.text = "Hello world"
    mock_sentence.start = 0
    mock_sentence.end = 5000
    mock_sentence.confidence = 0.95
    mock_transcript.get_sentences.return_value = [mock_sentence]

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = mock_transcript
    mock_aai.Transcriber.return_value = mock_transcriber
    mock_aai.TranscriptStatus.error = "error"

    provider = AssemblyAIProvider(api_key="test-key")
    result = provider.transcribe("test.mp3")

    assert result.text == "Hello world"
    assert result.language == "en_us"
    assert len(result.segments) == 1
    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 5.0


@patch("transcribe_cli.providers.assemblyai.aai")
def test_transcribe_with_speaker_labels(mock_aai):
    """Test that speaker labels are mapped to segments."""
    mock_utt = MagicMock()
    mock_utt.text = "Hello"
    mock_utt.start = 0
    mock_utt.end = 2000
    mock_utt.speaker = "A"
    mock_utt.confidence = 0.9

    mock_transcript = MagicMock()
    mock_transcript.status = MagicMock()
    mock_transcript.status.value = "completed"
    mock_transcript.text = "Hello"
    mock_transcript.id = "test-id"
    mock_transcript.language_code = "en_us"
    mock_transcript.audio_duration = 2000
    mock_transcript.confidence = 0.9
    mock_transcript.utterances = [mock_utt]
    mock_transcript.entities = None
    mock_transcript.iab_categories = None
    mock_transcript.chapters = None
    mock_transcript.summary = None
    mock_transcript.sentiment_analysis = None

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = mock_transcript
    mock_aai.Transcriber.return_value = mock_transcriber
    mock_aai.TranscriptStatus.error = "error"

    provider = AssemblyAIProvider(api_key="test-key")
    result = provider.transcribe("test.mp3", speaker_labels=True)

    assert result.segments[0].speaker == "A"


@patch("transcribe_cli.providers.assemblyai.aai")
def test_transcribe_error_raises(mock_aai):
    """Test that API errors raise RuntimeError."""
    mock_transcript = MagicMock()
    mock_transcript.status = mock_aai.TranscriptStatus.error
    mock_transcript.error = "Something went wrong"

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = mock_transcript
    mock_aai.Transcriber.return_value = mock_transcriber

    provider = AssemblyAIProvider(api_key="test-key")
    with pytest.raises(RuntimeError, match="Something went wrong"):
        provider.transcribe("test.mp3")
