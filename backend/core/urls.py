from django.urls import path, include
from .views import (
    AuthMeView, AuthLoginView, AuthRegisterView, AuthLogoutView,
    CharacterListCreateView, CharacterMineView, CharacterDetailView,
    ChatStreamView, ChatHistoryView, ChatHistoryItemView, DocumentUploadView, CharacterVoiceCloneView,
)

# 1. 引入你新建的 stats_views 里面的函数
from .views.stats_views import get_chat_stats, get_topic_analysis

urlpatterns = [
    path('auth/', include([
        path('me/', AuthMeView.as_view()),
        path('login/', AuthLoginView.as_view()),
        path('register/', AuthRegisterView.as_view()),
        path('logout/', AuthLogoutView.as_view()),
    ])),
    
    # === 新增：数据洞察的 API 路由 ===
    path('stats/chat/', get_chat_stats),
    path('stats/analysis/', get_topic_analysis),
    # ===============================

    path('characters/', CharacterListCreateView.as_view()),
    path('characters/mine/', CharacterMineView.as_view()),
    path('characters/<uuid:pk>/', CharacterDetailView.as_view()),
    path('characters/<uuid:character_id>/voice-clone/', CharacterVoiceCloneView.as_view()),
    path('chat/<uuid:character_id>/stream/', ChatStreamView.as_view()),
    path('chat/<uuid:character_id>/history/', ChatHistoryView.as_view()),
    path('chat/<uuid:character_id>/history/<uuid:message_id>/', ChatHistoryItemView.as_view()),
    path('chat/<uuid:character_id>/documents/', DocumentUploadView.as_view()),
]