from datetime import timedelta
from typing import Optional

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from langchain_core.messages import HumanMessage

from ..models import Message
from ..services.llm_service import _get_llm


PRESET_RANGE_DAYS = {
    'today': 1,
    '7d': 7,
    '30d': 30,
    '90d': 90,
    '1y': 365,
    # 兼容旧参数
    'day': 1,
    'week': 7,
    'month': 30,
    'quarter': 90,
    'year': 365,
}


def _parse_query_datetime(value: Optional[str], *, end_of_day: bool = False):
    """解析查询参数中的日期/时间，兼容 YYYY-MM-DD 与 ISO datetime。"""
    if not value:
        return None

    dt = parse_datetime(value)
    if dt is None:
        d = parse_date(value)
        if d is None:
            return None
        if end_of_day:
            dt = timezone.datetime.combine(d, timezone.datetime.max.time().replace(microsecond=999999))
        else:
            dt = timezone.datetime.combine(d, timezone.datetime.min.time())

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _resolve_time_window(request):
    """统一计算起止时间。返回 (start_dt, end_dt, range_key, error_message)。"""
    range_key = (request.query_params.get('range') or '30d').strip().lower()
    start_dt = _parse_query_datetime(request.query_params.get('startDate'), end_of_day=False)
    end_dt = _parse_query_datetime(request.query_params.get('endDate'), end_of_day=True)

    now = timezone.now()

    # 优先使用预设范围
    if range_key in PRESET_RANGE_DAYS:
        days = PRESET_RANGE_DAYS[range_key]
        if end_dt is None:
            end_dt = now
        start_dt = end_dt - timedelta(days=days - 1)
    elif range_key == 'all':
        # 全部数据允许不传时间
        pass
    elif start_dt and end_dt:
        # 兼容未定义 range、但传了时间窗口的情况
        range_key = 'custom'
    else:
        # 兜底默认近 30 天
        range_key = '30d'
        end_dt = now
        start_dt = end_dt - timedelta(days=29)

    if start_dt and end_dt and start_dt > end_dt:
        return None, None, range_key, 'startDate 不能晚于 endDate'

    return start_dt, end_dt, range_key, None


def _build_range_label(range_key: str, start_dt, end_dt) -> str:
    if range_key == 'today':
        return '今天'
    if range_key == '7d':
        return '近7天'
    if range_key == '30d':
        return '近30天'
    if range_key == '90d':
        return '近90天'
    if range_key == '1y':
        return '近1年'
    if range_key == 'all':
        return '全部数据'

    if start_dt and end_dt:
        return f"{start_dt.strftime('%Y-%m-%d')} 至 {end_dt.strftime('%Y-%m-%d')}"
    return '最近一段时间'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_stats(request):
    """互动频次统计：按时间范围聚合消息条数。"""
    user = request.user
    start_dt, end_dt, range_key, error = _resolve_time_window(request)
    if error:
        return Response({'detail': error}, status=400)

    filters = {'session__user': user}
    if start_dt is not None:
        filters['created_at__gte'] = start_dt
    if end_dt is not None:
        filters['created_at__lte'] = end_dt

    qs = Message.objects.filter(**filters)

    # 时间跨度较大时，按月聚合避免图表过密
    if start_dt and end_dt:
        span_days = max((end_dt.date() - start_dt.date()).days + 1, 1)
    else:
        span_days = 9999
    use_month_bucket = range_key in {'1y', 'year', 'all'} or span_days > 120

    bucket_expr = TruncMonth('created_at') if use_month_bucket else TruncDate('created_at')
    rows = (
        qs.annotate(bucket=bucket_expr)
        .values('bucket')
        .annotate(count=Count('id'))
        .order_by('bucket')
    )

    chart_data = []
    for item in rows:
        bucket = item.get('bucket')
        if bucket is None:
            continue
        chart_data.append(
            {
                'date': bucket.strftime('%Y-%m') if use_month_bucket else bucket.strftime('%Y-%m-%d'),
                'count': item.get('count', 0),
            }
        )

    return Response(
        {
            'chart_data': chart_data,
            'meta': {
                'range': range_key,
                'label': _build_range_label(range_key, start_dt, end_dt),
                'bucket': 'month' if use_month_bucket else 'day',
                'startDate': start_dt.isoformat() if start_dt else None,
                'endDate': end_dt.isoformat() if end_dt else None,
            },
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_topic_analysis(request):
    """按时间范围提取用户消息并调用大模型做情绪/话题总结。"""
    user = request.user
    start_dt, end_dt, range_key, error = _resolve_time_window(request)
    if error:
        return Response({'detail': error}, status=400)

    filters = {
        'session__user': user,
        'role': Message.ROLE_USER,
    }
    if start_dt is not None:
        filters['created_at__gte'] = start_dt
    if end_dt is not None:
        filters['created_at__lte'] = end_dt

    recent_messages = Message.objects.filter(**filters).order_by('-created_at')[:120]
    if not recent_messages:
        return Response({'analysis': '该时间范围内暂无足够聊天记录用于分析。'})

    # 反转后按时间正序拼接，提高总结稳定性
    ordered_messages = list(reversed(list(recent_messages)))
    chat_texts = '\n'.join([m.content for m in ordered_messages if (m.content or '').strip()])
    if not chat_texts.strip():
        return Response({'analysis': '该时间范围内暂无足够聊天记录用于分析。'})

    llm = _get_llm(streaming=False)
    if not llm:
        return Response({'analysis': '分析服务暂不可用，请稍后重试。'})

    range_label = _build_range_label(range_key, start_dt, end_dt)
    prompt = (
        '你是一位温和、专业的心理与沟通分析助手。\n'
        f'请基于用户在「{range_label}」的聊天内容，输出：\n'
        '1) 主要情绪状态（2-3点）\n'
        '2) 高频关注话题（3-5点）\n'
        '3) 一句温和的行动建议\n\n'
        '要求：\n'
        '- 使用简洁中文\n'
        '- 分点输出\n'
        '- 不要编造未出现的信息\n\n'
        f'【聊天片段】\n{chat_texts}'
    )

    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        analysis_text = (getattr(resp, 'content', '') or '').strip()
        if not analysis_text:
            analysis_text = '该时间范围内暂无可总结的稳定主题。'
        return Response({'analysis': analysis_text})
    except Exception:
        return Response({'analysis': '分析服务暂时繁忙，请稍后点击刷新重试。'})
