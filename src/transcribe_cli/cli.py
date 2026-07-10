"""transcribe CLI — modular transcription with pluggable providers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from transcribe_cli import __version__


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _run_doctor(api_key: str | None, fmt: str, offline: bool) -> int:
    """Diagnose setup/environment issues. Returns process exit code."""
    from transcribe_cli import __version__
    from transcribe_cli.providers import list_providers as _list

    checks: list[dict] = []

    def check(name: str, status: str, message: str):
        checks.append({"name": name, "status": status, "message": message})

    # API key present
    if api_key:
        check("api_key", "pass", "API key found")
    else:
        check("api_key", "fail",
              "No API key. Set ASSEMBLYAI_API_KEY env var or pass --api-key.")

    # SDK installed
    try:
        import assemblyai

        sdk_version = getattr(assemblyai, "__version__", "unknown")
        check("sdk", "pass", f"assemblyai SDK {sdk_version} installed")
    except ImportError:
        check("sdk", "fail", "assemblyai SDK not installed")

    # Providers registered and available
    available = [p["name"] for p in _list() if p["available"]]
    if available:
        check("providers", "pass", f"available: {', '.join(available)}")
    else:
        check("providers", "fail", "no providers available")

    # Network checks
    if offline:
        check("key_valid", "skip", "skipped (--offline)")
        check("update", "skip", "skipped (--offline)")
    else:
        import httpx

        if api_key:
            try:
                resp = httpx.get(
                    "https://api.assemblyai.com/v2/transcript",
                    params={"limit": 1},
                    headers={"authorization": api_key},
                    timeout=10,
                )
                if resp.status_code == 200:
                    check("key_valid", "pass", "API key accepted by AssemblyAI")
                elif resp.status_code == 401:
                    check("key_valid", "fail", "API key rejected by AssemblyAI (401)")
                else:
                    check("key_valid", "warn",
                          f"unexpected response from AssemblyAI: {resp.status_code}")
            except Exception as e:  # network unreachable, DNS, timeout, ...
                check("key_valid", "warn", f"could not reach AssemblyAI: {e}")
        else:
            check("key_valid", "skip", "skipped (no API key)")

        try:
            resp = httpx.get("https://pypi.org/pypi/transcriber-cli/json", timeout=10)
            latest = resp.json()["info"]["version"]
            if str(latest) == __version__:
                check("update", "pass", f"up to date ({__version__})")
            else:
                check("update", "warn", f"update available: {__version__} -> {latest}")
        except Exception as e:
            check("update", "warn", f"could not check PyPI for updates: {e}")

    summary = {
        "passed": sum(1 for c in checks if c["status"] == "pass"),
        "warned": sum(1 for c in checks if c["status"] == "warn"),
        "failed": sum(1 for c in checks if c["status"] == "fail"),
        "skipped": sum(1 for c in checks if c["status"] == "skip"),
    }
    ok = summary["failed"] == 0

    if fmt == "json":
        click.echo(json.dumps(
            {"ok": ok, "summary": summary, "checks": checks}, indent=2))
    else:
        for c in checks:
            click.echo(f"[{c['status']:>4}] {c['name']}: {c['message']}")
        click.echo(
            f"\n{summary['passed']} passed, {summary['warned']} warned, "
            f"{summary['failed']} failed, {summary['skipped']} skipped"
        )
    return 0 if ok else 1


AGENT_EPILOG = """\b
Note for AI/LLM agents:
  Use -f json for structured output (errors also emit JSON on stdout), or
  -f ndjson for one JSON object per segment (stream/grep-friendly).
  Use --summary to keep context small: prints metadata JSON (word/token counts,
  speakers, duration) and writes the full transcript to a file instead of stdout.
  Pair --summary with -o <path> to control where the transcript lands.
  Use --dry-run to validate flags and preview the resolved provider config
  as JSON without an API key, network, or credits.
  Use --doctor [-f json] [--offline] to diagnose setup (API key, SDK, network).
  Use --progress-jsonl [path] for JSONL progress events (long jobs are not hung).
  Transcript goes to stdout; progress/timing (-v) goes to stderr.
  Exit codes: 0 success, 1 error, 130 interrupted.
  Set ASSEMBLYAI_API_KEY env var instead of passing --api-key.
  Use --list-providers -f json to discover available providers.
