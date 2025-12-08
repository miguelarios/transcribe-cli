# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based audio transcription and speaker diarization tool using the AssemblyAI API. The project transcribes audio files with advanced features including:

- **Speaker Diarization** - Identifies different speakers (Speaker A, B, C...)
- **Speaker Identification** - Maps speakers to actual names or roles
- **Sentiment Analysis** - Detects emotional tone per utterance
- **Entity Detection** - Extracts names, locations, dates, emails, phone numbers
- **Language Detection** - Auto-detects or manually specifies language
- **Auto Chapters** - Automatically generates chapters with headlines and summaries
- **Summarization** - Creates overall transcript summaries in various formats
- **Topic Detection** - Identifies topics using IAB taxonomy (~698 topics)
- **Multiple Output Formats** - TXT, SRT, and comprehensive JSON

## Architecture

The codebase contains a single production-ready script:

- **`transcribe.py`**: Enhanced audio transcription tool with multiple output formats and advanced features

The script follows this architecture:
1. Load API key from environment variable or `.env` file
2. Parse command-line arguments (audio file path, output format, options)
3. Validate the input audio file
4. Configure AssemblyAI with speaker labels, sentiment analysis, and entity detection
5. Transcribe the audio file using AssemblyAI's API with progress indicators
6. **Receive complete structured data** from AssemblyAI (utterances, speakers, sentiment, entities, timestamps)
7. Save the output in the requested format (TXT, SRT, or JSON)
8. Display a summary with duration, speaker count, utterances, and entity count

## Project Structure

```
transcribe/
├── transcribe.py          # Main CLI script
├── pyproject.toml         # Package configuration and dependencies
├── uv.lock                # Locked dependency versions (managed by uv)
├── .python-version        # Python version specification (3.11)
├── .env.example           # Template for environment variables
├── .gitignore             # Git ignore patterns
├── README.md              # User-facing documentation
├── CLAUDE.md              # This file - AI assistant guidance
├── MIGRATION.md           # Guide for migrating from pyenv to uv
└── src/                   # Package build artifacts
    └── transcribe.egg-info/
```

### Key Files
- **transcribe.py**: The main script containing all transcription logic
- **pyproject.toml**: Defines package metadata, dependencies, and the CLI entry point
- **uv.lock**: Ensures reproducible dependency installations
- **.python-version**: Specifies Python 3.11 for the project
- **MIGRATION.md**: Documents the transition from pyenv-virtualenv to uv

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and global CLI installation. There are two ways to set up the project:

### Method 1: Global CLI Installation (Recommended)

Install the tool globally so you can run `transcribe` from anywhere:

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install the transcribe tool globally
cd /path/to/transcribe
uv tool install .

# 3. Now you can use 'transcribe' from any directory
transcribe audio.mp3
```

To update after pulling changes:
```bash
cd /path/to/transcribe
git pull
uv tool install . --force
```

See [MIGRATION.md](MIGRATION.md) for details on the migration from pyenv-virtualenv to uv.

### Method 2: Direct Python Execution (Development)

For development or if you prefer running the script directly:

```bash
# Run directly without installing (uv handles dependencies)
cd /path/to/transcribe
uv run python transcribe.py audio.mp3

# Or install dependencies manually with pip
pip install assemblyai>=0.17.0
python transcribe.py audio.mp3
```

### API Key Configuration

Configure your API key using one of these methods (in order of precedence):

1. **Environment variable** (recommended for global CLI installation):
   ```bash
   export ASSEMBLYAI_API_KEY='your_api_key_here'
   # Add to ~/.zshrc or ~/.bashrc to make permanent
   ```

2. **Home directory .env file** (convenient for global CLI):
   ```bash
   echo "ASSEMBLYAI_API_KEY=your_api_key_here" > ~/.transcribe.env
   ```

3. **Project directory .env file** (for development):
   ```bash
   cd /path/to/transcribe
   cp .env.example .env
   # Edit .env and add your API key
   ```

The script searches for `.env` files in this order:
1. Current working directory
2. Script's directory
3. Home directory (`~/.transcribe.env`)

Get your API key from: https://www.assemblyai.com/dashboard

## Running the Script

### Using the CLI Command (After Global Installation)

If you installed with `uv tool install .`, use the `transcribe` command from anywhere:

```bash
# Basic usage (creates both JSON + TXT by default)
transcribe audio.mp3
# Creates: audio_transcript.json + audio_transcript.txt

