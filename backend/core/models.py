# 定义了数据库中的表结构
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# 角色头像上传路径：按角色 ID 分目录存储
def character_avatar_path(instance, filename):
    return f'characters/{instance.id}/{filename}'


class User(AbstractUser):
    """
    自定义用户模型，继承 Django 的 AbstractUser
    """

    # 使用 UUID 作为主键，自动生成，不可编辑
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('邮箱', blank=True)  # 邮箱字段，可为空
    is_admin = models.BooleanField('超级管理员', default=False)
    can_create_character = models.BooleanField('可创建角色', default=True)
    can_publish_character = models.BooleanField('可发布角色', default=True)

    class Meta:
        db_table = 'users'  # 指定数据库表名


class Character(models.Model):
    """
    角色模型：代表一个 AI 角色，包含基本信息和设定
    """

    GENDER_CHOICES = [('male', '男'), ('female', '女'), ('other', '其他')]

    # UUID 主键
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('名称', max_length=64)  # 角色名称
    gender = models.CharField('性别', max_length=16, choices=GENDER_CHOICES, default='other')  # 性别，可选
    avatar = models.ImageField('头像', upload_to=character_avatar_path, null=True, blank=True)  # 头像图片
    system_prompt = models.TextField('系统提示词/背景设定')  # 角色的系统提示词，用于定义角色行为
    opening_message = models.TextField('开场白', default='', blank=True)  # 对话开始时的欢迎语
    personality = models.JSONField('性格标签', default=list)  # 性格标签列表，如 ["温柔","体贴"]
    voice_id = models.CharField('TTS 音色 ID', max_length=128, null=True, blank=True)  # 语音合成音色标识
    is_public = models.BooleanField('公开到广场', default=False)  # 是否公开给所有用户
    # 创建者：关联到用户，可为空（如系统预置角色）
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='characters', null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间
    updated_at = models.DateTimeField(auto_now=True)  # 更新时间

    class Meta:
        db_table = 'characters'  # 数据库表名
        ordering = ['-created_at']  # 按创建时间倒序排列

    def __str__(self):
        return self.name


class ChatSession(models.Model):
    """
    对话会话：记录用户与某个角色的对话历史
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID 主键
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions', null=True, blank=True
    )  # 所属用户，可为空（匿名会话）
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='sessions')  # 关联的角色
    created_at = models.DateTimeField(auto_now_add=True)  # 会话创建时间

    class Meta:
        db_table = 'chat_sessions'  # 数据库表名
        ordering = ['-created_at']  # 按创建时间倒序排列


class Message(models.Model):
    """
    消息模型：会话中的单条消息
    """

    ROLE_USER = 'user'  # 用户消息
    ROLE_ASSISTANT = 'assistant'  # AI 助手消息

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID 主键
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')  # 所属会话
    role = models.CharField(max_length=16, choices=[(ROLE_USER, '用户'), (ROLE_ASSISTANT, '助手')])  # 消息角色
    content = models.TextField()  # 消息内容
    created_at = models.DateTimeField(auto_now_add=True)  # 消息创建时间

    class Meta:
        db_table = 'messages'  # 数据库表名
        ordering = ['created_at']  # 按创建时间正序排列（对话顺序）


class KnowledgeBase(models.Model):
    """
    知识库模型：与角色一对一关联，用于 RAG 检索
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID 主键
    character = models.OneToOneField(Character, on_delete=models.CASCADE, related_name='knowledge_base')  # 所属角色
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间

    class Meta:
        db_table = 'knowledge_bases'  # 数据库表名


class DocumentChunk(models.Model):
    """
    文档分块模型：存储上传文档的分块内容，向量存储在 Milvus 中
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID 主键
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='chunks')  # 所属知识库
    source_file = models.CharField('来源文件名', max_length=255)  # 原始文件名
    chunk_index = models.IntegerField(default=0)  # 分块索引
    content = models.TextField()  # 分块文本内容
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间

    class Meta:
        db_table = 'document_chunks'  # 数据库表名
        ordering = ['knowledge_base', 'chunk_index']  # 按知识库和索引排序
