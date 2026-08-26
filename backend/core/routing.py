# 前端通过 HTTP 访问后端 API 的 URL 路径
from django.urls import path

from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chat/<uuid:character_id>/', ChatConsumer.as_asgi()),
]
