"""
TTS + Voice Cloning 服务：
- text_to_speech_bytes：文本转语音
- clone_voice_from_wav：上传参考音频克隆音色（ElevenLabs）
"""
from __future__ import annotations

from typing import Optional, Dict, Any

import httpx
from django.conf import settings


def text_to_speech_bytes(text: str, voice_id: Optional[str] = None) -> bytes:
    """
    ElevenLabs TTS。失败返回空 bytes，调用方自行决定兜底策略。
    """
    api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
    voice_id = voice_id or getattr(settings, 'ELEVENLABS_VOICE_ID', '') or '21m00Tcm4TlvDq8ikWAM'
    if not api_key or not (text or '').strip():
        return b''

    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    headers = {
        'xi-api-key': api_key,
        'Content-Type': 'application/json',
        'accept': 'audio/mpeg',
    }
    payload = {
        'text': text[:5000],
        'model_id': 'eleven_multilingual_v2',
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        return b''
    return b''


def clone_voice_from_wav(
    wav_bytes: bytes,
    filename: str,
    voice_name: str,
    description: str = '',
) -> Dict[str, Any]:
    """
    调用 ElevenLabs Voice Cloning API，返回:
    {'ok': True, 'voice_id': 'xxx', 'provider': 'elevenlabs'}
    """
    provider = (getattr(settings, 'VOICE_CLONE_PROVIDER', 'elevenlabs') or 'elevenlabs').lower()
    if provider != 'elevenlabs':
        return {'ok': False, 'error': f'当前未实现的语音复刻提供方: {provider}'}

    api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
    if not api_key:
        return {'ok': False, 'error': '未配置 ELEVENLABS_API_KEY'}
    if not wav_bytes:
        return {'ok': False, 'error': '参考音频为空'}

    url = 'https://api.elevenlabs.io/v1/voices/add'
    headers = {'xi-api-key': api_key}
    data = {
        'name': (voice_name or 'custom_voice')[:64],
        'description': (description or 'Voice cloned from user sample')[:256],
    }
    files = {'files': (filename or 'sample.wav', wav_bytes, 'audio/wav')}
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, data=data, files=files)
        if resp.status_code >= 400:
            detail = resp.text[:400]
            return {'ok': False, 'error': f'ElevenLabs 克隆失败: {detail}'}
        body = resp.json()
        voice_id = body.get('voice_id')
        if not voice_id:
            return {'ok': False, 'error': 'ElevenLabs 返回中缺少 voice_id'}
        return {'ok': True, 'voice_id': voice_id, 'provider': 'elevenlabs'}
    except Exception as exc:
        return {'ok': False, 'error': f'调用 Voice Cloning 失败: {exc}'}
