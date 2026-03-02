from __future__ import annotations

from django.core.files.base import ContentFile

from ..models import Character


DEFAULT_CHARACTER_TEMPLATES = [
    {
        'key': 'weather',
        'name': '晴空天气官',
        'gender': 'other',
        'opening_message': '我是你的天气助手，告诉我城市即可。',
        'system_prompt': (
            '你是一个天气查询角色，语气清晰简洁。'
            '当用户询问天气时，优先给出结论，再给出温度与出行建议。'
        ),
        'personality': ['系统角色', '工具代理', '天气'],
        'bg': '#7AA8FF',
        'emoji': '☀',
    },
    {
        'key': 'news',
        'name': '今日资讯官',
        'gender': 'other',
        'opening_message': '我可以帮你速览热点与新闻。',
        'system_prompt': (
            '你是资讯检索角色。遇到新闻类提问时，先给要点摘要，再列出来源链接。'
            '保持客观，避免杜撰。'
        ),
        'personality': ['系统角色', '工具代理', '资讯'],
        'bg': '#6FC7A8',
        'emoji': '📰',
    },
    {
        'key': 'knowledge',
        'name': '知识库馆长',
        'gender': 'other',
        'opening_message': '把文档交给我，我来帮你检索与归纳。',
        'system_prompt': (
            '你是知识库检索角色。优先基于上传文档回答，引用命中片段，'
            '在信息不足时明确说明。'
        ),
        'personality': ['系统角色', '工具代理', '知识库'],
        'bg': '#C48DFF',
        'emoji': '📚',
    },
]


def _avatar_svg(bg: str, emoji: str, title: str) -> str:
    # 简洁头像：纯色背景 + emoji + 角色简称
    short_title = (title or '')[:2]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{bg}" />
      <stop offset="100%" stop-color="#222222" stop-opacity="0.20" />
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="96" fill="url(#g)" />
  <text x="256" y="238" text-anchor="middle" font-size="120" dominant-baseline="middle">{emoji}</text>
  <text x="256" y="360" text-anchor="middle" font-size="64" font-family="Arial, sans-serif" fill="white">{short_title}</text>
</svg>"""


def ensure_default_characters(user):
    """
    登录后为当前用户确保存在 3 个系统角色（天气/资讯/知识库）。
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return

    for tpl in DEFAULT_CHARACTER_TEMPLATES:
        char = Character.objects.filter(creator=user, name=tpl['name']).first()
        created = False
        if not char:
            char = Character(
                creator=user,
                name=tpl['name'],
                gender=tpl['gender'],
                system_prompt=tpl['system_prompt'],
                opening_message=tpl['opening_message'],
                personality=list(tpl['personality']),
                is_public=False,
            )
            created = True

        changed = False
        if not char.system_prompt:
            char.system_prompt = tpl['system_prompt']
            changed = True
        if not char.opening_message:
            char.opening_message = tpl['opening_message']
            changed = True
        if not char.personality:
            char.personality = list(tpl['personality'])
            changed = True

        if created:
            char.save()

        if not char.avatar:
            svg = _avatar_svg(tpl['bg'], tpl['emoji'], tpl['name'])
            char.avatar.save(
                f"default_{tpl['key']}.svg",
                ContentFile(svg.encode('utf-8')),
                save=False,
            )
            changed = True

        if changed:
            char.save()
