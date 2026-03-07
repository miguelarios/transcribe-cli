# transcribe-cli v1 Design

## Overview

A modular audio transcription CLI tool. V1 uses AssemblyAI as the sole provider, with a provider abstraction ready for future backends (parakeet-mlx, faster-whisper, etc.).

- **Package name (PyPI):** `transcribe-cli`
- **CLI command:** `transcribe`
- **Python:** `>=3.10`
- **Distribution:** PyPI (`pip install transcribe-cli`, `uvx transcribe-cli`)

## Project Structure

```
transcribe-cli/
├── src/transcribe_cli/
│   ├── __init__.py          # __version__
│   ├── cli.py               # Click entry point
│   ├── base.py              # Segment, TranscriptionResult, TranscriptionProvider ABC
│   └── providers/
│       ├── __init__.py      # registry (register, get_provider, list_providers)
│       └── assemblyai.py    # AssemblyAI provider
├── pyproject.toml           # hatchling build, PyPI metadata, CLI entry point
├── README.md
├── LICENSE
└── CLAUDE.md
```

- **Build system:** hatchling
- **CLI framework:** Click (`>=8.1`)
- **Runtime deps:** `click>=8.1`, `assemblyai>=0.30`
- **Optional deps:** `[parakeet]` (future), `[all]`
- **Entry point:** `transcribe = "transcribe_cli.cli:cli"`

## CLI Interface

```
transcribe [OPTIONS] AUDIO

AUDIO: File path or URL to audio/video
```

### Output Options

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output PATH` | stdout | Write to file instead of stdout |
| `-f, --format` | `text` | `text`, `json`, `srt`, `vtt` |
| `--summary` | off | Output metadata only, save transcript to temp file |

### API Key

| Flag | Default | Description |
|------|---------|-------------|
| `--api-key KEY` | `$ASSEMBLYAI_API_KEY` | AssemblyAI API key |

Resolution order: `--api-key` flag > `ASSEMBLYAI_API_KEY` env var > error with setup instructions.

### Speaker/Diarization (all default: off, matching API)

| Flag | API param | Description |
|------|-----------|-------------|
| `--speaker-labels` | `speaker_labels` | Enable speaker diarization |
| `--speakers-expected N` | `speakers_expected` | Exact speaker count |
| `--min-speakers N` | `speaker_options.min_speakers_expected` | Min speakers (use with --max-speakers) |
| `--max-speakers N` | `speaker_options.max_speakers_expected` | Max speakers (use with --min-speakers) |
| `--speaker-id-type role\|name` | `speech_understanding.speaker_identification.speaker_type` | Speaker identification mode |
| `--speaker-names "Name"` | `speech_understanding.speaker_identification.known_values` | Known speaker names/roles (repeatable, 35 char max each) |

### Analysis (all default: off, matching API)

| Flag | API param | Description |
|------|-----------|-------------|
| `--entities` | `entity_detection` | Detect names, locations, dates, etc. |
| `--sentiment` | `sentiment_analysis` | Sentiment per utterance |
| `--topics` | `iab_categories` | IAB topic detection |
| `--auto-chapters` | `auto_chapters` | Generate chapters with headlines |
| `--summarize` | `summarization` | Generate transcript summary |
| `--summary-model` | `summary_model` | `informative` (default), `conversational`, `catchy` |
| `--summary-type` | `summary_type` | `bullets` (default), `bullets_verbose`, `gist`, `headline`, `paragraph` |
| `--content-safety` | `content_safety` | Content moderation |

### Language

| Flag | API param | Default | Description |
|------|-----------|---------|-------------|
| `--language CODE` | `language_code` | `en_us` | Language code |
| `--language-detection` | `language_detection` | off | Auto-detect language |

### Advanced

| Flag | API param | Default | Description |
|------|-----------|---------|-------------|
| `--prompt TEXT` | `prompt` | none | Context prompt (Universal-3-Pro) |
| `--multichannel` | `multichannel` | off | Separate audio channels |
| `--redact-pii` | `redact_pii` | off | Redact PII from text |
| `--filter-profanity` | `filter_profanity` | off | Filter profanity |
| `--disfluencies` | `disfluencies` | off | Include filler words (um, uh) |
| `--keyterms A B C` | `keyterms_prompt` | none | Domain-specific terms to boost |
| `--no-punctuate` | `punctuate=false` | on | Disable auto punctuation |
| `--no-format-text` | `format_text=false` | on | Disable text formatting |

### Meta

| Flag | Description |
|------|-------------|
| `--list-providers` | List available providers |
| `-v, --verbose` | Progress/timing info on stderr |
| `--version` | Show version |
| `-h, --help` | Help (shows defaults per API docs) |

## Output Formats

### Default text format

Timestamps always included. Speaker labels shown when diarization data is available.

```
# With --speaker-labels
[00:00:00] Speaker A: Hello everyone, welcome to the meeting.
[00:00:04] Speaker A: Today we're going to talk about the roadmap.
[00:00:09] Speaker B: Let's start with the Q3 priorities.

