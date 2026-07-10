"""AssemblyAI provider — cloud transcription with full feature support."""

from __future__ import annotations

import os
import time
from pathlib import Path

import assemblyai as aai

from transcribe_cli.base import Segment, TranscriptionProvider, TranscriptionResult
from transcribe_cli.providers import register

# Default PII policies when --redact-pii is enabled without explicit policies.
# The API requires redact_pii_policies whenever redact_pii is true; this set
# mirrors AssemblyAI's contact-center example.
DEFAULT_REDACT_POLICIES = [
    "person_name",
    "phone_number",
    "email_address",
    "account_number",
    "us_social_security_number",
    "credit_card_number",
    "credit_card_cvv",
    "credit_card_expiration",
    "date_of_birth",
]


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

    @classmethod
    def build_config_kwargs(
        cls,
        *,
        language: str | None = None,
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
        redact_policies: list[str] | None = None,
        filter_profanity: bool = False,
        disfluencies: bool = False,
        prompt: str | None = None,
        keyterms: list[str] | None = None,
        punctuate: bool = True,
        format_text: bool = True,
        language_detection: bool = False,
        **kwargs,
    ) -> dict:
        """Resolve CLI options into AssemblyAI TranscriptionConfig kwargs.

        Classmethod so callers (e.g. --dry-run) can resolve the config
        without an API key. Unknown kwargs are ignored.
        """
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

        if redact_pii:
            # The API rejects redact_pii=true without policies
            config_kwargs["redact_pii_policies"] = redact_policies or DEFAULT_REDACT_POLICIES

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

        # Speech understanding: speaker identification.
        # The API shape requires a "request" wrapper and speaker_labels enabled.
        if speaker_id_type and speaker_names:
            config_kwargs["speaker_labels"] = True
            config_kwargs["speech_understanding"] = {
                "request": {
                    "speaker_identification": {
                        "speaker_type": speaker_id_type,
                        "known_values": speaker_names,
                    }
                }
            }

        return config_kwargs

    _POLL_INTERVAL_SECONDS = 3.0

    @staticmethod
    def _status_str(status) -> str:
        return getattr(status, "value", None) or str(status)

    def _transcribe_with_progress(self, transcriber, audio_str: str, config, callback):
        """Submit and poll, emitting progress events via callback."""
        if not audio_str.startswith(("http://", "https://")):
            callback({"event": "uploading", "file": audio_str})
        transcript = transcriber.submit(audio_str, config=config)
        callback({
            "event": "submitted",
            "id": transcript.id,
            "status": self._status_str(transcript.status),
        })

        terminal = (aai.TranscriptStatus.completed, aai.TranscriptStatus.error)
        last_status = transcript.status
        while transcript.status not in terminal:
            time.sleep(self._POLL_INTERVAL_SECONDS)
            transcript = aai.Transcript.get_by_id(transcript.id)
            if transcript.status != last_status and transcript.status not in terminal:
                callback({"event": "status", "status": self._status_str(transcript.status)})
                last_status = transcript.status

        if transcript.status == aai.TranscriptStatus.error:
            callback({"event": "error", "error": str(transcript.error)})
        else:
            callback({"event": "completed", "id": transcript.id})
        return transcript

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        timestamps: bool = True,
        **options,
    ) -> TranscriptionResult:
        aai.settings.api_key = self.api_key

        progress_callback = options.pop("progress_callback", None)
        config_kwargs = self.build_config_kwargs(**options)
        speaker_labels = config_kwargs["speaker_labels"]
        multichannel = config_kwargs["multichannel"]
        sentiment = config_kwargs["sentiment_analysis"]
        entities = config_kwargs["entity_detection"]
        topics = config_kwargs["iab_categories"]
        auto_chapters = config_kwargs["auto_chapters"]
        content_safety = config_kwargs["content_safety"]
        summarize = config_kwargs.get("summarization", False)

        config = aai.TranscriptionConfig(**config_kwargs)
        transcriber = aai.Transcriber()

        audio_str = str(audio_path)
        if progress_callback:
            transcript = self._transcribe_with_progress(
                transcriber, audio_str, config, progress_callback
            )
        else:
            transcript = transcriber.transcribe(audio_str, config=config)

        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(f"AssemblyAI error: {transcript.error}")

        # Build segments from utterances (if speaker_labels or multichannel) or sentences
        channel_names = options.get("channel_names")
        segments = []
        if timestamps and (speaker_labels or multichannel) and transcript.utterances:
            for utt in transcript.utterances:
                # Determine speaker label: channel name > channel number > speaker ID
                if multichannel and getattr(utt, "channel", None) is not None:
                    # API types channel as string|null, 1-indexed ("1", "2", ...)
                    ch = str(utt.channel)
                    try:
                        idx = int(ch)
                    except ValueError:
                        idx = None
                    if channel_names and idx is not None and 1 <= idx <= len(channel_names):
                        speaker = channel_names[idx - 1]
                    else:
                        speaker = f"Channel {ch}"
                else:
                    speaker = utt.speaker
                seg = Segment(
                    text=utt.text,
                    start=utt.start / 1000.0,
                    end=utt.end / 1000.0,
                    speaker=speaker,
                    confidence=utt.confidence,
                )
                if sentiment and hasattr(utt, "sentiment") and utt.sentiment:
                    seg.sentiment = utt.sentiment.value
                segments.append(seg)
        elif timestamps:
            for sent in transcript.get_sentences():
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
        # assemblyai is a core dependency, not an optional extra
        return ""
