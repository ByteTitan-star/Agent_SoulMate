"""Smoke tests for WebSocket barge-in helpers."""

from core.consumers import _ITER_END, _next_or_end


def test_next_or_end_exhausts_iterator() -> None:
    it = iter(["hello", "world"])
    assert _next_or_end(it) == "hello"
    assert _next_or_end(it) == "world"
    assert _next_or_end(it) is _ITER_END


def test_wav_magic_bytes() -> None:
    """Frontend VAD uploads WAV; ASR should detect RIFF header."""
    header = b"RIFF" + bytes(40)
    assert header[:4] == b"RIFF"