# Without --speaker-labels
[00:00:00] Hello everyone, welcome to the meeting.
[00:00:04] Today we're going to talk about the roadmap.
[00:00:09] Let's start with the Q3 priorities.
```

### JSON format (`-f json`)

```json
{
  "text": "Hello everyone...",
  "segments": [
    {
      "text": "Hello everyone, welcome to the meeting.",
      "start": 0.0,
      "end": 3.5,
      "speaker": "A",
      "confidence": 0.95,
      "sentiment": "POSITIVE"
    }
  ],
  "language": "en_us",
  "duration_seconds": 342.0,
  "provider": "assemblyai",
  "elapsed_seconds": 12.3,
  "metadata": {
    "id": "abc123",
    "entities": [],
    "chapters": [],
    "topics": {},
    "summary": "..."
  }
}
```

### SRT/VTT

Standard subtitle formats with speaker labels when available.

### Summary mode (`--summary`)

Outputs metadata to stdout, saves full transcript to a temp file:

```json
{
  "file": "/tmp/transcribe-cli/abc123.json",
  "word_count": 4521,
  "token_count": 5800,
  "speaker_count": 3,
  "duration_seconds": 342,
  "language": "en_us",
  "provider": "assemblyai"
}
```

Purpose: AI agents can inspect metadata to decide whether to ingest the full transcript directly or delegate to a subagent to avoid context window overflow.

## Architecture

### Provider Abstraction

```
TranscriptionProvider (ABC)
├── transcribe(audio_path, **kwargs) -> TranscriptionResult
├── is_available() -> bool
└── required_extras() -> str

TranscriptionResult (dataclass)
├── text: str
├── segments: list[Segment]
├── language, duration_seconds, provider, elapsed_seconds
├── metadata: dict
├── to_dict() -> dict
├── to_srt() -> str
└── to_vtt() -> str

Segment (dataclass)
├── text, start (seconds), end (seconds)
├── speaker (optional), confidence (optional), sentiment (optional)
```

### Provider Registry

- `@register` decorator on provider classes
- `get_provider(name, **kwargs)` to instantiate
- `list_providers()` for `--list-providers`
- Auto-discovery via imports in `providers/__init__.py`

### Data Flow

```
1. CLI parses args (Click)
2. Resolve API key (--api-key flag -> env var -> error)
3. Detect input type (file path vs URL)
4. Get provider via registry -> AssemblyAIProvider
5. Build config from CLI flags -> AssemblyAI TranscriptionConfig
6. Call provider.transcribe(audio, **kwargs) -> TranscriptionResult
7. Format output (text/json/srt/vtt) or summary mode
8. Write to stdout or -o file
```

### Error Handling

- Missing API key: clear error message with setup instructions
- Invalid file/URL: error before hitting the API
- API errors: clean message to stderr, JSON error object if `-f json`
- Exit codes: 0 = success, 1 = error, 130 = interrupted

## Design Decisions

- **No `--provider` flag in v1:** Only AssemblyAI. Flag will be added when a second provider lands.
- **Parakeet deferred:** parakeet-mlx is Apple Silicon only. Cross-platform local transcription needs more research (faster-whisper, parakeet-stream). Revisit in v2.
- **Click over argparse:** Better help formatting, show_default support, extensible for future subcommands.
- **stdout by default:** Unix-friendly, pipe-friendly. Use `-o` for file output.
- **Timestamps always in text output:** Matches the format the user wants for agent consumption.
- **API key via flag or env var only:** No config file in v1. Keep it simple.

## Future (out of scope for v1)

- Local providers: parakeet-mlx (macOS), faster-whisper (cross-platform)
- `--provider` flag
- `--summarize-with-llm` flag to pipe transcript through an LLM
- Config file (`~/.config/transcribe-cli/config.toml`)
- Homebrew formula
