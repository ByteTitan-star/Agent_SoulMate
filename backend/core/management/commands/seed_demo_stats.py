"""
为数据洞察页注入可演示的假聊天数据（默认挂到 admin 用户）。

用法:
  python manage.py seed_demo_stats
  python manage.py seed_demo_stats --username admin --total 2500 --days 180
  python manage.py seed_demo_stats --clear
"""

from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Character, ChatSession, Message

USER_LINES = [
    '最近工作压力有点大，晚上总是睡不着。',
    '我想聊聊职业规划，感觉自己卡在原地了。',
    '今天市场波动很大，我有点焦虑要不要减仓。',
    '和朋友吵架了，心里挺难受的，不知道怎么和好。',
    '我想开始健身，但总是坚持不下去，有什么建议吗？',
    '周末想出去走走，你有没有轻松一点的放松方式？',
    '我在准备面试，总担心答不好行为面试题。',
    '感觉自己情绪起伏比较大，早上还好下午就低落。',
    '最近在看投资理财，想了解一下风险控制。',
    '我想提升沟通能力，在团队里总是说不清楚想法。',
    '对未来有点迷茫，不知道该不该换城市发展。',
    '今天天气不错，心情也好一点了，想分享一下。',
    '我好像有点过度思考，小事也能纠结很久。',
    '帮我分析一下这段关系里我是不是太敏感了。',
    '想学习新技能，Python 和产品哪个更适合我现在？',
    '最近睡眠质量变差，白天注意力也不集中。',
    '我有点害怕失败，所以很多事情迟迟不敢开始。',
    '今天和同事协作挺顺利的，想总结一下经验。',
    '我对理财收益预期有点高，怕自己不够理性。',
    '想聊聊如何平衡工作和生活，感觉一直在赶工。',
    '最近看新闻有点焦虑，世界变化太快了。',
    '我想练习表达感激，你觉得怎么开口比较自然？',
    '有时候会突然很孤独，哪怕身边有人也一样。',
    '我想设定一个可执行的周计划，别再半途而废。',
    '对恋爱关系有点不确定，想听听更冷静的视角。',
    '今天完成了一个小目标，其实挺开心的。',
    '我担心自己不够优秀，总拿别人的进度比较。',
    '想了解如何做决策更果断，别再反复摇摆。',
    '最近胃口不太好，可能是情绪影响到身体了。',
    '我想重建自信，从哪些小事开始比较合适？',
]

ASSISTANT_LINES = [
    '我听到了你的感受。我们先把问题拆小一点，一次只处理一件事。',
    '这很正常，很多人都会有类似的纠结。你愿意说说最让你卡住的点吗？',
    '可以先从低成本试错开始：设定一个两周实验，再根据结果调整。',
    '你的情绪是有信号的，它在提醒你需要休息或重新对齐目标。',
    '我们一起看看：事实、感受、行动，这三层分别是什么。',
    '你已经在觉察了，这本身就是进步。下一步可以更具体一点。',
    '如果把期待调到“今天完成 20%”，压力会小很多，也更容易坚持。',
    '我建议你先记录三件可控的事，再决定要不要扩大行动范围。',
    '听起来你其实很在意这段关系/这份工作，我们可以把需求说清楚。',
    '先呼吸一下。你不是一个人面对这些，我们可以慢慢理顺。',
]


