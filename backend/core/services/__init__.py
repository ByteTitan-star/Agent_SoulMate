try:
    from .llm_service import build_chain, stream_chat
except ImportError:
    def build_chain(*args, **kwargs):
        return None
    def stream_chat(*args, **kwargs):
        yield '（请安装 LangChain 并启动本地 Ollama）'
        return

try:
    from .rag_service import get_rag_retriever, ingest_document
except ImportError:
    def get_rag_retriever(*args, **kwargs):
        return None
    def ingest_document(*args, **kwargs):
        return {'ok': False, 'error': 'RAG 依赖未安装'}

from .tts_service import text_to_speech_bytes, clone_voice_from_wav
from .asr_service import speech_to_text

__all__ = [
    'build_chain', 'stream_chat',
    'get_rag_retriever', 'ingest_document',
    'text_to_speech_bytes', 'clone_voice_from_wav', 'speech_to_text',
]
