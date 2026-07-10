# transcribe-cli

A modular audio transcription CLI with pluggable providers. Agent-friendly.

Currently supports [AssemblyAI](https://www.assemblyai.com) with speaker diarization, sentiment analysis, entity detection, auto chapters, summarization, topic detection, and more.

## Installation

```bash
# With uv (recommended)
uv tool install transcriber-cli

# With pip
pip install transcriber-cli

# Run without installing
uvx --from transcriber-cli transcribe audio.mp3
```

Or install from source:

```bash
git clone https://github.com/miguelarios/transcribe-cli.git
cd transcribe-cli
uv tool install .
```

## Setup

Get an API key from the [AssemblyAI Dashboard](https://www.assemblyai.com/dashboard) and set it:

```bash
export ASSEMBLYAI_API_KEY='your_key_here'
```

Or pass it directly: `transcribe --api-key <key> audio.mp3`

## Usage

```bash
# Basic transcription (text output to stdout)
transcribe interview.mp3

# JSON output
transcribe interview.mp3 -f json

# With speaker diarization
transcribe meeting.wav --speaker-labels

# SRT subtitles to file
transcribe lecture.mp3 -f srt -o lecture.srt

# Full-featured transcription
transcribe call.m4a --speaker-labels --entities --sentiment -f json

# Pipe JSON to jq
transcribe interview.mp3 -f json | jq '.segments[] | .speaker, .text'

# Agent-friendly summary (saves full transcript to temp file)
transcribe meeting.mp3 --summary

# Transcribe from URL
transcribe https://example.com/audio.mp3
```

## Output Formats

| Format | Flag | Description |
|--------|------|-------------|
| text | `-f text` (default) | Timestamped text with optional speaker labels |
| json | `-f json` | Full structured data (segments, metadata, entities) |
| ndjson | `-f ndjson` | One JSON object per segment line (stream/grep-friendly) |
| srt | `-f srt` | SRT subtitle format |
| vtt | `-f vtt` | WebVTT subtitle format |

## All Options

Run `transcribe -h` for the full list. Key options:

### Speaker/Diarization
- `--speaker-labels` — Enable speaker diarization
- `--speakers-expected N` — Exact speaker count
- `--min-speakers N --max-speakers M` — Speaker range
- `--speaker-id-type [role|name]` — Speaker identification mode
- `--speaker-names NAME` — Known speaker names (repeatable)

### Analysis
- `--entities` — Detect names, locations, dates, etc.
- `--sentiment` — Sentiment analysis per utterance
- `--topics` — IAB topic detection
- `--auto-chapters` — Generate chapters with headlines
- `--summarize` — Generate transcript summary
- `--content-safety` — Content moderation

### Language
- `--language CODE` — Language code (e.g., `en_us`)
- `--language-detection` — Auto-detect language

### Advanced
- `--prompt TEXT` — Context prompt for transcription
- `--keyterms TERM` — Domain-specific terms to boost (repeatable)
- `--multichannel` — Multichannel transcription
- `--redact-pii` — Redact personally identifiable information
- `--redact-policies POLICY` — PII policies to redact (repeatable; defaults to a common-PII set)
- `--filter-profanity` — Filter profanity
- `--disfluencies` — Include filler words (um, uh)

### Output
- `-f, --format [text|json|ndjson|srt|vtt]` — Output format
- `-o, --output PATH` — Write to file instead of stdout
- `--summary` — Output metadata summary, save full transcript to temp file
- `--progress-jsonl [PATH]` — Emit JSONL progress events to stderr (bare) or a file
- `-v, --verbose` — Show progress and timing on stderr

### Meta
- `--dry-run` — Print the resolved provider config as JSON; no API key or network needed
- `--doctor` — Diagnose setup issues (`-f json` for structured output, `--offline` to skip network checks)
- `--list-providers` — List available transcription providers
- `--api-key KEY` — AssemblyAI API key
- `-V, --version` — Show version
- `-h, --help` — Show help

## Agent-Friendly Design

Built to be driven by AI agents as well as humans:

```bash
# Validate a flag combo without spending credits
transcribe call.mp3 --speaker-labels --redact-pii --dry-run

# Self-diagnose setup problems, machine-readable
transcribe --doctor -f json

# Long job? Progress events prove it isn't hung
transcribe podcast.mp3 --progress-jsonl events.jsonl -o out.txt

# Keep agent context small: metadata to stdout, transcript to file
transcribe meeting.mp3 --summary -o meeting.md

# One JSON object per segment, pipe-friendly
transcribe call.mp3 --speaker-labels -f ndjson | grep '"speaker": "A"'
```

Errors emit JSON on stdout when `-f json`/`-f ndjson` is set. Bare `transcribe`
prints full help including an agent usage note.

## Development

```bash
git clone https://github.com/miguelarios/transcribe-cli.git
cd transcribe-cli
uv run --extra dev pytest tests/ -v
```

## License

MIT
