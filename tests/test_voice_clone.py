"""Voice clone API tests (ElevenLabs calls are mocked)."""

from __future__ import annotations

import io
import wave
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import Character


def _make_wav_bytes(duration_sec: float = 15.0, rate: int = 16000) -> bytes:
    frames = int(rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def owner(db):
    User = get_user_model()
    return User.objects.create_user(username="owner", password="pass12345")


@pytest.fixture
def other_user(db):
    User = get_user_model()
    return User.objects.create_user(username="other", password="pass12345")


@pytest.fixture
def character(owner):
    return Character.objects.create(
        name="CloneBot",
        gender="other",
        system_prompt="You are a test companion.",
        creator=owner,
        is_public=False,
    )


@pytest.mark.django_db
def test_voice_clone_rejects_non_owner(api_client, character, other_user):
    api_client.force_authenticate(user=other_user)
    wav = SimpleUploadedFile("sample.wav", _make_wav_bytes(), content_type="audio/wav")
    res = api_client.post(
        f"/api/characters/{character.id}/voice-clone/",
        {"file": wav},
        format="multipart",
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_voice_clone_rejects_short_wav(api_client, character, owner):
    api_client.force_authenticate(user=owner)
    wav = SimpleUploadedFile("short.wav", _make_wav_bytes(3.0), content_type="audio/wav")
    res = api_client.post(
        f"/api/characters/{character.id}/voice-clone/",
        {"file": wav},
        format="multipart",
    )
    assert res.status_code == 400
    assert "10~30" in (res.data.get("detail") or "")


@pytest.mark.django_db
def test_voice_clone_persists_voice_id(api_client, character, owner):
    api_client.force_authenticate(user=owner)
    wav = SimpleUploadedFile("sample.wav", _make_wav_bytes(12.0), content_type="audio/wav")

    with patch(
        "core.views.chat_views.clone_voice_from_wav",
        return_value={"ok": True, "voice_id": "voice_abc", "provider": "elevenlabs"},
    ):
        res = api_client.post(
            f"/api/characters/{character.id}/voice-clone/",
            {"file": wav, "voice_name": "CloneBot-owner"},
            format="multipart",
        )

    assert res.status_code == 200
    assert res.data["voice_id"] == "voice_abc"
    character.refresh_from_db()
    assert character.voice_id == "voice_abc"
