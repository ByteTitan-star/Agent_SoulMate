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


from .asr_service import speech_to_text
from .tts_service import clone_voice_from_wav, text_to_speech_bytes

__all__ = [
    'build_chain',
    'clone_voice_from_wav',
    'get_rag_retriever',
    'ingest_document',
    'speech_to_text',
    'stream_chat',
    'text_to_speech_bytes',
]
