import io
import json
import uuid
import wave

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Character, ChatSession, Message
from ..services import stream_chat, get_rag_retriever, ingest_document, clone_voice_from_wav
from ..services.llm_service import build_chain

# 内存中按 session 存 chain，生产建议用 Redis。
_chat_chains = {}


def _get_or_build_chain(character, session_id: str):
    key = f'{character.id}:{session_id}'
    if key not in _chat_chains:
        rag = get_rag_retriever(character)
        _chat_chains[key] = build_chain(character, session_id, rag_retriever=rag)
    return _chat_chains.get(key)


def _get_latest_chat_session(character, user, create: bool = False):
    if not user or not user.is_authenticated:
        return None
    session = ChatSession.objects.filter(user=user, character=character).order_by('-created_at').first()
    if session or not create:
        return session
    return ChatSession.objects.create(user=user, character=character)


def _get_or_create_chat_session(character, user):
    return _get_latest_chat_session(character, user, create=True)


def _load_history_messages(chat_session, limit: int = 20):
    if not chat_session:
        return []
    qs = Message.objects.filter(session=chat_session).order_by('-created_at')[:limit]
    rows = list(reversed(list(qs)))
    return [{'role': m.role, 'content': m.content} for m in rows]


def _save_turn(chat_session, user_text: str, assistant_text: str):
    if not chat_session:
        return
    Message.objects.create(session=chat_session, role=Message.ROLE_USER, content=user_text)
    Message.objects.create(session=chat_session, role=Message.ROLE_ASSISTANT, content=assistant_text)


def _serialize_message(message: Message):
    return {
        'id': str(message.id),
        'role': message.role,
        'content': message.content,
        'timestamp': message.created_at.isoformat(),
    }


def _wav_duration_seconds(wav_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate() or 1
            return float(frames) / float(rate)
    except Exception:
        return 0.0


class ChatStreamView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser]

    def post(self, request, character_id):
        character = get_object_or_404(Character, pk=character_id)
        if not character.is_public and (
            not request.user.is_authenticated or character.creator_id != request.user.id
        ):
            return Response({'detail': '无权与该角色对话'}, status=status.HTTP_403_FORBIDDEN)

        body = request.data or {}
        message = (body.get('message') or '').strip()
        if not message:
            return Response({'detail': 'message 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        if not request.session.session_key:
            request.session.create()
        session_id = str(request.session.session_key or uuid.uuid4())
        chain = _get_or_build_chain(character, session_id)
        rag = get_rag_retriever(character)

        chat_session = _get_or_create_chat_session(character, request.user)
        history = _load_history_messages(chat_session)

        def generate():
            full = []
            for token in stream_chat(
                character,
                session_id,
                message,
                chain_dict=chain,
                rag_retriever=rag,
                history_messages=history,
            ):
                full.append(token)
                payload = json.dumps({'choices': [{'delta': {'content': token}}]}, ensure_ascii=False)
                yield f'data: {payload}\n\n'

            assistant_text = ''.join(full).strip()
            if assistant_text:
                _save_turn(chat_session, message, assistant_text)
            yield 'data: [DONE]\n\n'

        return StreamingHttpResponse(
            generate(),
            content_type='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
        )


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, character_id):
        character = get_object_or_404(Character, pk=character_id)
        if not character.is_public and character.creator_id != request.user.id:
            return Response({'detail': '无权访问该角色历史'}, status=status.HTTP_403_FORBIDDEN)

        items = [
            _serialize_message(m)
            for m in Message.objects.filter(
                session__character=character,
                session__user=request.user,
            ).order_by('created_at')
        ]
        return Response({'session_id': None, 'items': items, 'total': len(items)})


class ChatHistoryItemView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, character_id, message_id):
        character = get_object_or_404(Character, pk=character_id)
        if not character.is_public and character.creator_id != request.user.id:
            return Response({'detail': '无权删除该角色历史'}, status=status.HTTP_403_FORBIDDEN)

        message = get_object_or_404(
            Message,
            pk=message_id,
            session__character=character,
            session__user=request.user,
        )
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, character_id):
        character = get_object_or_404(Character, pk=character_id)
        if character.creator_id != request.user.id:
            return Response({'detail': '只能为自己的角色上传知识库文档'}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传 file 字段'}, status=status.HTTP_400_BAD_REQUEST)
        name = (file.name or '').lower()
        if not (name.endswith('.pdf') or name.endswith('.txt')):
            return Response({'detail': '仅支持 PDF 或 TXT'}, status=status.HTTP_400_BAD_REQUEST)

        result = ingest_document(str(character_id), file)
        if result.get('ok'):
            return Response(result)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class CharacterVoiceCloneView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, character_id):
        character = get_object_or_404(Character, pk=character_id)
        if character.creator_id != request.user.id:
            return Response({'detail': '只能为自己的角色克隆音色'}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传 wav 文件，字段名 file'}, status=status.HTTP_400_BAD_REQUEST)

        name = (file.name or '').lower()
        if not name.endswith('.wav'):
            return Response({'detail': '仅支持 .wav 音频'}, status=status.HTTP_400_BAD_REQUEST)

        wav_bytes = file.read()
        duration = _wav_duration_seconds(wav_bytes)
        if duration <= 0:
            return Response({'detail': '无法识别 wav 音频时长，请检查文件格式'}, status=status.HTTP_400_BAD_REQUEST)
        if duration < 10 or duration > 30:
            return Response({'detail': f'参考音频需 10~30 秒，当前约 {duration:.1f} 秒'}, status=status.HTTP_400_BAD_REQUEST)

        voice_name = (request.data.get('voice_name') or f'{character.name}-{request.user.username}').strip()
        description = (request.data.get('description') or '').strip()
        result = clone_voice_from_wav(
            wav_bytes=wav_bytes,
            filename=file.name or 'sample.wav',
            voice_name=voice_name,
            description=description,
        )
        if not result.get('ok'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        character.voice_id = result['voice_id']
        character.save(update_fields=['voice_id'])
        return Response(
            {
                'ok': True,
                'voice_id': result['voice_id'],
                'provider': result.get('provider', 'elevenlabs'),
                'character_id': str(character.id),
            }
        )