# With options
transcribe audio.mp3 --format srt
transcribe audio.mp3 --timestamps
transcribe audio.mp3 --json-only
transcribe audio.mp3 --output /path/to/transcript
```

### Using Direct Python Execution

If running the script directly:

```bash
# Basic usage
python transcribe.py audio.mp3

# With options
python transcribe.py audio.mp3 --format srt
python transcribe.py audio.mp3 --timestamps
python transcribe.py audio.mp3 --json-only
python transcribe.py audio.mp3 --output /path/to/transcript
```

### Common Usage Examples

```bash
# Create JSON + SRT subtitle files
transcribe audio.mp3 --format srt

# Include timestamps in text output (JSON + TXT with timestamps)
transcribe audio.mp3 --timestamps

# Only create JSON file (skip human-readable format)
transcribe audio.mp3 --json-only

# Specify custom output path (without extension)
transcribe audio.mp3 --output /path/to/transcript

# Disable sentiment analysis
transcribe audio.mp3 --no-sentiment

# Control speaker detection (exact count)
transcribe audio.mp3 --speakers-expected 3

# Control speaker detection (range)
transcribe audio.mp3 --min-speakers 2 --max-speakers 5
```

**Note**: JSON files always include metadata and speaker statistics by default. Use `--json-only` to skip creating a human-readable file.

## Command-line Options

### Basic Options
- `audio_file`: Path to the audio file to transcribe (required)
- `-f, --format`: Human-readable format - `txt` or `srt` (default: txt). JSON is always created.
- `-t, --timestamps`: Include timestamps in text output
- `-m, --metadata`: Force additional metadata in JSON (already enabled by default)
- `--json-only`: Only create JSON file, skip human-readable format
- `-o, --output`: Base output file path without extension (extensions added automatically)
- `--version`: Show version information

### Feature Toggle Options
- `--no-speaker-labels`: Disable speaker diarization
- `--no-sentiment`: Disable sentiment analysis
- `--no-entities`: Disable entity detection (names, locations, dates, emails, etc.)

### Speaker Detection Control
Control the number of speakers to detect in the audio:

- `--speakers-expected N`: Specify exact number of speakers (use when you know for certain)
- `--min-speakers N --max-speakers M`: Specify a range of speakers (use together)

**Note**: You cannot use `--speakers-expected` with `--min-speakers`/`--max-speakers`. Choose one approach:
- Use `--speakers-expected 3` when you know exactly 3 speakers
- Use `--min-speakers 2 --max-speakers 4` for a range of 2-4 speakers
- Omit both to let AssemblyAI auto-detect (default: 1-10 range)

## Dependencies

The project uses `pyproject.toml` for dependency management and packaging:

### Runtime Dependencies
- `assemblyai>=0.17.0` - AssemblyAI Python SDK for audio transcription and speaker diarization
- Standard library: `sys`, `os`, `json`, `argparse`, `time`, `pathlib`, `typing`, `datetime`

### Build System
- `hatchling` - Modern Python build backend
- Requires Python 3.8 or higher (project uses Python 3.11)

### Package Configuration
The project is configured as a Python package with a CLI entry point:
- Package name: `transcribe`
- Entry point: `transcribe` command maps to `transcribe:main`
- Version: 0.1.0

## Output Formats

**By default, the script creates TWO files**:
1. **JSON file** - Complete structured data (always created unless you use `--json-only`)
2. **Human-readable file** - TXT or SRT for easy reading

### JSON (.json) - Always Created
Structured data with utterances, confidence scores, entities (names, locations, dates, etc.), metadata, and speaker statistics.

Example structure:
```json
{
  "transcript_id": "abc123",
  "metadata": {
    "audio_duration": 125300,
    "confidence": 0.9423,
    "language_code": "en"
  },
  "speaker_statistics": {
    "A": {"word_count": 150, "utterance_count": 12, "total_time_ms": 45000},
    "B": {"word_count": 200, "utterance_count": 18, "total_time_ms": 60000}
  },
  "utterances": [
    {
      "speaker": "A",
      "text": "Hello, this is a sample.",
      "start": 0,
      "end": 2000,
      "confidence": 0.95,
      "sentiment": "POSITIVE"
    }
  ],
  "entities": [
    {
      "text": "John Smith",
      "type": "person_name",
      "start": 1500,
      "end": 2000
    }
  ]
}
```

### Text (.txt) - Default Human-Readable Format
```
Speaker A: [transcribed text]

