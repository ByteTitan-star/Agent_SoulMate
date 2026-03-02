from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Character, ChatSession, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email')

    def get_id(self, obj):
        return str(obj.pk)


class CharacterSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    creator_id = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)

    class Meta:
        model = Character
        fields = (
            'id', 'name', 'gender', 'avatar_url', 'system_prompt', 'opening_message', 'personality',
            'voice_id', 'is_public', 'creator_id', 'creator_name', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_id(self, obj):
        return str(obj.pk)

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_creator_id(self, obj):
        return str(obj.creator_id) if obj.creator_id else ''

    def get_creator_name(self, obj):
        return obj.creator.username if obj.creator else None
