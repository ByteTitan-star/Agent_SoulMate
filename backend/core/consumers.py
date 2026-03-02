"""
WebSocket 聊天消费者（全双工 + 打断）：
- 文本消息：type=message
- VAD 协议：
  - type=vad_start   -> 立即打断当前 LLM/TTS
  - type=audio_chunk -> base64 音频分片追加
  - type=vad_end     -> 触发 ASR + LLM 回复
- 显式打断：
  - type=interrupt   -> 立即 cancel 当前任务
"""
from __future__ import annotations

import asyncio
import base64
import json
import uuid
from typing import Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Character, ChatSession, Message
from .services import stream_chat, get_rag_retriever, speech_to_text, text_to_speech_bytes
from .services.llm_service import build_chain

_chat_chains = {}
_ITER_END = object()


def _next_or_end(iterator):
    return next(iterator, _ITER_END)


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character_id: Optional[str] = None
        self.character: Optional[Character] = None
        self.session_key: Optional[str] = None
        self.user = None
        self.chat_session: Optional[ChatSession] = None

        self.reply_task: Optional[asyncio.Task] = None
        self.tts_task: Optional[asyncio.Task] = None
        self.audio_buffer = bytearray()
        self._task_lock = asyncio.Lock()

    async def connect(self):
        self.character_id = str(self.scope['url_route']['kwargs']['character_id'])
        try:
            self.character = await sync_to_async(Character.objects.get)(pk=self.character_id)
        except Character.DoesNotExist:
            await self.close(code=4404)
            return

        user = self.scope.get('user')
        self.user = user
        if not self.character.is_public:
            if not user or not user.is_authenticated or str(user.id) != str(self.character.creator_id):
                await self.close(code=4403)
                return

        session = self.scope.get('session')
        if session and not session.session_key:
            await sync_to_async(session.create)()
        self.session_key = (session and session.session_key) or str(uuid.uuid4())
        self.chat_session = await self._get_or_create_chat_session()
        await self.accept()

    async def disconnect(self, code):
        await self._interrupt_current_generation(reason='disconnect', notify=False)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self._handle_text_frame(text_data)
            return
        if bytes_data:
            # 兼容旧版：直接传整段音频 bytes
            await self._interrupt_current_generation(reason='voice-bytes')
            await self._handle_voice_input(bytes_data)
            return

    async def _handle_text_frame(self, text_data: str):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({'type': 'error', 'detail': '无效 JSON'})
            return

        msg_type = (data.get('type') or '').strip()
        if msg_type == 'message':
            content = (data.get('content') or '').strip()
            if not content:
                return
            await self._interrupt_current_generation(reason='new-message', notify=False)
            self.reply_task = asyncio.create_task(self._run_reply(content, source='text'))
            return

        if msg_type in ('interrupt', 'vad_start', 'speech_start'):
            # 用户开口或主动打断时，取消 LLM/TTS
            self.audio_buffer.clear()
            await self._interrupt_current_generation(reason=msg_type)
            return

        if msg_type == 'audio_chunk':
            chunk_b64 = data.get('data') or ''
            if not chunk_b64:
                return
            try:
                chunk = base64.b64decode(chunk_b64)
            except Exception:
                await self.send_json({'type': 'error', 'detail': 'audio_chunk base64 解码失败'})
                return
            self.audio_buffer.extend(chunk)
            return

        if msg_type == 'vad_end':
            if not self.audio_buffer:
                return
            audio_bytes = bytes(self.audio_buffer)
            self.audio_buffer.clear()
            await self._handle_voice_input(audio_bytes)
            return

    async def _handle_voice_input(self, audio_bytes: bytes):
        # 语音输入开始前中断已有输出，实现“可打断”
        await self._interrupt_current_generation(reason='voice-input', notify=False)

        text = await sync_to_async(speech_to_text)(audio_bytes)
        await self.send_json({'type': 'asr_result', 'text': text or ''})
        if not text or text.startswith('['):
            return
        self.reply_task = asyncio.create_task(self._run_reply(text, source='voice'))

    async def _run_reply(self, user_text: str, source: str):
        msg_id = str(uuid.uuid4())
        await self.send_json({'type': 'stream_start', 'id': msg_id, 'source': source})

        try:
            chain = await self._get_chain()
            rag = await sync_to_async(get_rag_retriever)(self.character)
            history = await self._load_history_messages()
            generator = stream_chat(
                self.character,
                self.session_key or str(uuid.uuid4()),
                user_text,
                chain_dict=chain,
                rag_retriever=rag,
                history_messages=history,
            )

            full_text = ''
            async for token in self._iterate_sync_generator(generator):
                full_text += token
                await self.send_json({'type': 'stream_token', 'id': msg_id, 'token': token})

            await self.send_json({'type': 'stream_end', 'id': msg_id})

            if full_text.strip():
                await self._save_turn(user_text, full_text)

            if full_text and getattr(self.character, 'voice_id', None):
                self.tts_task = asyncio.create_task(self._run_tts(full_text, msg_id))
        except asyncio.CancelledError:
            await self.send_json({'type': 'stream_cancelled', 'id': msg_id})
            raise
        except Exception as exc:
            await self.send_json({'type': 'error', 'detail': f'生成失败: {exc}'})

    async def _iterate_sync_generator(self, generator):
        iterator = iter(generator)
        while True:
            token = await asyncio.to_thread(_next_or_end, iterator)
            if token is _ITER_END:
                break
            yield token

    async def _run_tts(self, text: str, stream_id: str):
        try:
            tts_bytes = await sync_to_async(text_to_speech_bytes)(
                text,
                voice_id=getattr(self.character, 'voice_id', None),
            )
            if not tts_bytes:
                return
            b64 = base64.b64encode(tts_bytes).decode('ascii')
            await self.send_json(
                {'type': 'audio', 'stream_id': stream_id, 'data': b64, 'format': 'mp3'}
            )
        except asyncio.CancelledError:
            await self.send_json({'type': 'tts_cancelled', 'stream_id': stream_id})
            raise
        except Exception as exc:
            await self.send_json({'type': 'error', 'detail': f'TTS 失败: {exc}'})

    async def _interrupt_current_generation(self, reason: str = 'interrupt', notify: bool = True):
        """
        通过 asyncio.Task.cancel() 中止当前 LLM/TTS 任务。
        """
        async with self._task_lock:
            cancelled = False
            if self.reply_task and not self.reply_task.done():
                self.reply_task.cancel()
                cancelled = True
            if self.tts_task and not self.tts_task.done():
                self.tts_task.cancel()
                cancelled = True

            if self.reply_task:
                try:
                    await self.reply_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            if self.tts_task:
                try:
                    await self.tts_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass

            self.reply_task = None
            self.tts_task = None
            if notify and cancelled:
                await self.send_json({'type': 'interrupted', 'reason': reason})

    async def _get_chain(self):
        key = f'{self.character_id}:{self.session_key}'
        if key not in _chat_chains:
            rag = await sync_to_async(get_rag_retriever)(self.character)
            _chat_chains[key] = await sync_to_async(build_chain)(
                self.character,
                self.session_key or str(uuid.uuid4()),
                rag_retriever=rag,
            )
        return _chat_chains.get(key)

    async def _get_or_create_chat_session(self):
        if not self.user or not getattr(self.user, 'is_authenticated', False):
            return None

        def _sync_get_or_create():
            session = ChatSession.objects.filter(user=self.user, character=self.character).order_by('-created_at').first()
            if session:
                return session
            return ChatSession.objects.create(user=self.user, character=self.character)

        return await sync_to_async(_sync_get_or_create)()

    async def _load_history_messages(self, limit: int = 20):
        if not self.chat_session:
            return []

        def _sync_load():
            qs = Message.objects.filter(session=self.chat_session).order_by('-created_at')[:limit]
            rows = list(reversed(list(qs)))
            return [{'role': m.role, 'content': m.content} for m in rows]

        return await sync_to_async(_sync_load)()

    async def _save_turn(self, user_text: str, assistant_text: str):
        if not self.chat_session:
            return

        def _sync_save():
            Message.objects.create(session=self.chat_session, role=Message.ROLE_USER, content=user_text)
            Message.objects.create(session=self.chat_session, role=Message.ROLE_ASSISTANT, content=assistant_text)

        await sync_to_async(_sync_save)()

    async def send_json(self, payload: dict):
        await self.send(text_data=json.dumps(payload, ensure_ascii=False))
