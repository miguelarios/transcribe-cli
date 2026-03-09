# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

A modular Python CLI for audio transcription with pluggable providers. V1 uses AssemblyAI. Output goes to stdout by default; `-o` writes to file. Designed to be agent-friendly (JSON output, `--summary` mode, piping).

## Architecture

```
src/transcribe_cli/
├── __init__.py              # Package version
├── base.py                  # Segment, TranscriptionResult, TranscriptionProvider ABC
├── cli.py                   # Click CLI entry point
└── providers/
    ├── __init__.py          # Provider registry (register, get_provider, list_providers)
    └── assemblyai.py        # AssemblyAI provider implementation
tests/
├── test_base.py             # Data class and output format tests
├── test_registry.py         # Provider registry tests
├── test_assemblyai_provider.py  # AssemblyAI provider tests (mocked)
└── test_cli.py              # CLI integration tests
```

### Key patterns
- **Provider registry**: `providers/__init__.py` auto-discovers providers via `_auto_discover()`. New providers register with `@register` decorator.
- **Data flow**: CLI → `get_provider()` → `provider.timed_transcribe()` → `TranscriptionResult` → format output (text/json/srt/vtt)
- **TranscriptionResult** has `to_dict()`, `to_text()`, `to_srt()`, `to_vtt()`, `to_summary()` methods
- **All output to stdout** by default. Verbose/progress info goes to stderr.

## Tech Stack

- Python 3.10+, Click, AssemblyAI SDK, hatchling (build), pytest (test), ruff (lint)

## Setup

```bash
# Development
uv run --extra dev pytest tests/ -v

# Install globally
uv tool install .

# Run without installing
uv run transcribe audio.mp3
```

### API Key

```bash
export ASSEMBLYAI_API_KEY='your_key'
# Or: transcribe --api-key <key> audio.mp3
```

## Running Tests

```bash
uv run --extra dev pytest tests/ -v
```

All AssemblyAI tests use mocking — no real API calls needed.

## Git Conventions

**Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `chore:`

**Branch naming**: `<type>/<short-description>` (e.g., `feat/whisper-provider`)

## Adding a New Provider

1. Create `src/transcribe_cli/providers/<name>.py`
2. Subclass `TranscriptionProvider`, implement `transcribe()`, set `name`, `is_available()`, `required_extras()`
3. Decorate with `@register`
4. Add import to `_auto_discover()` in `providers/__init__.py`
5. Add dependency to `pyproject.toml` as optional extra
