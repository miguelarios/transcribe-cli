#!/usr/bin/env python3
"""
Enhanced Audio Transcription and Speaker Diarization Tool
Uses AssemblyAI API for transcription with speaker labels and sentiment analysis.
"""

import assemblyai as aai
import sys
import os
import json
import argparse
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import timedelta


def load_env_file():
    """Load environment variables from .env file if it exists.

    Searches for .env in the following order:
    1. Current working directory
    2. Script's directory (for development)
    3. User's home directory (~/.transcribe.env)
    """
    # Check current directory first
    env_paths = [
        Path.cwd() / '.env',
        Path(__file__).parent / '.env',
        Path.home() / '.transcribe.env'
    ]

    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Only set if not already in environment
                        if key.strip() not in os.environ:
                            os.environ[key.strip()] = value.strip()
            break  # Use first .env file found


def get_api_key() -> str:
    """Get API key from environment variable or .env file."""
    load_env_file()

    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("Error: ASSEMBLYAI_API_KEY not found")
        print("Create a .env file with: ASSEMBLYAI_API_KEY=your_api_key_here")
        print("Or set it with: export ASSEMBLYAI_API_KEY='your_api_key_here'")
        sys.exit(1)
    return api_key


def validate_file(file_path: str) -> Path:
    """Validate that the file exists and is accessible."""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    if not path.is_file():
        print(f"Error: Path is not a file: {file_path}")
        sys.exit(1)

    # Check file size
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"File: {path.name}")
    print(f"Size: {size_mb:.2f} MB")

    return path


def format_timestamp(milliseconds: int) -> str:
    """Convert milliseconds to SRT timestamp format."""
    td = timedelta(milliseconds=milliseconds)
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    ms = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def save_txt_transcript(transcript: aai.Transcript, output_file: Path, include_timestamps: bool = False) -> None:
    """Save transcript in text format with speaker labels."""
    with open(output_file, 'w') as f:
        for utterance in transcript.utterances:
            if include_timestamps:
                start_time = format_timestamp(utterance.start)
                end_time = format_timestamp(utterance.end)
                f.write(f"[{start_time} --> {end_time}] Speaker {utterance.speaker}: {utterance.text}\n\n")
            else:
                f.write(f"Speaker {utterance.speaker}: {utterance.text}\n\n")


def save_srt_transcript(transcript: aai.Transcript, output_file: Path) -> None:
    """Save transcript in SRT subtitle format."""
    with open(output_file, 'w') as f:
        for i, utterance in enumerate(transcript.utterances, 1):
            start_time = format_timestamp(utterance.start)
            end_time = format_timestamp(utterance.end)
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"Speaker {utterance.speaker}: {utterance.text}\n\n")