Speaker B: [transcribed text]
```

With `--timestamps`:
```
[00:00:00,000 --> 00:00:05,000] Speaker A: [transcribed text]

[00:00:05,000 --> 00:00:10,000] Speaker B: [transcribed text]
```

### SRT (.srt) - Alternative Human-Readable Format
Standard subtitle format with timestamps and speaker labels. Use `--format srt` to create this alongside JSON.

## Recommended Workflow for Note-Taking

This tool is designed to extract **structured data** from audio that's difficult to obtain from text alone:

1. **Speaker Diarization** - Identifies who said what
2. **Timestamps** - When each utterance occurred
3. **Sentiment Analysis** - Emotional tone per utterance
4. **Entity Detection** - Extracted names, locations, dates, emails, phone numbers

**For best results**, use the JSON output with metadata and feed it to an LLM (Claude, ChatGPT) for:
- Creating meeting notes
- Summarizing content
- Identifying action items
- Generating chapters/sections
- Extracting key decisions

The structured data provides context that helps LLMs understand:
- Who made specific statements
- When important information was mentioned
- What entities (people, places, organizations) were discussed
- The emotional context of the conversation

## Development Workflow

When working on the code or making changes:

### Running During Development
```bash
# Method 1: Run directly with uv (handles dependencies automatically)
cd /path/to/transcribe
uv run python transcribe.py audio.mp3

# Method 2: Install in editable mode for live testing
uv tool install --editable .
# Now changes to transcribe.py are immediately available via 'transcribe' command
transcribe audio.mp3
```

### Making Changes
1. Edit `transcribe.py` directly - it contains all the logic
2. Test changes locally using `uv run python transcribe.py` or the installed CLI
3. Update version in `pyproject.toml` if making a release
4. Follow Conventional Commits (see Git Conventions below)

### Important Notes for AI Assistants
- The script is self-contained in `transcribe.py` - no other Python modules
- Do not create new Python files unless absolutely necessary
- When adding features, prefer extending the existing command-line arguments
- All output generation happens in the save_* functions (save_txt_transcript, save_srt_transcript, save_json_transcript)
- The AssemblyAI API returns structured data - we don't need to parse or extract it, just format it

## Security Notes

- API keys are managed via environment variables or `.env` file
- The `.env` file is gitignored to prevent accidental commits
- Never commit API keys to version control
- Use `.env.example` as a template for setting up your environment

## Git Conventions

This project follows **Conventional Commits** specification for all commit messages and standardized branch naming conventions.

### Commit Message Format

All commits MUST follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Common types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semi-colons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI/CD configuration
- `chore`: Other changes that don't modify src or test files

**Examples:**
```
docs: add comprehensive README
feat: add support for WebM audio format
fix: handle missing sentiment data gracefully
refactor: simplify timestamp formatting logic
```

### Branch Naming Convention

Branches should follow this pattern:

```
<type>/<short-description>
```

**Examples:**
- `feat/webm-support`
- `fix/timestamp-formatting`
- `docs/update-readme`
- `refactor/simplify-output`

**Note:** Claude Code may use a special prefix `claude/` for automated branches, which is acceptable in that context.

### Why Conventional Commits?

1. **Automatic changelog generation** - Tools can parse commits to generate changelogs
2. **Semantic versioning** - Determine version bumps automatically (feat = minor, fix = patch)
3. **Clear history** - Easy to understand what each commit does
4. **Better collaboration** - Consistent format across all contributors
