# 角色管理视图。处理与 AI 伴侣角色相关的 API 请求，比如获取角色列表、创建自定义角色、修改角色设定（Prompt）等
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from ..models import Character
from ..serializers import CharacterSerializer


def _to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


class CharacterListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        # 统一处理前端常见的占位字符串，避免 search=undefined 导致广场被过滤为空
        search_raw = (request.query_params.get('search') or '').strip()
        search = '' if search_raw.lower() in ('undefined', 'null') else search_raw

        is_public_raw = request.query_params.get('is_public', 'true')
        only_public = _to_bool(is_public_raw) if str(is_public_raw).lower() not in ('undefined', 'null') else True

        qs = Character.objects.select_related('creator')
        if only_public:
            qs = qs.filter(is_public=True)

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(opening_message__icontains=search)
                | Q(system_prompt__icontains=search)
            )
        serializer = CharacterSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': '请先登录'}, status=status.HTTP_403_FORBIDDEN)
        if not request.user.can_create_character:
            return Response({'detail': '您没有创建角色的权限'}, status=status.HTTP_403_FORBIDDEN)
        is_public_raw = request.data.get('is_public', request.POST.get('is_public', False))
        data = {
            'name': request.data.get('name') or request.POST.get('name'),
            'gender': request.data.get('gender') or request.POST.get('gender', 'other'),
            'system_prompt': request.data.get('system_prompt') or request.POST.get('system_prompt', ''),
            'opening_message': request.data.get('opening_message') or request.POST.get('opening_message', ''),
            'personality': request.data.get('personality') or request.POST.get('personality'),
            'voice_id': request.data.get('voice_id') or request.POST.get('voice_id') or None,
            'is_public': _to_bool(is_public_raw),
        }
        if isinstance(data['personality'], str):
            import json
            try:
                data['personality'] = json.loads(data['personality']) if data['personality'] else []
            except json.JSONDecodeError:
                data['personality'] = [p.strip() for p in (data['personality'] or '').split(',') if p.strip()]
        publish_blocked = False
        if data['is_public'] and not request.user.can_publish_character:
            data['is_public'] = False
            publish_blocked = True
        serializer = CharacterSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        char = serializer.save(creator=request.user)
        if request.FILES.get('avatar'):
            char.avatar = request.FILES['avatar']
            char.save(update_fields=['avatar'])
        response_data = CharacterSerializer(char, context={'request': request}).data
        if publish_blocked:
            response_data = dict(response_data)
            response_data['publish_blocked'] = True
        return Response(response_data, status=status.HTTP_201_CREATED)


class CharacterMineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Character.objects.filter(creator=request.user).select_related('creator')
        serializer = CharacterSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class CharacterDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, pk):
        char = get_object_or_404(Character, pk=pk)
        if not char.is_public and (not request.user.is_authenticated or char.creator_id != request.user.id):
            return Response({'detail': '无权访问'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CharacterSerializer(char, context={'request': request}).data)

    def patch(self, request, pk):
        char = get_object_or_404(Character, pk=pk)
        if not request.user.is_authenticated or char.creator_id != request.user.id:
            return Response({'detail': '无权修改'}, status=status.HTTP_403_FORBIDDEN)
        # 检查是否尝试将 is_public 改为 True
        new_is_public = request.data.get('is_public') if 'is_public' in request.data else request.POST.get('is_public')
        if new_is_public is not None:
            if _to_bool(new_is_public) and not request.user.can_publish_character:
                return Response({'detail': '您没有发布角色的权限'}, status=status.HTTP_403_FORBIDDEN)
        for key in ('name', 'gender', 'system_prompt', 'opening_message', 'personality', 'voice_id', 'is_public'):
            has_key = key in request.data
            val = request.data.get(key) if has_key else request.POST.get(key)
            if val is not None:
                if key == 'personality' and isinstance(val, str):
                    import json
                    try:
                        val = json.loads(val) if val else []
                    except json.JSONDecodeError:
                        val = [p.strip() for p in (val or '').split(',') if p.strip()]
                if key == 'is_public':
                    val = _to_bool(val)
                setattr(char, key, val)
        if request.FILES.get('avatar'):
            char.avatar = request.FILES['avatar']
        char.save()
        return Response(CharacterSerializer(char, context={'request': request}).data)

    def delete(self, request, pk):
        char = get_object_or_404(Character, pk=pk)
        if not request.user.is_authenticated or char.creator_id != request.user.id:
            return Response({'detail': '无权删除'}, status=status.HTTP_403_FORBIDDEN)
        char.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