def save_json_transcript(transcript: aai.Transcript, output_file: Path, include_metadata: bool = False) -> None:
    """Save transcript in JSON format with optional metadata."""
    data: Dict[str, Any] = {
        "transcript_id": transcript.id,
        "utterances": []
    }

    # Add metadata if requested
    if include_metadata:
        metadata = {
            "audio_duration": transcript.audio_duration,
            "confidence": transcript.confidence,
            "status": transcript.status.value
        }

        # Add optional attributes if they exist
        if hasattr(transcript, 'language_code') and transcript.language_code:
            metadata["language_code"] = transcript.language_code

        data["metadata"] = metadata

        # Add speaker statistics
        speaker_stats: Dict[str, Dict[str, Any]] = {}
        for utterance in transcript.utterances:
            speaker = utterance.speaker
            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    "word_count": 0,
                    "utterance_count": 0,
                    "total_time_ms": 0
                }
            speaker_stats[speaker]["word_count"] += len(utterance.text.split())
            speaker_stats[speaker]["utterance_count"] += 1
            speaker_stats[speaker]["total_time_ms"] += (utterance.end - utterance.start)

        data["speaker_statistics"] = speaker_stats

    # Add utterances with sentiment if available
    for utterance in transcript.utterances:
        utterance_data = {
            "speaker": utterance.speaker,
            "text": utterance.text,
            "start": utterance.start,
            "end": utterance.end,
            "confidence": utterance.confidence
        }

        # Include sentiment if available
        if hasattr(utterance, 'sentiment') and utterance.sentiment:
            utterance_data["sentiment"] = utterance.sentiment.value

        data["utterances"].append(utterance_data)

    # Add entities if available
    if hasattr(transcript, 'entities') and transcript.entities:
        data["entities"] = []
        for entity in transcript.entities:
            entity_data = {
                "text": entity.text,
                "type": entity.entity_type.value,
                "start": entity.start,
                "end": entity.end
            }
            data["entities"].append(entity_data)

    # Add summary if available
    if hasattr(transcript, 'summary') and transcript.summary:
        data["summary"] = transcript.summary

    # Add chapters if available
    if hasattr(transcript, 'chapters') and transcript.chapters:
        data["chapters"] = []
        for chapter in transcript.chapters:
            chapter_data = {
                "headline": chapter.headline,
                "summary": chapter.summary,
                "gist": chapter.gist,
                "start": chapter.start,
                "end": chapter.end
            }
            data["chapters"].append(chapter_data)

    # Add topic detection results if available
    if hasattr(transcript, 'iab_categories') and transcript.iab_categories:
        data["topics"] = {
            "summary": {},
            "results": []
        }

        # Add overall topic summary
        if hasattr(transcript.iab_categories, 'summary') and transcript.iab_categories.summary:
            for topic, relevance in transcript.iab_categories.summary.items():
                data["topics"]["summary"][topic] = relevance

        # Add detailed topic results
        if hasattr(transcript.iab_categories, 'results') and transcript.iab_categories.results:
            for result in transcript.iab_categories.results:
                result_data = {
                    "text": result.text,
                    "timestamp": {
                        "start": result.timestamp.start,
                        "end": result.timestamp.end
                    },
                    "labels": []
                }
                for label in result.labels:
                    result_data["labels"].append({
                        "label": label.label,
                        "relevance": label.relevance
                    })
                data["topics"]["results"].append(result_data)

    # Add detected language if available
    if hasattr(transcript, 'language_code') and transcript.language_code:
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["detected_language"] = transcript.language_code
        if hasattr(transcript, 'language_confidence'):
            data["metadata"]["language_confidence"] = transcript.language_confidence

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced audio transcription with speaker diarization and sentiment analysis"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="transcribe 0.1.0"
    )
    parser.add_argument(
        "audio_file",
        help="Path to the audio file to transcribe"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["txt", "srt"],
        default="txt",
        help="Human-readable format to create alongside JSON (default: txt). JSON is always created unless --json-only is specified."
    )
    parser.add_argument(
        "-t", "--timestamps",
        action="store_true",
        help="Include timestamps in text output"
    )
    parser.add_argument(
        "-m", "--metadata",
        action="store_true",
        help="Include metadata and statistics in JSON output"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only create JSON output (skip human-readable format)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Base output file path without extension (default: same directory as input)"
    )
    parser.add_argument(
        "--no-speaker-labels",
        action="store_true",
        help="Disable speaker labels"
    )
    parser.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Disable sentiment analysis"
    )
    parser.add_argument(
        "--no-entities",
        action="store_true",
        help="Disable entity detection"
    )
    parser.add_argument(
        "--speakers-expected",
        type=int,
        help="Exact number of speakers expected (use when certain)"
    )
    parser.add_argument(
        "--min-speakers",
        type=int,
        help="Minimum number of speakers expected (use with --max-speakers for range)"
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        help="Maximum number of speakers expected (use with --min-speakers for range)"
    )

    # Language detection options
    parser.add_argument(
        "--language-detection",
        action="store_true",
        help="Enable automatic language detection (auto-detects the language)"
    )
    parser.add_argument(
        "--language-code",
        type=str,
        help="Manually specify language code (e.g., 'en', 'es', 'fr'). Use when you know the language."
    )

    # Content understanding features
    parser.add_argument(
        "--auto-chapters",
        action="store_true",
        help="Generate automatic chapters with headlines and summaries (cannot be used with --summarization)"
    )
    parser.add_argument(
        "--summarization",
        action="store_true",
        help="Generate a summary of the entire transcript (cannot be used with --auto-chapters)"
    )
    parser.add_argument(
        "--summary-model",
        choices=["informative", "conversational", "catchy"],
        default="informative",
        help="Summary model type (default: informative). Only used with --summarization."
    )
    parser.add_argument(
        "--summary-type",
        choices=["bullets", "paragraph", "headline", "gist"],
        default="bullets",
        help="Summary format type (default: bullets). Only used with --summarization."
    )
    parser.add_argument(
        "--topics",
        action="store_true",
        help="Enable topic detection using IAB taxonomy"
    )

    # Speaker identification (requires speaker labels)
    parser.add_argument(
        "--speaker-names",
        type=str,
        nargs="+",
        help="List of speaker names for identification (e.g., --speaker-names 'John Smith' 'Jane Doe')"
    )

    args = parser.parse_args()

    # Validate speaker arguments
    if args.speakers_expected and (args.min_speakers or args.max_speakers):
        print("Error: Cannot use --speakers-expected with --min-speakers/--max-speakers")
        print("Use either:")
        print("  --speakers-expected N  (when you know exactly)")
        print("  --min-speakers N --max-speakers M  (for a range)")
        sys.exit(1)
    
    if (args.min_speakers and not args.max_speakers) or (args.max_speakers and not args.min_speakers):
        print("Error: Must specify both --min-speakers and --max-speakers for a range")
        sys.exit(1)

    # Validate language detection arguments
    if args.language_detection and args.language_code:
        print("Error: Cannot use both --language-detection and --language-code")
        print("Use either:")
        print("  --language-detection  (auto-detect language)")
        print("  --language-code CODE  (manually specify language)")
        sys.exit(1)

    # Validate summarization/chapters arguments
    if args.auto_chapters and args.summarization:
        print("Error: Cannot use both --auto-chapters and --summarization")
        print("These features are mutually exclusive. Choose one:")
        print("  --auto-chapters     (generate chapters with headlines)")
        print("  --summarization     (generate overall summary)")
        sys.exit(1)

    # Validate speaker identification
    if args.speaker_names and args.no_speaker_labels:
        print("Error: --speaker-names requires speaker labels to be enabled")
        print("Remove --no-speaker-labels to use speaker identification")
        sys.exit(1)

    # Get API key from environment
    api_key = get_api_key()
    aai.settings.api_key = api_key

    # Validate input file
    audio_path = validate_file(args.audio_file)

    # Configure transcription
    config_kwargs = {
        'speaker_labels': not args.no_speaker_labels,
        'sentiment_analysis': not args.no_sentiment,
        'entity_detection': not args.no_entities
    }

    # Add speaker configuration if provided
    if args.speakers_expected:
        config_kwargs['speakers_expected'] = args.speakers_expected
    elif args.min_speakers and args.max_speakers:
        config_kwargs['speaker_options'] = aai.SpeakerOptions(
            min_speakers_expected=args.min_speakers,
            max_speakers_expected=args.max_speakers
        )

    # Add language configuration
    if args.language_detection:
        config_kwargs['language_detection'] = True
    elif args.language_code:
        config_kwargs['language_code'] = args.language_code

    # Add content understanding features
    if args.auto_chapters:
        config_kwargs['auto_chapters'] = True

    if args.summarization:
        config_kwargs['summarization'] = True
        # Map string choices to AssemblyAI enum types
        model_map = {
            'informative': aai.SummarizationModel.informative,
            'conversational': aai.SummarizationModel.conversational,
            'catchy': aai.SummarizationModel.catchy
        }
        type_map = {
            'bullets': aai.SummarizationType.bullets,
            'paragraph': aai.SummarizationType.paragraph,
            'headline': aai.SummarizationType.headline,
            'gist': aai.SummarizationType.gist
        }
        config_kwargs['summary_model'] = model_map[args.summary_model]
        config_kwargs['summary_type'] = type_map[args.summary_type]

    if args.topics:
        config_kwargs['iab_categories'] = True

    # Add speaker identification if provided
    if args.speaker_names:
        config_kwargs['speech_model'] = aai.SpeechModel.best  # Required for speaker identification
        # Note: Speaker identification configuration is more complex and may require custom API calls
        # For now, we'll just enable the best speech model

    config = aai.TranscriptionConfig(**config_kwargs)

    # Determine output files (base path without extension)
    if args.output:
        base_output_path = Path(args.output).expanduser().resolve()
    else:
        base_name = audio_path.stem
        base_output_path = audio_path.parent / f"{base_name}_transcript"

    # Create file paths for JSON and human-readable format
    json_output_file = base_output_path.parent / f"{base_output_path.stem}.json"
    readable_output_file = base_output_path.parent / f"{base_output_path.stem}.{args.format}"

    print(f"\nTranscribing audio file...")

    # Speaker configuration
    print(f"Speaker labels: {'enabled' if not args.no_speaker_labels else 'disabled'}")
    if not args.no_speaker_labels:
        if args.speakers_expected:
            print(f"  Expected speakers: exactly {args.speakers_expected}")
        elif args.min_speakers and args.max_speakers:
            print(f"  Expected speakers: {args.min_speakers}-{args.max_speakers} (range)")
        else:
            print(f"  Expected speakers: auto-detect (1-10 default range)")
        if args.speaker_names:
            print(f"  Speaker identification: {', '.join(args.speaker_names)}")

    # Language configuration
    if args.language_detection:
        print(f"Language: auto-detect")
    elif args.language_code:
        print(f"Language: {args.language_code}")

    # Analysis features
    print(f"Sentiment analysis: {'enabled' if not args.no_sentiment else 'disabled'}")
    print(f"Entity detection: {'enabled' if not args.no_entities else 'disabled'}")
    print(f"Topic detection: {'enabled' if args.topics else 'disabled'}")

    # Content features
    if args.auto_chapters:
        print(f"Auto chapters: enabled")
    if args.summarization:
        print(f"Summarization: enabled ({args.summary_model}, {args.summary_type})")

    # Output format
    if args.json_only:
        print(f"Output format: JSON only")
    else:
        print(f"Output formats: JSON + {args.format.upper()}")

    # Transcribe with progress updates
    transcriber = aai.Transcriber(config=config)

    print("\nUploading and processing...")
    transcript = transcriber.transcribe(str(audio_path))

    # Wait for completion with status updates
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_idx = 0
    last_status = None

    while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
        if transcript.status != last_status:
            if last_status is not None:
                print()  # New line after spinner
            print(f"Status: {transcript.status.value}", end='', flush=True)
            last_status = transcript.status
        else:
            print(f"\r{spinner[spinner_idx % len(spinner)]} Status: {transcript.status.value}", end='', flush=True)
            spinner_idx += 1

        time.sleep(0.3)
        transcript = transcriber.get_transcript(transcript.id)

    if transcript.status == aai.TranscriptStatus.error:
        print(f"\n\nTranscription failed: {transcript.error}")
        sys.exit(1)

    print(f"\r✓ Status: completed          ")

    # Always save JSON file (with metadata enabled by default for complete data)
    save_json_transcript(transcript, json_output_file, args.metadata or True)

    saved_files = [str(json_output_file)]

    # Save human-readable format unless --json-only is specified
    if not args.json_only:
        if args.format == "txt":
            save_txt_transcript(transcript, readable_output_file, args.timestamps)
        elif args.format == "srt":
            save_srt_transcript(transcript, readable_output_file)
        saved_files.append(str(readable_output_file))

    # Report saved files
    print(f"\n✓ Transcript saved to:")
    for file_path in saved_files:
        print(f"  - {file_path}")

    # Show quick summary
    if transcript.utterances:
        num_speakers = len(set(u.speaker for u in transcript.utterances))
        print(f"\nSummary:")
        print(f"  Duration: {transcript.audio_duration / 1000:.1f} seconds")
        print(f"  Speakers detected: {num_speakers}")
        print(f"  Utterances: {len(transcript.utterances)}")
        if transcript.confidence:
            print(f"  Confidence: {transcript.confidence:.2%}")

        # Language detection results
        if hasattr(transcript, 'language_code') and transcript.language_code:
            lang_info = f"  Language: {transcript.language_code}"
            if hasattr(transcript, 'language_confidence') and transcript.language_confidence:
                lang_info += f" (confidence: {transcript.language_confidence:.2%})"
            print(lang_info)

        # Analysis results
        if hasattr(transcript, 'entities') and transcript.entities:
            print(f"  Entities detected: {len(transcript.entities)}")

        if hasattr(transcript, 'chapters') and transcript.chapters:
            print(f"  Chapters: {len(transcript.chapters)}")

        if hasattr(transcript, 'iab_categories') and transcript.iab_categories:
            if hasattr(transcript.iab_categories, 'summary') and transcript.iab_categories.summary:
                num_topics = len(transcript.iab_categories.summary)
                print(f"  Topics detected: {num_topics}")

        if hasattr(transcript, 'summary') and transcript.summary:
            print(f"  Summary: generated ({args.summary_type} format)")


if __name__ == "__main__":
    main()
