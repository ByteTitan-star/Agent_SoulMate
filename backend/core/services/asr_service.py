"""
ASR：语音转文字。支持 OpenAI Whisper API 或本地 whisper。
"""

import io
import os

from django.conf import settings


# 优先用 OpenAI Whisper API（与 OpenAI 兼容的接口）
def speech_to_text(audio_bytes: bytes, content_type: str = 'audio/wav') -> str:
    """
    将音频字节转为文本。
    content_type: 如 audio/wav, audio/webm, audio/mpeg
    """
    # 与主 LLM 配置解耦，避免把 Ollama 当 Whisper API 调用
    api_key = getattr(settings, 'ASR_OPENAI_API_KEY', None) or ''
    api_base = getattr(settings, 'ASR_OPENAI_BASE_URL', None) or ''
    if api_key and api_base:
        try:
            import openai

            client = openai.OpenAI(api_key=api_key, base_url=api_base)
            fp = io.BytesIO(audio_bytes)
            fp.name = 'audio.webm'
            transcript = client.audio.transcriptions.create(model='whisper-1', file=fp)
            return transcript.text or ''
        except Exception as e:
            return f'[ASR 错误: {e!s}]'

    # 本地 whisper（需安装 openai-whisper）
    try:
        import whisper

        model_name = getattr(settings, 'WHISPER_MODEL', 'base')
        model = whisper.load_model(model_name)
        # whisper needs a file path; write a temp file then clean up
        import tempfile

        suffix = '.wav' if audio_bytes[:4] == b'RIFF' else '.webm'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name
        try:
            result = model.transcribe(tmp_path, language='zh', fp16=False)
            text = (result.get('text') or '').strip()
            return text or '[无法识别]'
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except ImportError:
        return '[请配置 ASR_OPENAI_API_KEY/ASR_OPENAI_BASE_URL 或安装 openai-whisper]'
    except Exception as e:
        return f'[ASR 错误: {e!s}]'