class Command(BaseCommand):
    help = '为 Dashboard 洞察页生成演示用聊天消息'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='目标用户名')
        parser.add_argument('--total', type=int, default=2500, help='总消息条数（用户+助手合计）')
        parser.add_argument('--days', type=int, default=180, help='分布到过去多少天')
        parser.add_argument('--sessions', type=int, default=24, help='会话数量')
        parser.add_argument('--clear', action='store_true', help='先清空该用户会话与消息再生成')

    def handle(self, *args, **options):
        username = options['username']
        total = options['total']
        days = options['days']
        session_count = options['sessions']
        clear = options['clear']

        if total < 100:
            raise CommandError('total 建议至少 100')
        if days < 7:
            raise CommandError('days 建议至少 7')

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'用户不存在: {username}') from exc

        characters = list(Character.objects.filter(is_public=True).order_by('created_at')[:8])
        if not characters:
            characters = list(Character.objects.order_by('created_at')[:8])
        if not characters:
            raise CommandError('库中没有任何角色，无法生成会话')

        if clear:
            deleted_sessions, _ = ChatSession.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING(f'已清空用户会话相关数据: {deleted_sessions}'))

        now = timezone.now()
        rng = random.Random(42)

        # 让近端时间更密，远端更疏，方便各时间档都有曲线差异
        weights = []
        for day_offset in range(days):
            # day_offset=0 是今天，权重最高
            w = 1.0 / (1.0 + day_offset * 0.035)
            weights.append(w)
        weight_sum = sum(weights)

        with transaction.atomic():
            sessions = []
            for i in range(session_count):
                character = characters[i % len(characters)]
                created = now - timedelta(days=rng.randint(0, days - 1), hours=rng.randint(0, 20))
                session = ChatSession(user=user, character=character, created_at=created)
                sessions.append(session)
            ChatSession.objects.bulk_create(sessions)
            sessions = list(ChatSession.objects.filter(user=user).order_by('-created_at')[:session_count])

            messages: list[Message] = []
            remaining = total
            # 每会话消息数大致均匀，略有波动
            base = max(remaining // len(sessions), 2)
            for idx, session in enumerate(sessions):
                if remaining <= 0:
                    break
                n = base if idx < len(sessions) - 1 else remaining
                n = min(n, remaining)
                # 保证偶数，方便 user/assistant 成对
                if n % 2 == 1:
                    n -= 1
                if n < 2:
                    n = 2 if remaining >= 2 else remaining

                for j in range(n):
                    # 按权重抽一天
                    r = rng.random() * weight_sum
                    acc = 0.0
                    day_offset = 0
                    for d, w in enumerate(weights):
                        acc += w
                        if r <= acc:
                            day_offset = d
                            break

                    created_at = now - timedelta(
                        days=day_offset,
                        hours=rng.randint(8, 23),
                        minutes=rng.randint(0, 59),
                        seconds=rng.randint(0, 59),
                    )
                    # 同会话内略作顺序偏移，避免完全同秒
                    created_at = created_at - timedelta(seconds=(n - j))

                    if j % 2 == 0:
                        role = Message.ROLE_USER
                        content = USER_LINES[rng.randint(0, len(USER_LINES) - 1)]
                    else:
                        role = Message.ROLE_ASSISTANT
                        content = ASSISTANT_LINES[rng.randint(0, len(ASSISTANT_LINES) - 1)]

                    messages.append(
                        Message(
                            session=session,
                            role=role,
                            content=content,
                            created_at=created_at,
                        )
                    )
                remaining -= n

            Message.objects.bulk_create(messages, batch_size=500)

        # bulk_create 对 auto_now_add 可能忽略传入值，二次校准时间
        to_fix = list(Message.objects.filter(session__user=user).order_by('id'))
        # 若时间几乎全是“现在”，重新铺开
        if to_fix:
            sample = to_fix[:50]
            newest = max(m.created_at for m in sample)
            oldest = min(m.created_at for m in sample)
            if (newest - oldest) < timedelta(days=2):
                updates = []
                for m in to_fix:
                    r = rng.random() * weight_sum
                    acc = 0.0
                    day_offset = 0
                    for d, w in enumerate(weights):
                        acc += w
                        if r <= acc:
                            day_offset = d
                            break
                    m.created_at = now - timedelta(
                        days=day_offset,
                        hours=rng.randint(8, 23),
                        minutes=rng.randint(0, 59),
                        seconds=rng.randint(0, 59),
                    )
                    updates.append(m)
                Message.objects.bulk_update(updates, ['created_at'], batch_size=500)

        final_count = Message.objects.filter(session__user=user).count()
        user_count = Message.objects.filter(session__user=user, role=Message.ROLE_USER).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'完成：用户={username} 会话≈{session_count} 消息={final_count}（用户消息={user_count}）'
            )
        )
