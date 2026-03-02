"""
RAG：文档入库（PDF/TXT）-> 切块 -> 本地 Milvus 向量库。
"""
from __future__ import annotations

import os
import tempfile
from typing import Optional, Dict, Any, List

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from ..models import Character, KnowledgeBase, DocumentChunk

try:
    from langchain_community.document_loaders import PyPDFLoader, TextLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_milvus import Milvus
    try:
        from langchain_community.embeddings import OllamaEmbeddings
    except ImportError:
        from langchain_ollama import OllamaEmbeddings

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


def _milvus_connection_args() -> Dict[str, Any]:
    """
    优先使用 MILVUS_URI；否则走 host/port。
    """
    uri = (getattr(settings, 'MILVUS_URI', '') or '').strip()
    if uri:
        return {'uri': uri}
    return {
        'host': getattr(settings, 'MILVUS_HOST', '127.0.0.1'),
        'port': str(getattr(settings, 'MILVUS_PORT', '19530')),
        'db_name': getattr(settings, 'MILVUS_DB_NAME', 'default'),
    }


def _collection_name(character_id: str) -> str:
    # Milvus collection 名称尽量避免特殊字符
    return f'char_{character_id.replace("-", "_")}'


def _get_embeddings():
    if not RAG_AVAILABLE:
        return None
    return OllamaEmbeddings(
        model=getattr(settings, 'OLLAMA_EMBED_MODEL', 'nomic-embed-text'),
        base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
    )


def _get_milvus_store(character_id: str):
    if not RAG_AVAILABLE:
        return None
    embeddings = _get_embeddings()
    if not embeddings:
        return None
    return Milvus(
        embedding_function=embeddings,
        collection_name=_collection_name(character_id),
        connection_args=_milvus_connection_args(),
        auto_id=True,
        drop_old=False,
    )


def get_rag_retriever(character, k: int = 4):
    """
    返回角色知识库 retriever；当角色没有文档时返回 None。
    """
    if not RAG_AVAILABLE or not character:
        return None
    has_kb = DocumentChunk.objects.filter(knowledge_base__character=character).exists()
    if not has_kb:
        return None
    try:
        store = _get_milvus_store(str(character.id))
        if not store:
            return None
        return store.as_retriever(search_kwargs={'k': k})
    except Exception:
        return None


def _load_file_content(upload: UploadedFile) -> List:
    """
    使用 LangChain Loader 解析 PDF/TXT。
    """
    if not RAG_AVAILABLE:
        return []

    suffix = os.path.splitext(upload.name or '')[1].lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fp:
        for chunk in upload.chunks():
            fp.write(chunk)
        local_path = fp.name
    try:
        if suffix == '.pdf':
            loader = PyPDFLoader(local_path)
        else:
            loader = TextLoader(local_path, encoding='utf-8', autodetect_encoding=True)
        return loader.load()
    finally:
        try:
            os.unlink(local_path)
        except Exception:
            pass


def ingest_document(character_id: str, upload: UploadedFile) -> dict:
    """
    将文档切块后写入 Milvus，并记录 DocumentChunk 元数据。
    返回 {'ok': True, 'chunks': n} 或 {'ok': False, 'error': str}
    """
    character = Character.objects.filter(pk=character_id).first()
    if not character:
        return {'ok': False, 'error': '角色不存在'}
    if not RAG_AVAILABLE:
        return {'ok': False, 'error': '缺少 Milvus/LangChain 依赖'}

    kb, _ = KnowledgeBase.objects.get_or_create(character=character)
    docs = _load_file_content(upload)
    if not docs:
        return {'ok': False, 'error': '无法解析文档内容'}

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        length_function=len,
    )
    splits = splitter.split_documents(docs)
    if not splits:
        return {'ok': False, 'error': '切块后为空'}

    source_name = upload.name or 'unknown'
    for i, doc in enumerate(splits):
        doc.metadata = {
            **(doc.metadata or {}),
            'character_id': str(character.id),
            'source': source_name,
            'chunk_index': i,
        }

    try:
        store = _get_milvus_store(str(character.id))
        if not store:
            return {'ok': False, 'error': 'Milvus 向量库初始化失败'}
        store.add_documents(splits)
    except Exception as exc:
        return {'ok': False, 'error': f'Milvus 写入失败: {exc}'}

    # 保存文本元数据，便于后台审计与管理
    DocumentChunk.objects.filter(knowledge_base=kb, source_file=source_name).delete()
    for i, doc in enumerate(splits):
        DocumentChunk.objects.create(
            knowledge_base=kb,
            source_file=source_name,
            chunk_index=i,
            content=doc.page_content[:10000],
        )

    return {'ok': True, 'chunks': len(splits), 'source_file': source_name}
