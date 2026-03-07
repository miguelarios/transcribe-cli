# transcribe-cli v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a modular audio transcription CLI (`transcribe`) using AssemblyAI, publishable to PyPI.

**Architecture:** Click-based CLI with a provider abstraction layer. V1 has one provider (AssemblyAI). Provider registry pattern allows future providers to be added by dropping in a new file. All output goes to stdout by default; `-o` writes to file.

**Tech Stack:** Python 3.10+, Click, AssemblyAI SDK, hatchling (build), pytest (test)

**Design doc:** `docs/plans/2026-03-06-transcribe-cli-v1-design.md`

---

### Task 1: Project scaffolding and pyproject.toml

**Files:**
- Create: `src/transcribe_cli/__init__.py`
- Create: `src/transcribe_cli/providers/__init__.py` (empty for now)
- Modify: `pyproject.toml`
- Delete: `transcribe.py` (old monolith, replaced by package)
- Delete: `src/transcribe.egg-info/` (stale build artifacts)
- Delete: `files/` (scaffold reference, no longer needed)

**Step 1: Clean up old files**

```bash
rm -f transcribe.py
rm -rf src/transcribe.egg-info/
rm -rf files/
```

**Step 2: Create package init**

Create `src/transcribe_cli/__init__.py`:

```python
"""transcribe-cli — modular audio transcription with pluggable providers."""

__version__ = "0.1.0"
```

**Step 3: Create empty providers package**

Create `src/transcribe_cli/providers/__init__.py`:

```python
"""Provider registry — discovers and manages transcription backends."""
```

**Step 4: Rewrite pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "transcribe-cli"
version = "0.1.0"
description = "A modular transcription CLI with pluggable providers. Agent-friendly."
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "Miguel Rios" }]

