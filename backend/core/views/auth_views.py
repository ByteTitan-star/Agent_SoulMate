from django.contrib.auth import login, logout, authenticate, get_user_model
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from ..serializers import UserSerializer
from ..services.default_characters import ensure_default_characters

User = get_user_model()


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AuthMeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            ensure_default_characters(request.user)
            return Response(UserSerializer(request.user).data)
        return Response(None)


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password')
        if not username or not password:
            return Response({'detail': '缺少用户名或密码'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({'detail': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        ensure_default_characters(user)
        get_token(request)
        return Response({'user': UserSerializer(user).data})


class AuthRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password')
        if not username or not password:
            return Response({'detail': '缺少用户名或密码'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'detail': '用户名已存在'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        ensure_default_characters(user)
        get_token(request)
        return Response({'user': UserSerializer(user).data})


class AuthLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({})
