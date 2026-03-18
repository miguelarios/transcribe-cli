"""Tests for base data classes and output formatting."""

from transcribe_cli.base import Segment, TranscriptionResult


def test_segment_defaults():
    seg = Segment(text="hello", start=0.0, end=1.0)
    assert seg.speaker is None
    assert seg.confidence is None
    assert seg.sentiment is None


def test_transcription_result_to_dict():
    result = TranscriptionResult(
        text="Hello world",
        segments=[
            Segment(text="Hello world", start=0.0, end=2.0, speaker="A", confidence=0.95),
        ],
        language="en_us",
        duration_seconds=2.0,
        provider="test",
        elapsed_seconds=0.5,
        metadata={"id": "abc123"},
    )
    d = result.to_dict()
    assert d["text"] == "Hello world"
    assert len(d["segments"]) == 1
    assert d["segments"][0]["speaker"] == "A"
    assert d["provider"] == "test"
    assert d["metadata"]["id"] == "abc123"


def test_transcription_result_to_dict_omits_none_speaker():
    result = TranscriptionResult(
        text="Hi",
        segments=[Segment(text="Hi", start=0.0, end=1.0)],
    )
    d = result.to_dict()
    assert "speaker" not in d["segments"][0]
    assert "confidence" not in d["segments"][0]
    assert "sentiment" not in d["segments"][0]


def test_to_srt():
    result = TranscriptionResult(
        text="Hello. World.",
        segments=[
            Segment(text="Hello.", start=0.0, end=1.5),
            Segment(text="World.", start=2.0, end=3.5),
        ],
    )
    srt = result.to_srt()
    assert "1\n00:00:00,000 --> 00:00:01,500\nHello." in srt
    assert "2\n00:00:02,000 --> 00:00:03,500\nWorld." in srt


def test_to_srt_with_speakers():
    result = TranscriptionResult(
        text="Hi. Hey.",
        segments=[
            Segment(text="Hi.", start=0.0, end=1.0, speaker="A"),
            Segment(text="Hey.", start=1.5, end=2.5, speaker="B"),
        ],
    )
    srt = result.to_srt()
    assert "Speaker A: Hi." in srt
    assert "Speaker B: Hey." in srt


def test_to_vtt():
    result = TranscriptionResult(
        text="Hello.",
        segments=[Segment(text="Hello.", start=0.0, end=1.5)],
    )
    vtt = result.to_vtt()
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.500" in vtt


def test_to_srt_no_segments_returns_text():
    result = TranscriptionResult(text="Just text")
    assert result.to_srt() == "Just text"


def test_to_vtt_no_segments_returns_text():
    result = TranscriptionResult(text="Just text")
    assert "Just text" in result.to_vtt()


def test_to_text_with_speakers():
    result = TranscriptionResult(
        text="Hi. Hey.",
        segments=[
            Segment(text="Hi.", start=0.0, end=1.0, speaker="A"),
            Segment(text="Hey.", start=1.5, end=2.5, speaker="B"),
        ],
    )
    text = result.to_text()
    assert "[00:00:00] Speaker A: Hi." in text
    assert "[00:00:01] Speaker B: Hey." in text


def test_to_text_without_speakers():
    result = TranscriptionResult(
        text="Hello. World.",
        segments=[
            Segment(text="Hello.", start=0.0, end=1.5),
            Segment(text="World.", start=2.0, end=3.5),
        ],
    )
    text = result.to_text()
    assert "[00:00:00] Hello." in text
    assert "[00:00:02] World." in text
    assert "Speaker" not in text


def test_to_text_no_segments_returns_text():
    result = TranscriptionResult(text="Just text")
    assert result.to_text() == "Just text"


def test_to_summary():
    result = TranscriptionResult(
        text="Hello world this is a test with some words",
        segments=[
            Segment(text="Hello world", start=0.0, end=2.0, speaker="A"),
            Segment(text="this is a test with some words", start=2.0, end=5.0, speaker="B"),
        ],
        language="en_us",
        duration_seconds=5.0,
        provider="assemblyai",
        elapsed_seconds=1.2,
        metadata={"id": "abc123"},
    )
    summary = result.to_summary()
    assert summary["word_count"] == 9
    assert summary["speaker_count"] == 2
    assert summary["duration_seconds"] == 5.0
    assert summary["language"] == "en_us"
    assert summary["provider"] == "assemblyai"
    assert "file" in summary
    assert summary["file"].endswith(".json")

    # With explicit output_path and content, transcript text is written there
    import tempfile as _tf
    from pathlib import Path
    with _tf.NamedTemporaryFile(suffix=".md", delete=False) as f:
        out_path = f.name
    formatted = result.to_text()
    summary2 = result.to_summary(output_path=out_path, output_content=formatted)
    assert summary2["file"] == out_path
    written = Path(out_path).read_text()
    assert written == formatted
    Path(out_path).unlink()
