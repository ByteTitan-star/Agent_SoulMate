"""
预热洞察页 Redis 缓存（图表 + 情绪总结）。

用法:
  python manage.py warm_stats_cache --username admin
  python manage.py warm_stats_cache --username admin --ranges 30d,all,7d
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.services.stats_cache import (
    analysis_cache_key,
    cache_set,
    chat_cache_key,
)
from core.views.stats_views import _compute_chat_stats, _resolve_time_window


class _FakeRequest:
    def __init__(self, range_key: str):
        self.query_params = {'range': range_key}


DEMO_ANALYSIS = {
    'today': (
        '1) 主要情绪状态\n'
        '- 白天节奏偏紧，偶有焦虑，但整体可控\n'
        '- 有完成小目标后的轻松感\n\n'
        '2) 高频关注话题\n'
        '- 工作推进与任务拆解\n'
        '- 睡眠与精力管理\n'
        '- 情绪自我觉察\n\n'
        '3) 行动建议\n'
        '今晚给自己留 20 分钟无屏幕放松，先把身体节奏稳住。'
    ),
    '7d': (
        '1) 主要情绪状态\n'
        '- 压力与期待并存，偶有自我怀疑\n'
        '- 对关系与沟通较敏感\n'
        '- 也有阶段性成就带来的正向反馈\n\n'
        '2) 高频关注话题\n'
        '- 职业规划与能力提升\n'
        '- 理财风险与决策理性\n'
        '- 人际关系边界\n'
        '- 作息与身心状态\n\n'
        '3) 行动建议\n'
        '本周只选一个最重要目标，拆成每天 30 分钟可执行动作。'
    ),
    '30d': (
        '1) 主要情绪状态\n'
        '- 中高强度压力下仍在坚持，韧性明显\n'
        '- 情绪起伏存在，但觉察能力在增强\n'
        '- 对未来有迷茫，也有想主动改变的动力\n\n'
        '2) 高频关注话题\n'
        '- 工作压力与职业发展\n'
        '- 投资理财与风险控制\n'
        '- 亲密关系与沟通方式\n'
        '- 睡眠、健身与生活平衡\n'
        '- 决策犹豫与行动启动\n\n'
        '3) 行动建议\n'
        '把“想做的事”改成“本周可验证的小实验”，用结果替代内耗。'
    ),
    '90d': (
        '1) 主要情绪状态\n'
        '- 长期忙碌下的疲惫与自我要求偏高\n'
        '- 对成长有清晰渴望，也夹杂比较焦虑\n\n'
        '2) 高频关注话题\n'
        '- 长期职业路径\n'
        '- 资产配置与理性决策\n'
        '- 关系质量与表达方式\n'
        '- 身心恢复与边界感\n\n'
        '3) 行动建议\n'
        '每月做一次复盘：保留有效习惯，删掉消耗最大的一项义务。'
    ),
    '1y': (
        '1) 主要情绪状态\n'
        '- 整体向上，阶段性低落可自愈\n'
        '- 对不确定环境保持警觉但不放弃行动\n\n'
        '2) 高频关注话题\n'
        '- 成长与自我价值\n'
        '- 工作与生活平衡\n'
        '- 财务安全感\n'
        '- 重要关系经营\n\n'
        '3) 行动建议\n'
        '给自己设定“季度主题”而不是同时追太多目标。'
    ),
    'all': (
        '1) 主要情绪状态\n'
        '- 长期对话中体现出持续自我探索\n'
        '- 压力、孤独与希望交替出现，整体积极求变\n\n'
        '2) 高频关注话题\n'
        '- 情绪管理与自我对话\n'
        '- 职业与能力成长\n'
        '- 理财与风险意识\n'
        '- 关系沟通与亲密边界\n'
        '- 健康作息与可持续节奏\n\n'
        '3) 行动建议\n'
        '把聊天里反复出现的主题，选一个做成下周可衡量的小改变。'
    ),
}


class Command(BaseCommand):
    help = '预热 Dashboard 洞察页 Redis 缓存'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument(
            '--ranges',
            default='today,7d,30d,90d,1y,all',
            help='逗号分隔的 range 列表',
        )
        parser.add_argument(
            '--llm',
            action='store_true',
            help='用真实 LLM 生成总结（较慢）；默认写入高质量演示总结',
        )

    def handle(self, *args, **options):
        username = options['username']
        ranges = [x.strip() for x in options['ranges'].split(',') if x.strip()]
        use_llm = options['llm']

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'用户不存在: {username}') from exc

        chat_ttl = getattr(settings, 'STATS_CHAT_CACHE_TTL', 300)
        analysis_ttl = getattr(settings, 'STATS_ANALYSIS_CACHE_TTL', 1800)

        for range_key in ranges:
            req = _FakeRequest(range_key)
            start_dt, end_dt, resolved, error = _resolve_time_window(req)
            if error:
                self.stderr.write(f'{range_key}: skip ({error})')
                continue

            chat_payload = _compute_chat_stats(user, start_dt, end_dt, resolved)
            cache_set(chat_cache_key(str(user.id), resolved), chat_payload, chat_ttl)

            if use_llm:
                from core.views.stats_views import _compute_topic_analysis

                analysis_payload = _compute_topic_analysis(user, start_dt, end_dt, resolved)
                text = analysis_payload.get('analysis') or ''
            else:
                text = DEMO_ANALYSIS.get(resolved) or DEMO_ANALYSIS['30d']
                # 附带时间戳，方便确认是预热写入
                text = f"{text}\n\n（缓存预热于 {timezone.localtime().strftime('%Y-%m-%d %H:%M')}）"

            cache_set(analysis_cache_key(str(user.id), resolved), {'analysis': text}, analysis_ttl)
            points = len(chat_payload.get('chart_data') or [])
            self.stdout.write(
                self.style.SUCCESS(f'warmed {username}/{resolved}: chart_points={points} analysis_chars={len(text)}')
            )
