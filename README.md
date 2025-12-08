# Audio Transcription with Speaker Diarization

A powerful Python-based audio transcription tool that uses the AssemblyAI API to transcribe audio files with automatic speaker identification, sentiment analysis, and entity detection.

## Features

- **Speaker Diarization**: Automatically identifies and labels different speakers in the audio
- **Sentiment Analysis**: Detects the emotional tone (positive, neutral, negative) of each utterance
- **Entity Detection**: Extracts names, locations, dates, emails, phone numbers, and other entities
- **Multiple Output Formats**: Generates JSON (structured data) and human-readable formats (TXT or SRT)
- **Progress Tracking**: Real-time transcription status updates with visual progress indicators
- **Flexible Configuration**: Enable/disable features via command-line options

## Quick Start (Recommended)

### Install as a Global CLI Tool with uv

The easiest way to use this tool is to install it globally with [uv](https://github.com/astral-sh/uv), making the `transcribe` command available from any directory without needing to activate virtual environments.

#### Prerequisites
- macOS, Linux, or Windows
- No Python installation needed (uv handles it automatically)

#### Installation Steps

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone https://github.com/miguelarios/transcribe.git
cd transcribe

# 3. Install the tool globally
uv tool install .

# 4. Configure your API key (see below)
```

#### Get Your API Key

1. Sign up for a free AssemblyAI account at [https://www.assemblyai.com](https://www.assemblyai.com)
2. Get your API key from the [AssemblyAI Dashboard](https://www.assemblyai.com/dashboard)

#### Configure API Key

Choose one of these methods:

**Option 1: Environment variable (recommended for global install)**

```bash
export ASSEMBLYAI_API_KEY='your_api_key_here'
# Add to your ~/.zshrc or ~/.bashrc to make it permanent
echo 'export ASSEMBLYAI_API_KEY="your_api_key_here"' >> ~/.zshrc
```

**Option 2: Home directory .env file**

```bash
echo "ASSEMBLYAI_API_KEY=your_api_key_here" > ~/.transcribe.env
```

**Option 3: Project directory .env file (for development)**

```bash
cd ~/path/to/transcribe
cp .env.example .env
# Edit .env and add your API key
```

#### That's it!

Now you can use `transcribe` from any directory:

```bash
cd ~/anywhere
transcribe audio.mp3
```

### Update the Tool

```bash
cd ~/path/to/transcribe
git pull
uv tool install . --force
```

### Uninstall

```bash
uv tool uninstall transcribe
```

---

## Alternative: Traditional Python Installation

If you prefer using pip and virtual environments:

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install assemblyai
```

### Run Directly

```bash
python transcribe.py audio.mp3
```

**Note**: With this method, you need to be in the project directory to run the script.

## Usage

### Basic Usage

By default, the script creates both JSON (structured data) and TXT (human-readable) files:

```bash
python transcribe.py audio.mp3
```

This creates:
- `audio_transcript.json` - Complete structured data with metadata
- `audio_transcript.txt` - Easy-to-read speaker transcript

### Advanced Usage Examples

**Create SRT subtitle files (JSON + SRT):**
```bash
python transcribe.py audio.mp3 --format srt
```

**Include timestamps in text output:**
```bash
python transcribe.py audio.mp3 --timestamps
```

**Create only JSON file (skip human-readable format):**
```bash
python transcribe.py audio.mp3 --json-only
```

**Specify custom output path:**
```bash
python transcribe.py audio.mp3 --output /path/to/my_transcript
```

**Disable optional features:**
```bash
# Disable sentiment analysis
python transcribe.py audio.mp3 --no-sentiment

# Disable entity detection
python transcribe.py audio.mp3 --no-entities

# Disable speaker diarization
python transcribe.py audio.mp3 --no-speaker-labels
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `audio_file` | Path to the audio file to transcribe (required) |
| `-f, --format` | Human-readable format: `txt` or `srt` (default: txt) |
| `-t, --timestamps` | Include timestamps in text output |
| `-m, --metadata` | Force additional metadata in JSON (enabled by default) |
| `--json-only` | Only create JSON file, skip human-readable format |
| `-o, --output` | Base output file path without extension |
| `--no-speaker-labels` | Disable speaker diarization |
| `--no-sentiment` | Disable sentiment analysis |
| `--no-entities` | Disable entity detection |

## Output Formats

### JSON Format (Always Created)

Complete structured data with utterances, speakers, timestamps, sentiment, entities, and metadata:

```json
{
  "transcript_id": "abc123",
  "metadata": {
    "audio_duration": 125300,
    "confidence": 0.9423,
    "language_code": "en"
  },
  "speaker_statistics": {
    "A": {
      "word_count": 150,
      "utterance_count": 12,
      "total_time_ms": 45000
    },
    "B": {
      "word_count": 200,
      "utterance_count": 18,
      "total_time_ms": 60000
    }
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

### Text Format (.txt)

Simple speaker-labeled transcript:

```
Speaker A: [transcribed text]

Speaker B: [transcribed text]
```

With `--timestamps` option:

```
[00:00:00,000 --> 00:00:05,000] Speaker A: [transcribed text]

[00:00:05,000 --> 00:00:10,000] Speaker B: [transcribed text]
```

### SRT Format (.srt)

Standard subtitle format with speaker labels:

```
1
00:00:00,000 --> 00:00:05,000
Speaker A: [transcribed text]

2
00:00:05,000 --> 00:00:10,000
Speaker B: [transcribed text]
```

## Use Cases

### Meeting Notes and Summaries

This tool excels at extracting structured data that's difficult to obtain from plain text:

1. **Speaker Identification**: Know who said what
2. **Timestamps**: When each statement was made
3. **Sentiment Analysis**: Emotional context of discussions
4. **Entity Extraction**: Names, locations, dates, organizations mentioned

### LLM-Powered Analysis

The JSON output is ideal for feeding to Large Language Models (Claude, ChatGPT, etc.) to:

- Generate meeting minutes
- Create executive summaries
- Extract action items and decisions
- Identify key topics and themes
- Generate chapter markers
- Create searchable transcripts

**Example workflow:**
```bash
# Transcribe your meeting
python transcribe.py meeting.mp3

# Feed meeting_transcript.json to an LLM with a prompt like:
# "Based on this transcript with speaker labels and timestamps,
#  create meeting notes with action items and key decisions."
```

## Supported Audio Formats

AssemblyAI supports various audio and video formats including:

- MP3, MP4
- WAV, FLAC
- M4A, AAC
- OGG, OPUS
- WebM

## Security Notes

- API keys are managed via environment variables or `.env` file
- The `.env` file is gitignored to prevent accidental commits
- **Never commit API keys to version control**
- Use `.env.example` as a template for your local setup

## Development

If you want to contribute or work on the code:

```bash
# Clone the repository
git clone https://github.com/miguelarios/transcribe.git
cd transcribe

# Run directly without installing
uv run python transcribe.py audio.mp3

# Or install in editable mode for global access while developing
uv tool install --editable .

# Make your changes, they'll be immediately available
transcribe audio.mp3
```

## Migrating from pyenv-virtualenv

If you previously used this tool with pyenv-virtualenv, see [MIGRATION.md](MIGRATION.md) for a complete migration guide.

**TL;DR:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reinstall with uv
cd ~/path/to/transcribe
uv tool install .

# The tool now works globally without activation!
```

## Troubleshooting

### "Error: ASSEMBLYAI_API_KEY not found"

Make sure you've set up your API key using one of the methods described in the Setup section.

### "transcribe: command not found" (uv installation)

```bash
# Restart your shell
exec "$SHELL"

# Or check if uv's bin directory is in PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### File size limits

AssemblyAI has file size limits depending on your plan. For large files, consider:
- Compressing the audio
- Splitting into smaller segments
- Upgrading your AssemblyAI plan

### Audio quality issues

For best transcription results:
- Use clear audio with minimal background noise
- Ensure speakers are clearly audible
- Use higher bitrate audio files when possible

## License

This project is open source. Feel free to modify and distribute as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- Built with [AssemblyAI API](https://www.assemblyai.com) for transcription and speaker diarization
- Developed as a tool for extracting structured data from audio conversations
