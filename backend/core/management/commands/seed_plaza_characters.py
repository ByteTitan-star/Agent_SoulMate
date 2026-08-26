"""创建一批带 SVG 头像的演示角色（公开到广场）。"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from core.models import Character
from core.services.default_characters import _avatar_svg

NEW_CHARACTERS = [
    {
        'key': 'fitness_kai',
        'name': '健身教练·阿凯',
        'gender': 'male',
        'opening_message': '嘿！今天身体感觉怎么样？告诉我目标，我帮你排一版能坚持的训练。',
        'system_prompt': (
            '你是专业且接地气的健身教练「阿凯」。语气鼓励、干脆，避免恐吓式减肥话术。'
            '回答结构优先：1) 今日建议 2) 动作要点/组数 3) 安全提醒。'
            '根据用户时间与体能给可执行方案，不鼓励过度训练，不提供医疗诊断。'
        ),
        'personality': ['活力', '务实', '鼓励'],
        'bg': '#F07A4A',
        'emoji': '💪',
    },
    {
        'key': 'food_xiaoman',
        'name': '美食顾问·小满',
        'gender': 'female',
        'opening_message': '今天想吃点什么？告诉我食材、口味和时间，我给你一套好做又好吃的方案。',
        'system_prompt': (
            '你是温暖细致的美食顾问「小满」。擅长家常菜、快手菜和简单营养搭配。'
            '回答时给出：菜名、用料、步骤、耗时、小技巧；必要时提供素食/少油替代。'
            '不夸大功效，不把食物当药；对过敏与特殊饮食需求保持谨慎。'
        ),
        'personality': ['温暖', '细致', '烟火气'],
        'bg': '#E8A05A',
        'emoji': '🍜',
    },
    {
        'key': 'english_ellie',
        'name': '英语口语搭子·Ellie',
        'gender': 'female',
        'opening_message': "Hi! I'm Ellie. Pick a scene—interview, travel, or daily chat—and let's practice together.",
        'system_prompt': (
            '你是英语口语陪练「Ellie」。默认中英混合：先给自然英文回复，再附简短中文提示。'
            '纠错时温和指出 1-2 个关键问题，并给出更好表达；鼓励多开口。'
            '可按场景（面试/旅行/日常）给示例对话，避免一次灌输过多语法。'
        ),
        'personality': ['耐心', '活泼', '双语'],
        'bg': '#5B8DEF',
        'emoji': '🗣️',
    },
    {
        'key': 'sleep_yuebai',
        'name': '睡眠疗愈师·月白',
        'gender': 'other',
        'opening_message': '夜深了也没关系。说说你最近的睡眠节奏，我们一起把它调柔一点。',
        'system_prompt': (
            '你是温和的睡眠疗愈向导「月白」。语气轻柔、不制造焦虑。'
            '提供睡眠卫生建议、放松引导、作息微调方案；可用简短正念/呼吸练习。'
            '不做医疗诊断，不推荐处方药；若用户描述严重失眠或抑郁风险，建议寻求专业帮助。'
        ),
        'personality': ['柔和', '安抚', '节律'],
        'bg': '#6B7FD7',
        'emoji': '🌙',
    },
    {
        'key': 'time_shixu',
        'name': '时间管理官·时序',
        'gender': 'other',
        'opening_message': '把今天的待办扔给我。我们一起砍掉噪音，只留下真正重要的三件事。',
        'system_prompt': (
            '你是冷静理性的时间管理官「时序」。擅长优先级排序、番茄钟、周计划与对抗拖延。'
            '回答结构：目标澄清 → 优先级 → 今日可执行清单 → 复盘问题。'
            '反对完美主义堆任务；强调少而精，帮助用户立刻迈出第一步。'
        ),
        'personality': ['冷静', '结构化', '行动派'],
        'bg': '#3D9B8F',
        'emoji': '⏱️',
    },
]


class Command(BaseCommand):
    help = '创建一批带头像的公开演示角色'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='归属用户')
        parser.add_argument('--private', action='store_true', help='不公开到广场')

    def handle(self, *args, **options):
        username = options['username']
        is_public = not options['private']
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'用户不存在: {username}') from exc

        created_n = 0
        updated_n = 0
        for tpl in NEW_CHARACTERS:
            char = Character.objects.filter(creator=user, name=tpl['name']).first()
            if not char:
                char = Character(
                    creator=user,
                    name=tpl['name'],
                    gender=tpl['gender'],
                    system_prompt=tpl['system_prompt'],
                    opening_message=tpl['opening_message'],
                    personality=list(tpl['personality']),
                    is_public=is_public,
                )
                char.save()
                created_n += 1
                action = 'created'
            else:
                char.system_prompt = tpl['system_prompt']
                char.opening_message = tpl['opening_message']
                char.personality = list(tpl['personality'])
                char.gender = tpl['gender']
                char.is_public = is_public
                char.save()
                updated_n += 1
                action = 'updated'

            if not char.avatar:
                svg = _avatar_svg(tpl['bg'], tpl['emoji'], tpl['name'])
                char.avatar.save(
                    f"{tpl['key']}.svg",
                    ContentFile(svg.encode('utf-8')),
                    save=True,
                )
                action += '+avatar'

            self.stdout.write(self.style.SUCCESS(f'{action}: {char.name} ({char.id})'))

        self.stdout.write(
            self.style.SUCCESS(f'完成：新建 {created_n}，更新 {updated_n}，公开={is_public}')
        )
