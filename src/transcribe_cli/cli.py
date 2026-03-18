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

    # Validate speaker options (before file check so tests can use fake paths)
    if speakers_expected and (min_speakers or max_speakers):
        raise click.UsageError(
            "Cannot use --speakers-expected with --min-speakers/--max-speakers. "
            "Use one or the other."
        )
    if bool(min_speakers) != bool(max_speakers):
        raise click.UsageError(
            "Must specify both --min-speakers and --max-speakers together."
        )

    # Validate file exists (skip for URLs)
    if not _is_url(audio) and not Path(audio).exists():
        raise click.UsageError(f"File not found: {audio}")

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
            click.echo(json.dumps(result.to_summary(output_path=output), indent=2))
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