dependencies = [
    "click>=8.1",
    "assemblyai>=0.30",
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[project.scripts]
transcribe = "transcribe_cli.cli:cli"

[tool.hatch.build.targets.wheel]
packages = ["src/transcribe_cli"]

[tool.ruff]
line-length = 100
```

**Step 5: Verify the package structure**

```bash
ls src/transcribe_cli/__init__.py src/transcribe_cli/providers/__init__.py
```

Expected: both files listed, no errors.

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: replace monolith with transcribe_cli package scaffold"
```

---

### Task 2: Base classes (Segment, TranscriptionResult, TranscriptionProvider)

**Files:**
- Create: `src/transcribe_cli/base.py`
- Create: `tests/test_base.py`

**Step 1: Write tests for Segment and TranscriptionResult**

Create `tests/test_base.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/mrios/Nextcloud/01-Projects/transcribe-cli
uv run pytest tests/test_base.py -v
```

Expected: ImportError — `transcribe_cli.base` does not exist yet.

**Step 3: Implement base.py**

Create `src/transcribe_cli/base.py`:

```python
"""Base provider interface and data classes for transcription backends."""

from __future__ import annotations

import json
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    """A timestamped segment of transcribed text."""

    text: str
    start: float  # seconds
    end: float  # seconds
    speaker: str | None = None
    confidence: float | None = None
    sentiment: str | None = None


@dataclass
class TranscriptionResult:
    """Standardized result from any transcription provider."""

    text: str
    segments: list[Segment] = field(default_factory=list)
    language: str | None = None
    duration_seconds: float | None = None
    provider: str = ""
    elapsed_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON output."""
        return {
            "text": self.text,
            "segments": [
                {
                    "text": s.text,
                    "start": s.start,
                    "end": s.end,
                    **({"speaker": s.speaker} if s.speaker else {}),
                    **({"confidence": s.confidence} if s.confidence is not None else {}),
                    **({"sentiment": s.sentiment} if s.sentiment is not None else {}),
                }
                for s in self.segments
            ],
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "provider": self.provider,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "metadata": self.metadata,
        }

    def to_text(self) -> str:
        """Render as timestamped text with optional speaker labels."""
        if not self.segments:
            return self.text

        lines = []
        for seg in self.segments:
            ts = _fmt_timestamp(seg.start)
            if seg.speaker:
                lines.append(f"[{ts}] Speaker {seg.speaker}: {seg.text.strip()}")
            else:
                lines.append(f"[{ts}] {seg.text.strip()}")
        return "\n".join(lines)

    def to_srt(self) -> str:
        """Render segments as SRT subtitle format."""
        if not self.segments:
            return self.text

        lines = []
        for i, seg in enumerate(self.segments, 1):
            start = _fmt_srt_time(seg.start)
            end = _fmt_srt_time(seg.end)
            text = seg.text.strip()
            if seg.speaker:
                text = f"Speaker {seg.speaker}: {text}"
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def to_vtt(self) -> str:
        """Render segments as WebVTT subtitle format."""
        if not self.segments:
            return f"WEBVTT\n\n{self.text}"

        lines = ["WEBVTT", ""]
        for seg in self.segments:
            start = _fmt_vtt_time(seg.start)
            end = _fmt_vtt_time(seg.end)
            text = seg.text.strip()
            if seg.speaker:
                text = f"Speaker {seg.speaker}: {text}"
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def to_summary(self) -> dict:
        """Generate agent-friendly summary metadata, save full transcript to temp file."""
        tmp_dir = Path(tempfile.gettempdir()) / "transcribe-cli"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = tmp_dir / f"{self.metadata.get('id', 'transcript')}.json"
        tmp_file.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

        word_count = len(self.text.split())
        speakers = {s.speaker for s in self.segments if s.speaker}

        return {
            "file": str(tmp_file),
            "word_count": word_count,
            "token_count": int(word_count * 1.3),  # rough estimate
            "speaker_count": len(speakers),
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "provider": self.provider,
        }


def _fmt_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


class TranscriptionProvider(ABC):
    """Abstract base class for transcription providers."""

    name: str = "base"

    @abstractmethod
    def transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        timestamps: bool = True,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe an audio file and return a standardized result."""
        ...

    @classmethod
    def is_available(cls) -> bool:
        """Check if this provider's dependencies are installed."""
        return True

    @classmethod
    def required_extras(cls) -> str:
        """pip extras name needed to install this provider."""
        return ""

    def timed_transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        timestamps: bool = True,
        **kwargs,
    ) -> TranscriptionResult:
        """Wrapper that adds timing info to the result."""
        start = time.monotonic()
        result = self.transcribe(
            audio_path, language=language, timestamps=timestamps, **kwargs
        )
        result.elapsed_seconds = time.monotonic() - start
        result.provider = self.name
        return result
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_base.py -v
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/transcribe_cli/base.py tests/test_base.py
git commit -m "feat: add base data classes and provider abstraction"
```

---

### Task 3: Provider registry

**Files:**
- Modify: `src/transcribe_cli/providers/__init__.py`
- Create: `tests/test_registry.py`

**Step 1: Write tests for the registry**

Create `tests/test_registry.py`:

```python
"""Tests for provider registry."""

from transcribe_cli.base import TranscriptionProvider, TranscriptionResult
from transcribe_cli.providers import register, get_provider, list_providers, _PROVIDERS

import pytest


class _FakeProvider(TranscriptionProvider):
    name = "fake"

    def transcribe(self, audio_path, **kwargs):
        return TranscriptionResult(text="fake")

    @classmethod
    def is_available(cls):
        return True


class _UnavailableProvider(TranscriptionProvider):
    name = "unavailable"

    def transcribe(self, audio_path, **kwargs):
        return TranscriptionResult(text="")

    @classmethod
    def is_available(cls):
        return False

    @classmethod
    def required_extras(cls):
        return "unavailable"


def test_register_and_get_provider():
    register(_FakeProvider)
    provider = get_provider("fake")
    assert isinstance(provider, _FakeProvider)


def test_get_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")


def test_get_unavailable_provider_raises():
    register(_UnavailableProvider)
    with pytest.raises(RuntimeError, match="dependencies not installed"):
        get_provider("unavailable")


def test_list_providers_includes_registered():
    register(_FakeProvider)
    providers = list_providers()
    names = [p["name"] for p in providers]
    assert "fake" in names


def teardown_function():
    _PROVIDERS.pop("fake", None)
    _PROVIDERS.pop("unavailable", None)
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_registry.py -v
```

Expected: ImportError — `register`, `get_provider`, etc. not defined.

**Step 3: Implement the registry**

Rewrite `src/transcribe_cli/providers/__init__.py`:

```python
"""Provider registry — discovers and manages available transcription backends."""

from __future__ import annotations

from transcribe_cli.base import TranscriptionProvider

_PROVIDERS: dict[str, type[TranscriptionProvider]] = {}


def register(cls: type[TranscriptionProvider]) -> type[TranscriptionProvider]:
    """Register a provider class by its name."""
    _PROVIDERS[cls.name] = cls
    return cls


def get_provider(name: str, **kwargs) -> TranscriptionProvider:
    """Instantiate a provider by name."""
    if name not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    cls = _PROVIDERS[name]
    if not cls.is_available():
        extras = cls.required_extras()
        raise RuntimeError(
            f"Provider '{name}' dependencies not installed. "
            f"Install with: pip install 'transcribe-cli[{extras}]'"
        )
    return cls(**kwargs)


def list_providers() -> list[dict]:
    """List all registered providers with availability status."""
    return [
        {
            "name": name,
            "available": cls.is_available(),
            "extras": cls.required_extras(),
        }
        for name, cls in sorted(_PROVIDERS.items())
    ]


def _auto_discover():
    """Import all provider modules to trigger @register decorators."""
    try:
        from transcribe_cli.providers import assemblyai  # noqa: F401
    except ImportError:
        pass


_auto_discover()
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_registry.py -v
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/transcribe_cli/providers/__init__.py tests/test_registry.py
git commit -m "feat: add provider registry with register/get/list"
```

---

### Task 4: AssemblyAI provider

**Files:**
- Create: `src/transcribe_cli/providers/assemblyai.py`
- Create: `tests/test_assemblyai_provider.py`

Note: Tests use mocking since we can't call the real API in tests.

**Step 1: Write tests**

Create `tests/test_assemblyai_provider.py`:

```python
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

    # Mock sentences() for segment extraction
    mock_sentence = MagicMock()
    mock_sentence.text = "Hello world"
    mock_sentence.start = 0
    mock_sentence.end = 5000
    mock_sentence.confidence = 0.95
    mock_transcript.sentences.return_value = [mock_sentence]

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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_assemblyai_provider.py -v
```

Expected: ImportError — `transcribe_cli.providers.assemblyai` does not exist.

**Step 3: Implement AssemblyAI provider**

Create `src/transcribe_cli/providers/assemblyai.py`:

```python
"""AssemblyAI provider — cloud transcription with full feature support."""

from __future__ import annotations

import os
from pathlib import Path

import assemblyai as aai

from transcribe_cli.base import Segment, TranscriptionProvider, TranscriptionResult
from transcribe_cli.providers import register


@register
class AssemblyAIProvider(TranscriptionProvider):
    """Cloud transcription via AssemblyAI.

    Supports speaker diarization, sentiment analysis, entity detection,
    auto chapters, summarization, topic detection, and more.

    API reference: https://www.assemblyai.com/docs/api-reference/transcripts/submit
    """

    name = "assemblyai"

    def __init__(self, *, api_key: str | None = None, **kwargs):
        self.api_key = api_key or os.environ.get("ASSEMBLYAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "AssemblyAI API key required. Set ASSEMBLYAI_API_KEY env var "
                "or pass --api-key <key>"
            )

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = None,
        timestamps: bool = True,
        speaker_labels: bool = False,
        speakers_expected: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        speaker_id_type: str | None = None,
        speaker_names: list[str] | None = None,
        sentiment: bool = False,
        entities: bool = False,
        topics: bool = False,
        auto_chapters: bool = False,
        summarize: bool = False,
        summary_model: str = "informative",
        summary_type: str = "bullets",
        content_safety: bool = False,
        multichannel: bool = False,
        redact_pii: bool = False,
        filter_profanity: bool = False,
        disfluencies: bool = False,
        prompt: str | None = None,
        keyterms: list[str] | None = None,
        punctuate: bool = True,
        format_text: bool = True,
        language_detection: bool = False,
        **kwargs,
    ) -> TranscriptionResult:
        aai.settings.api_key = self.api_key

        config_kwargs: dict = {
            "speaker_labels": speaker_labels,
            "sentiment_analysis": sentiment,
            "entity_detection": entities,
            "iab_categories": topics,
            "auto_chapters": auto_chapters,
            "content_safety": content_safety,
            "multichannel": multichannel,
            "redact_pii": redact_pii,
            "filter_profanity": filter_profanity,
            "disfluencies": disfluencies,
            "punctuate": punctuate,
            "format_text": format_text,
            "language_detection": language_detection,
        }

        if language and not language_detection:
            config_kwargs["language_code"] = language

        if speakers_expected:
            config_kwargs["speakers_expected"] = speakers_expected

        if min_speakers and max_speakers:
            config_kwargs["speaker_options"] = aai.SpeakerOptions(
                min_speakers_expected=min_speakers,
                max_speakers_expected=max_speakers,
            )

        if summarize:
            config_kwargs["summarization"] = True
            summary_model_map = {
                "informative": aai.SummarizationModel.informative,
                "conversational": aai.SummarizationModel.conversational,
                "catchy": aai.SummarizationModel.catchy,
            }
            summary_type_map = {
                "bullets": aai.SummarizationType.bullets,
                "bullets_verbose": aai.SummarizationType.bullets_verbose,
                "gist": aai.SummarizationType.gist,
                "headline": aai.SummarizationType.headline,
                "paragraph": aai.SummarizationType.paragraph,
            }
            config_kwargs["summary_model"] = summary_model_map[summary_model]
            config_kwargs["summary_type"] = summary_type_map[summary_type]

        if prompt:
            config_kwargs["prompt"] = prompt

        if keyterms:
            config_kwargs["keyterms_prompt"] = keyterms

        # Speech understanding: speaker identification
        if speaker_id_type and speaker_names:
            config_kwargs["speech_understanding"] = {
                "speaker_identification": {
                    "speaker_type": speaker_id_type,
                    "known_values": speaker_names,
                }
            }

        config = aai.TranscriptionConfig(**config_kwargs)
        transcriber = aai.Transcriber()

        audio_str = str(audio_path)
        transcript = transcriber.transcribe(audio_str, config=config)

        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(f"AssemblyAI error: {transcript.error}")

        # Build segments from utterances (if speaker_labels) or sentences
        segments = []
        if timestamps and speaker_labels and transcript.utterances:
            for utt in transcript.utterances:
                seg = Segment(
                    text=utt.text,
                    start=utt.start / 1000.0,
                    end=utt.end / 1000.0,
                    speaker=utt.speaker,
                    confidence=utt.confidence,
                )
                if sentiment and hasattr(utt, "sentiment") and utt.sentiment:
                    seg.sentiment = utt.sentiment.value
                segments.append(seg)
        elif timestamps:
            for sent in transcript.sentences():
                segments.append(
                    Segment(
                        text=sent.text,
                        start=sent.start / 1000.0,
                        end=sent.end / 1000.0,
                        confidence=sent.confidence,
                    )
                )

        # Build metadata
        meta: dict = {"id": transcript.id}
        if entities and transcript.entities:
            meta["entities"] = [
                {"text": e.text, "type": e.entity_type.value, "start": e.start, "end": e.end}
                for e in transcript.entities
            ]
        if auto_chapters and transcript.chapters:
            meta["chapters"] = [
                {
                    "headline": c.headline,
                    "summary": c.summary,
                    "gist": c.gist,
                    "start": c.start,
                    "end": c.end,
                }
                for c in transcript.chapters
            ]
        if topics and transcript.iab_categories:
            if hasattr(transcript.iab_categories, "summary") and transcript.iab_categories.summary:
                meta["topics"] = {
                    topic: relevance
                    for topic, relevance in transcript.iab_categories.summary.items()
                }
        if summarize and transcript.summary:
            meta["summary"] = transcript.summary
        if content_safety and hasattr(transcript, "content_safety") and transcript.content_safety:
            meta["content_safety"] = transcript.content_safety

        return TranscriptionResult(
            text=transcript.text or "",
            segments=segments,
            language=transcript.language_code,
            duration_seconds=(transcript.audio_duration or 0) / 1000.0,
            metadata=meta,
        )

    @classmethod
    def is_available(cls) -> bool:
        try:
            import assemblyai  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def required_extras(cls) -> str:
        return "assemblyai"
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_assemblyai_provider.py -v
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/transcribe_cli/providers/assemblyai.py tests/test_assemblyai_provider.py
git commit -m "feat: add AssemblyAI provider with full API feature support"
```

---

### Task 5: CLI entry point

**Files:**
- Create: `src/transcribe_cli/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write tests**

Create `tests/test_cli.py`:

```python
"""Tests for CLI entry point."""

from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from transcribe_cli.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


import pytest


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Transcribe audio files" in result.output


def test_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_list_providers(runner):
    result = runner.invoke(cli, ["--list-providers"])
    assert result.exit_code == 0
    assert "assemblyai" in result.output


def test_list_providers_json(runner):
    result = runner.invoke(cli, ["--list-providers", "-f", "json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    names = [p["name"] for p in data]
    assert "assemblyai" in names


def test_no_audio_file_shows_error(runner):
    result = runner.invoke(cli, [])
    assert result.exit_code != 0


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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: ImportError — `transcribe_cli.cli` does not exist.

**Step 3: Implement CLI**

Create `src/transcribe_cli/cli.py`:

```python
"""transcribe CLI — modular transcription with pluggable providers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from transcribe_cli import __version__


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _emit_result(result, fmt: str, output: str | None, verbose: bool):
    """Format and write the transcription result."""
    if fmt == "json":
        content = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    elif fmt == "srt":
        content = result.to_srt()
    elif fmt == "vtt":
        content = result.to_vtt()
    else:
        content = result.to_text()

    if output:
        Path(output).write_text(content, encoding="utf-8")
        if verbose:
            click.echo(f"Written to {output}", err=True)
    else:
        click.echo(content)

    if verbose:
        click.echo(
            f"[{result.provider}] "
            f"{result.elapsed_seconds:.1f}s elapsed"
            + (f", {result.duration_seconds:.0f}s audio" if result.duration_seconds else "")
            + (f", {result.language}" if result.language else ""),
            err=True,
        )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("audio", required=False)
@click.option("--api-key", default=None, envvar="ASSEMBLYAI_API_KEY",
              help="AssemblyAI API key.  [env: ASSEMBLYAI_API_KEY]")
@click.option("-f", "--format", "output_format",
              type=click.Choice(["text", "json", "srt", "vtt"]),
              default="text", show_default=True,
              help="Output format.")
@click.option("-o", "--output", type=click.Path(), default=None,
              help="Write output to file instead of stdout.")
@click.option("--summary", "summary_mode", is_flag=True, default=False,
              help="Output metadata summary only; save full transcript to temp file.")
# Speaker/Diarization
@click.option("--speaker-labels", is_flag=True, default=False, show_default=True,
              help="Enable speaker diarization. [API: speaker_labels]")
@click.option("--speakers-expected", type=int, default=None,
              help="Exact number of speakers. [API: speakers_expected]")
@click.option("--min-speakers", type=int, default=None,
              help="Min speakers (use with --max-speakers). [API: speaker_options.min_speakers_expected]")
@click.option("--max-speakers", type=int, default=None,
              help="Max speakers (use with --min-speakers). [API: speaker_options.max_speakers_expected]")
@click.option("--speaker-id-type", type=click.Choice(["role", "name"]), default=None,
              help="Speaker identification mode. [API: speech_understanding.speaker_identification.speaker_type]")
@click.option("--speaker-names", multiple=True,
              help="Known speaker names/roles (repeatable, 35 char max). [API: speech_understanding.speaker_identification.known_values]")
# Analysis
@click.option("--entities", is_flag=True, default=False, show_default=True,
              help="Detect names, locations, dates, etc. [API: entity_detection]")
@click.option("--sentiment", is_flag=True, default=False, show_default=True,
              help="Sentiment analysis per utterance. [API: sentiment_analysis]")
@click.option("--topics", is_flag=True, default=False, show_default=True,
              help="IAB topic detection. [API: iab_categories]")
@click.option("--auto-chapters", is_flag=True, default=False, show_default=True,
              help="Generate chapters with headlines. [API: auto_chapters]")
@click.option("--summarize", is_flag=True, default=False, show_default=True,
              help="Generate transcript summary. [API: summarization]")
@click.option("--summary-model",
              type=click.Choice(["informative", "conversational", "catchy"]),
              default="informative", show_default=True,
              help="Summary model (use with --summarize). [API: summary_model]")
@click.option("--summary-type",
              type=click.Choice(["bullets", "bullets_verbose", "gist", "headline", "paragraph"]),
              default="bullets", show_default=True,
              help="Summary format (use with --summarize). [API: summary_type]")
@click.option("--content-safety", is_flag=True, default=False, show_default=True,
              help="Enable content moderation. [API: content_safety]")
# Language
@click.option("--language", default=None,
              help="Language code (e.g., 'en_us'). Default: en_us. [API: language_code]")
@click.option("--language-detection", is_flag=True, default=False, show_default=True,
              help="Auto-detect language. [API: language_detection]")
# Advanced
@click.option("--prompt", default=None,
              help="Context prompt for transcription. [API: prompt]")
@click.option("--multichannel", is_flag=True, default=False, show_default=True,
              help="Enable multichannel transcription. [API: multichannel]")
@click.option("--redact-pii", is_flag=True, default=False, show_default=True,
              help="Redact PII from transcript. [API: redact_pii]")
@click.option("--filter-profanity", is_flag=True, default=False, show_default=True,
              help="Filter profanity. [API: filter_profanity]")
@click.option("--disfluencies", is_flag=True, default=False, show_default=True,
              help="Include filler words (um, uh). [API: disfluencies]")
@click.option("--keyterms", multiple=True,
              help="Domain-specific terms to boost (repeatable). [API: keyterms_prompt]")
@click.option("--no-punctuate", is_flag=True, default=False,
              help="Disable auto punctuation. [API: punctuate=false]")
@click.option("--no-format-text", is_flag=True, default=False,
              help="Disable text formatting. [API: format_text=false]")
# Meta
@click.option("--list-providers", is_flag=True, default=False,
              help="List available transcription providers and exit.")
@click.option("-v", "--verbose", is_flag=True, default=False,
              help="Show progress and timing info on stderr.")
@click.version_option(__version__, "-V", "--version")
def cli(
    audio,
    api_key,
    output_format,
    output,
    summary_mode,
    speaker_labels,
    speakers_expected,
    min_speakers,
    max_speakers,
    speaker_id_type,
    speaker_names,
    entities,
    sentiment,
    topics,
    auto_chapters,
    summarize,
    summary_model,
    summary_type,
    content_safety,
    language,
    language_detection,
    prompt,
    multichannel,
    redact_pii,
    filter_profanity,
    disfluencies,
    keyterms,
    no_punctuate,
    no_format_text,
    list_providers,
    verbose,
):
    """Transcribe audio files using AssemblyAI.

    \b
    AUDIO can be a local file path or a URL to an audio/video file.

    \b
    Examples:
        transcribe interview.mp3
        transcribe meeting.wav --speaker-labels
        transcribe call.m4a -f json | jq '.text'
        transcribe lecture.mp3 -f srt -o lecture.srt
        transcribe https://example.com/audio.mp3
    """
    # -- List providers mode --
    if list_providers:
        from transcribe_cli.providers import list_providers as _list

        providers = _list()
        if output_format == "json":
            click.echo(json.dumps(providers, indent=2))
        else:
            for p in providers:
                status = "+" if p["available"] else "-"
                click.echo(f"  {status} {p['name']}")
        return

    # -- Validate input --
    if audio is None:
        raise click.UsageError("Missing argument 'AUDIO'. Use -h for usage.")

    # Validate file exists (skip for URLs)
    if not _is_url(audio) and not Path(audio).exists():
        raise click.UsageError(f"File not found: {audio}")

    # Validate speaker options
    if speakers_expected and (min_speakers or max_speakers):
        raise click.UsageError(
            "Cannot use --speakers-expected with --min-speakers/--max-speakers. "
            "Use one or the other."
        )
    if bool(min_speakers) != bool(max_speakers):
        raise click.UsageError(
            "Must specify both --min-speakers and --max-speakers together."
        )

    # Validate API key
    if not api_key:
        raise click.UsageError(
            "AssemblyAI API key required.\n"
            "Set ASSEMBLYAI_API_KEY env var or pass --api-key <key>"
        )

    # -- Transcribe --
    try:
        from transcribe_cli.providers import get_provider

        if verbose:
            click.echo("Loading AssemblyAI provider...", err=True)

        provider = get_provider("assemblyai", api_key=api_key)

        if verbose:
            source = Path(audio).name if not _is_url(audio) else audio
            click.echo(f"Transcribing {source}...", err=True)

        result = provider.timed_transcribe(
            audio,
            language=language,
            speaker_labels=speaker_labels,
            speakers_expected=speakers_expected,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            speaker_id_type=speaker_id_type,
            speaker_names=list(speaker_names) if speaker_names else None,
            sentiment=sentiment,
            entities=entities,
            topics=topics,
            auto_chapters=auto_chapters,
            summarize=summarize,
            summary_model=summary_model,
            summary_type=summary_type,
            content_safety=content_safety,
            multichannel=multichannel,
            redact_pii=redact_pii,
            filter_profanity=filter_profanity,
            disfluencies=disfluencies,
            prompt=prompt,
            keyterms=list(keyterms) if keyterms else None,
            punctuate=not no_punctuate,
            format_text=not no_format_text,
            language_detection=language_detection,
        )

        if summary_mode:
            click.echo(json.dumps(result.to_summary(), indent=2))
        else:
            _emit_result(result, output_format, output, verbose)

    except (ValueError, RuntimeError) as e:
        if output_format == "json":
            click.echo(json.dumps({"error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.", err=True)
        sys.exit(130)


if __name__ == "__main__":
    cli()
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/transcribe_cli/cli.py tests/test_cli.py
git commit -m "feat: add Click CLI with full AssemblyAI flag support"
```

---

### Task 6: Integration test and install verification

**Files:**
- No new files

**Step 1: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Install locally and verify CLI works**

```bash
uv tool install . --force
transcribe --help
transcribe --version
transcribe --list-providers
```

Expected:
- `--help` shows all flags with defaults and API param references
- `--version` shows `0.1.0`
- `--list-providers` shows `assemblyai`

**Step 3: Verify error handling**

```bash
# No API key
unset ASSEMBLYAI_API_KEY
transcribe test.mp3
# Expected: error about missing API key

# Nonexistent file
ASSEMBLYAI_API_KEY=fake transcribe nonexistent.mp3
# Expected: error about file not found
```

**Step 4: Commit any fixes**

If any issues found, fix and commit:

```bash
git add -A
git commit -m "fix: address issues found during integration testing"
```

---

### Task 7: Clean up docs and old files

**Files:**
- Modify: `README.md` (rewrite for new CLI)
- Modify: `CLAUDE.md` (update for new structure)
- Delete: `MIGRATION.md` (no longer relevant)
- Delete: `.env.example` (API key is now via env var or flag, no .env loading)

**Step 1: Update README.md**

Rewrite to document the new CLI: installation via pip/uvx, usage examples, all flags, output formats. Reference the design doc for full details.

**Step 2: Update CLAUDE.md**

Update project structure, architecture description, setup instructions, and command-line options to match the new package layout.

**Step 3: Remove obsolete files**

```bash
rm -f MIGRATION.md .env.example
```

**Step 4: Commit**

```bash
git add -A
git commit -m "docs: update README and CLAUDE.md for v1 rewrite"
```

---

### Task 8: PyPI publishing setup

**Files:**
- Modify: `pyproject.toml` (add classifiers, URLs, license file)
- Create: `LICENSE`

**Step 1: Add MIT license**

Create `LICENSE` with standard MIT text.

**Step 2: Update pyproject.toml with PyPI metadata**

Add classifiers, project URLs, and keywords:

```toml
[project]
keywords = ["transcription", "audio", "assemblyai", "cli", "diarization"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Sound/Audio :: Speech",
]

[project.urls]
Homepage = "https://github.com/miguelarios/transcribe-cli"
Repository = "https://github.com/miguelarios/transcribe-cli"
Issues = "https://github.com/miguelarios/transcribe-cli/issues"
```

**Step 3: Verify build works**

```bash
uv run python -m build
```

Expected: Creates `dist/transcribe_cli-0.1.0.tar.gz` and `.whl` files.

**Step 4: Commit**

```bash
git add LICENSE pyproject.toml
git commit -m "build: add LICENSE and PyPI metadata for publishing"
```

**Step 5: Publish (with user confirmation)**

```bash
uv run python -m twine upload dist/*
```

Note: Requires PyPI credentials. Confirm with user before running.
