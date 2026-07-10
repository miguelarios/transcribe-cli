"""Tests for AssemblyAI provider."""

import pytest
from unittest.mock import MagicMock, patch

from transcribe_cli.providers.assemblyai import DEFAULT_REDACT_POLICIES, AssemblyAIProvider


def _mock_transcript(utterances=None):
    """A minimal successful transcript mock."""
    transcript = MagicMock()
    transcript.status = "completed"
    transcript.text = "hello world"
    transcript.utterances = utterances
    transcript.get_sentences.return_value = []
    transcript.language_code = "en_us"
    transcript.audio_duration = 1000
    transcript.id = "test-id"
    return transcript


def _transcribe_and_capture_config(mock_aai, **kwargs):
    """Run transcribe() against a mocked SDK; return the TranscriptionConfig kwargs."""
    mock_aai.Transcriber.return_value.transcribe.return_value = _mock_transcript(
        utterances=kwargs.pop("_utterances", None)
    )
    provider = AssemblyAIProvider(api_key="test-key")
    result = provider.transcribe("audio.mp3", **kwargs)
    return mock_aai.TranscriptionConfig.call_args.kwargs, result


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
    # assemblyai is a core dependency, so no extras are required
    assert AssemblyAIProvider.required_extras() == ""


def test_name():
    assert AssemblyAIProvider.name == "assemblyai"


@patch("transcribe_cli.providers.assemblyai.aai")
def test_redact_pii_sends_default_policies(mock_aai):
    cfg, _ = _transcribe_and_capture_config(mock_aai, redact_pii=True)
    assert cfg["redact_pii"] is True
    assert cfg["redact_pii_policies"] == DEFAULT_REDACT_POLICIES


@patch("transcribe_cli.providers.assemblyai.aai")
def test_redact_pii_explicit_policies(mock_aai):
    cfg, _ = _transcribe_and_capture_config(
        mock_aai, redact_pii=True, redact_policies=["person_name", "location"]
    )
    assert cfg["redact_pii_policies"] == ["person_name", "location"]


@patch("transcribe_cli.providers.assemblyai.aai")
def test_no_redact_pii_omits_policies(mock_aai):
    cfg, _ = _transcribe_and_capture_config(mock_aai)
    assert "redact_pii_policies" not in cfg


@patch("transcribe_cli.providers.assemblyai.aai")
def test_speaker_identification_request_shape(mock_aai):
    cfg, _ = _transcribe_and_capture_config(
        mock_aai, speaker_id_type="role", speaker_names=["Interviewer", "Interviewee"]
    )
    # API requires the "request" wrapper and speaker_labels enabled
    assert cfg["speaker_labels"] is True
    assert cfg["speech_understanding"] == {
        "request": {
            "speaker_identification": {
                "speaker_type": "role",
                "known_values": ["Interviewer", "Interviewee"],
            }
        }
    }


@patch("transcribe_cli.providers.assemblyai.time")
@patch("transcribe_cli.providers.assemblyai.aai")
def test_progress_callback_switches_to_submit_and_poll(mock_aai, mock_time):
    submitted = MagicMock()
    submitted.id = "t1"
    submitted.status = "queued"
    processing = MagicMock()
    processing.id = "t1"
    processing.status = "processing"
    done = _mock_transcript()
    done.status = mock_aai.TranscriptStatus.completed

    mock_aai.Transcriber.return_value.submit.return_value = submitted
    mock_aai.Transcript.get_by_id.side_effect = [processing, done]

    events = []
    provider = AssemblyAIProvider(api_key="test-key")
    result = provider.transcribe("audio.mp3", progress_callback=events.append)

    # Blocking transcribe() must not be used when polling
    mock_aai.Transcriber.return_value.transcribe.assert_not_called()
    assert result.text == "hello world"
    names = [e["event"] for e in events]
    assert names == ["uploading", "submitted", "status", "completed"]
    assert events[1]["id"] == "t1"


@patch("transcribe_cli.providers.assemblyai.time")
@patch("transcribe_cli.providers.assemblyai.aai")
def test_progress_callback_url_skips_uploading_event(mock_aai, mock_time):
    done = _mock_transcript()
    done.status = mock_aai.TranscriptStatus.completed
    done.id = "t2"
    mock_aai.Transcriber.return_value.submit.return_value = done

    events = []
    provider = AssemblyAIProvider(api_key="test-key")
    provider.transcribe("https://example.com/a.mp3", progress_callback=events.append)

    names = [e["event"] for e in events]
    assert names == ["submitted", "completed"]


@patch("transcribe_cli.providers.assemblyai.aai")
def test_no_progress_callback_uses_blocking_transcribe(mock_aai):
    mock_aai.Transcriber.return_value.transcribe.return_value = _mock_transcript()
    provider = AssemblyAIProvider(api_key="test-key")
    provider.transcribe("audio.mp3")
    mock_aai.Transcriber.return_value.transcribe.assert_called_once()
    mock_aai.Transcriber.return_value.submit.assert_not_called()


def _mock_utterance(channel, text="hi", start=0, end=1000):
    utt = MagicMock()
    utt.channel = channel
    utt.text = text
    utt.start = start
    utt.end = end
    utt.confidence = 0.9
    utt.sentiment = None
    return utt


@patch("transcribe_cli.providers.assemblyai.aai")
def test_multichannel_string_channels_map_to_names(mock_aai):
    # API types channel as string, 1-indexed
    _, result = _transcribe_and_capture_config(
        mock_aai,
        multichannel=True,
        channel_names=["Me", "Them"],
        _utterances=[_mock_utterance("1"), _mock_utterance("2")],
    )
    assert [s.speaker for s in result.segments] == ["Me", "Them"]


@patch("transcribe_cli.providers.assemblyai.aai")
def test_multichannel_out_of_range_channel_falls_back(mock_aai):
    _, result = _transcribe_and_capture_config(
        mock_aai,
        multichannel=True,
        channel_names=["Me", "Them"],
        _utterances=[_mock_utterance("3"), _mock_utterance("left")],
    )
    assert [s.speaker for s in result.segments] == ["Channel 3", "Channel left"]


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