"""


def _jsonable(obj):
    """JSON serializer for SDK objects (enums, pydantic models)."""
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


def _format_content(result, fmt: str) -> str:
    """Render a TranscriptionResult in the requested output format."""
    if fmt == "json":
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    if fmt == "ndjson":
        return result.to_ndjson()
    if fmt == "srt":
        return result.to_srt()
    if fmt == "vtt":
        return result.to_vtt()
    return result.to_text()


def _emit_result(result, fmt: str, output: str | None, verbose: bool):
    """Format and write the transcription result."""
    content = _format_content(result, fmt)

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


@click.command(context_settings={"help_option_names": ["-h", "--help"]},
               epilog=AGENT_EPILOG)
@click.argument("audio", required=False)
@click.option("--api-key", default=None, envvar="ASSEMBLYAI_API_KEY",
              help="AssemblyAI API key.  [env: ASSEMBLYAI_API_KEY]")
@click.option("-f", "--format", "output_format",
              type=click.Choice(["text", "json", "ndjson", "srt", "vtt"]),
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
@click.option("--channel-names", multiple=True,
              help="Map channel numbers to names (repeatable, order = channel number). "
                   "E.g., --channel-names Miguel --channel-names Justin")
@click.option("--redact-pii", is_flag=True, default=False, show_default=True,
              help="Redact PII from transcript. [API: redact_pii]")
@click.option("--redact-policies", multiple=True,
              help="PII policies to redact (repeatable, use with --redact-pii). "
                   "E.g., person_name, phone_number, email_address, location. "
                   "Defaults to a common-PII set. [API: redact_pii_policies]")
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
@click.option("--progress-jsonl", "progress_jsonl",
              is_flag=False, flag_value="-", default=None,
              help="Emit progress events as JSONL. Bare flag writes to stderr; "
                   "pass a path to write to a file instead.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Print the resolved provider config as JSON and exit without "
                   "transcribing. No API key or network needed.")
@click.option("--doctor", is_flag=True, default=False,
              help="Diagnose setup issues (API key, SDK, connectivity) and exit. "
                   "Combine with -f json for structured output.")
@click.option("--offline", is_flag=True, default=False,
              help="Skip network checks (use with --doctor).")
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
    channel_names,
    redact_pii,
    redact_policies,
    filter_profanity,
    disfluencies,
    keyterms,
    no_punctuate,
    no_format_text,
    progress_jsonl,
    dry_run,
    doctor,
    offline,
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
    # -- Doctor mode --
    if doctor:
        sys.exit(_run_doctor(api_key, output_format, offline))

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
        # Bare invocation: show full help (with agent note) instead of an error
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit(0)

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

    # Validate channel-names for multichannel-only mode (no speaker diarization)
    if multichannel and not speaker_labels and not speakers_expected:
        if channel_names and len(channel_names) != 2:
            raise click.UsageError(
                "--multichannel expects exactly 2 channel names (left and right). "
                f"Got {len(channel_names)}."
            )
        if not channel_names:
            channel_names = ("Me", "Them")

    # Validate file exists (skip for URLs)
    if not _is_url(audio) and not Path(audio).exists():
        raise click.UsageError(f"File not found: {audio}")

    options = {
        "language": language,
        "speaker_labels": speaker_labels,
        "speakers_expected": speakers_expected,
        "min_speakers": min_speakers,
        "max_speakers": max_speakers,
        "speaker_id_type": speaker_id_type,
        "speaker_names": list(speaker_names) if speaker_names else None,
        "sentiment": sentiment,
        "entities": entities,
        "topics": topics,
        "auto_chapters": auto_chapters,
        "summarize": summarize,
        "summary_model": summary_model,
        "summary_type": summary_type,
        "content_safety": content_safety,
        "multichannel": multichannel,
        "channel_names": list(channel_names) if channel_names else None,
        "redact_pii": redact_pii,
        "redact_policies": list(redact_policies) if redact_policies else None,
        "filter_profanity": filter_profanity,
        "disfluencies": disfluencies,
        "prompt": prompt,
        "keyterms": list(keyterms) if keyterms else None,
        "punctuate": not no_punctuate,
        "format_text": not no_format_text,
        "language_detection": language_detection,
    }

    # -- Dry-run mode: resolve and print the config, no API key or network --
    if dry_run:
        from transcribe_cli.providers.assemblyai import AssemblyAIProvider

        config = AssemblyAIProvider.build_config_kwargs(**options)
        click.echo(json.dumps(
            {"provider": "assemblyai", "audio": audio, "config": config},
            indent=2, ensure_ascii=False, default=_jsonable,
        ))
        return

    # Progress events as JSONL to stderr ("-") or a file
    if progress_jsonl:
        def _emit_progress(event: dict):
            line = json.dumps(event, ensure_ascii=False)
            if progress_jsonl == "-":
                click.echo(line, err=True)
            else:
                with open(progress_jsonl, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

        options["progress_callback"] = _emit_progress

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

        result = provider.timed_transcribe(audio, **options)

        if summary_mode:
            # Format the transcript content for the output file
            content = _format_content(result, output_format) if output else None
            click.echo(json.dumps(result.to_summary(output_path=output, output_content=content), indent=2))
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
