from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Character, ChatSession, Message, KnowledgeBase, DocumentChunk


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'is_public', 'creator', 'created_at')
    list_filter = ('gender', 'is_public')
    search_fields = ('name', 'system_prompt')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'character', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'content_preview', 'created_at')

    def content_preview(self, obj):
        return (obj.content or '')[:50] + '...' if len(obj.content or '') > 50 else (obj.content or '')
    content_preview.short_description = '内容'


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('character', 'created_at')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('knowledge_base', 'source_file', 'chunk_index', 'created_at')
