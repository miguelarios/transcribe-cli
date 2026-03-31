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

        # Build segments from utterances (if speaker_labels or multichannel) or sentences
        channel_names = kwargs.get("channel_names")
        segments = []
        if timestamps and (speaker_labels or multichannel) and transcript.utterances:
            for utt in transcript.utterances:
                # Determine speaker label: channel name > channel number > speaker ID
                if multichannel and hasattr(utt, "channel") and utt.channel is not None:
                    ch = utt.channel
                    if channel_names and len(channel_names) >= int(ch):
                        speaker = channel_names[int(ch) - 1]
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
        return "assemblyai"
