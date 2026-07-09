"""Provider registry — discovers and manages available transcription backends."""

from __future__ import annotations

from transcribe_cli.base import TranscriptionProvider

_PROVIDERS: dict[str, type[TranscriptionProvider]] = {}


def register(cls: type[TranscriptionProvider]) -> type[TranscriptionProvider]:
    """Register a provider class by its name."""
    _PROVIDERS[cls.name] = cls
    return cls


def get_provider(name: str, **kwargs) -> TranscriptionProvider:
    """Instantiate a provider by name."""
    if name not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    cls = _PROVIDERS[name]
    if not cls.is_available():
        extras = cls.required_extras()
        hint = (
            f"Install with: pip install 'transcriber-cli[{extras}]'"
            if extras
            else "Reinstall with: pip install transcriber-cli"
        )
        raise RuntimeError(f"Provider '{name}' dependencies not installed. {hint}")

    return cls(**kwargs)


def list_providers() -> list[dict]:
    """List all registered providers with availability status."""
    return [
        {
            "name": name,
            "available": cls.is_available(),
            "extras": cls.required_extras(),
        }
        for name, cls in sorted(_PROVIDERS.items())
    ]


def _auto_discover():
    """Import all provider modules to trigger @register decorators."""
    try:
        from transcribe_cli.providers import assemblyai  # noqa: F401
    except ImportError:
        pass


_auto_discover()
