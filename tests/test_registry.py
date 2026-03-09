"""Tests for provider registry."""

from transcribe_cli.base import TranscriptionProvider, TranscriptionResult
from transcribe_cli.providers import register, get_provider, list_providers, _PROVIDERS

import pytest


class _FakeProvider(TranscriptionProvider):
    name = "fake"

    def transcribe(self, audio_path, **kwargs):
        return TranscriptionResult(text="fake")

    @classmethod
    def is_available(cls):
        return True


class _UnavailableProvider(TranscriptionProvider):
    name = "unavailable"

    def transcribe(self, audio_path, **kwargs):
        return TranscriptionResult(text="")

    @classmethod
    def is_available(cls):
        return False

    @classmethod
    def required_extras(cls):
        return "unavailable"


def test_register_and_get_provider():
    register(_FakeProvider)
    provider = get_provider("fake")
    assert isinstance(provider, _FakeProvider)


def test_get_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")


def test_get_unavailable_provider_raises():
    register(_UnavailableProvider)
    with pytest.raises(RuntimeError, match="dependencies not installed"):
        get_provider("unavailable")


def test_list_providers_includes_registered():
    register(_FakeProvider)
    providers = list_providers()
    names = [p["name"] for p in providers]
    assert "fake" in names


def teardown_function():
    _PROVIDERS.pop("fake", None)
    _PROVIDERS.pop("unavailable", None)
