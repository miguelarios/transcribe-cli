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
                label = _fmt_speaker(seg.speaker)
                lines.append(f"[{ts}] {label}: {seg.text.strip()}")
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
                text = f"{_fmt_speaker(seg.speaker)}: {text}"
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
                text = f"{_fmt_speaker(seg.speaker)}: {text}"
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def to_summary(self, output_path: str | None = None, output_content: str | None = None) -> dict:
        """Generate agent-friendly summary metadata, save full transcript to file.

        If output_path is provided, the transcript is written there using
        output_content (the formatted transcript). Otherwise, the full JSON
        payload is saved to a temp file.
        """
        if output_path:
            out_file = Path(output_path)
            out_file.write_text(output_content or self.to_text(), encoding="utf-8")
        else:
            tmp_dir = Path(tempfile.gettempdir()) / "transcribe-cli"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            out_file = tmp_dir / f"{self.metadata.get('id', 'transcript')}.json"
            out_file.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

        word_count = len(self.text.split())
        speakers = {s.speaker for s in self.segments if s.speaker}

        return {
            "file": str(out_file),
            "word_count": word_count,
            "token_count": int(word_count * 1.3),  # rough estimate
            "speaker_count": len(speakers),
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "provider": self.provider,
        }


def _fmt_speaker(label: str) -> str:
    """Format a speaker label — prefix short diarization IDs with 'Speaker'."""
    if len(label) <= 2 and label.isalpha():
        return f"Speaker {label}"
    return label


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
