"""洞察页统计结果 Redis/本地缓存。"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def chat_cache_key(user_id: str, range_key: str) -> str:
    return f'stats:chat:{user_id}:{range_key}'


def analysis_cache_key(user_id: str, range_key: str) -> str:
    return f'stats:analysis:{user_id}:{range_key}'


def _want_refresh(request) -> bool:
    raw = (request.query_params.get('refresh') or '').strip().lower()
    return raw in {'1', 'true', 'yes'}


def cache_get(key: str) -> Any | None:
    try:
        return cache.get(key)
    except Exception as exc:
        logger.warning('cache get failed key=%s err=%s', key, exc)
        return None


def cache_set(key: str, value: Any, timeout: int) -> None:
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as exc:
        logger.warning('cache set failed key=%s err=%s', key, exc)


def get_or_compute_chat(request, user_id: str, range_key: str, compute):
    """读取图表缓存；refresh=1 时强制重算。"""
    key = chat_cache_key(str(user_id), range_key)
    if not _want_refresh(request):
        hit = cache_get(key)
        if hit is not None:
            payload = dict(hit)
            meta = dict(payload.get('meta') or {})
            meta['cached'] = True
            payload['meta'] = meta
            return payload

    payload = compute()
    ttl = getattr(settings, 'STATS_CHAT_CACHE_TTL', 300)
    cache_set(key, payload, ttl)
    out = dict(payload)
    meta = dict(out.get('meta') or {})
    meta['cached'] = False
    out['meta'] = meta
    return out


def get_or_compute_analysis(request, user_id: str, range_key: str, compute):
    """读取情绪总结缓存；refresh=1 时强制重算。"""
    key = analysis_cache_key(str(user_id), range_key)
    if not _want_refresh(request):
        hit = cache_get(key)
        if hit is not None:
            payload = dict(hit)
            payload['cached'] = True
            return payload

    payload = compute()
    # 仅缓存有效总结，避免把临时错误长期锁死
    text = (payload.get('analysis') or '').strip()
    skip_markers = ('暂不可用', '暂时繁忙', '请稍后')
    if text and not any(m in text for m in skip_markers):
        ttl = getattr(settings, 'STATS_ANALYSIS_CACHE_TTL', 1800)
        cache_set(key, {'analysis': text}, ttl)
    out = dict(payload)
    out['cached'] = False
    return out
