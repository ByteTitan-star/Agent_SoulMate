import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


def character_avatar_path(instance, filename):
    return f'characters/{instance.id}/{filename}'


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('邮箱', blank=True)

    class Meta:
        db_table = 'users'


class Character(models.Model):
    GENDER_CHOICES = [('male', '男'), ('female', '女'), ('other', '其他')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('名称', max_length=64)
    gender = models.CharField('性别', max_length=16, choices=GENDER_CHOICES, default='other')
    avatar = models.ImageField('头像', upload_to=character_avatar_path, null=True, blank=True)
    system_prompt = models.TextField('系统提示词/背景设定')
    opening_message = models.TextField('开场白', default='', blank=True)
    personality = models.JSONField('性格标签', default=list)  # ["温柔","体贴"]
    voice_id = models.CharField('TTS 音色 ID', max_length=128, null=True, blank=True)
    is_public = models.BooleanField('公开到广场', default=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='characters', null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'characters'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions', null=True, blank=True
    )
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-created_at']


class Message(models.Model):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16, choices=[(ROLE_USER, '用户'), (ROLE_ASSISTANT, '助手')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']


class KnowledgeBase(models.Model):
    """角色专属知识库（RAG 集合）"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    character = models.OneToOneField(Character, on_delete=models.CASCADE, related_name='knowledge_base')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'knowledge_bases'


class DocumentChunk(models.Model):
    """上传文档后的分块记录，向量在 Milvus 中"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='chunks')
    source_file = models.CharField('来源文件名', max_length=255)
    chunk_index = models.IntegerField(default=0)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_chunks'
        ordering = ['knowledge_base', 'chunk_index']
