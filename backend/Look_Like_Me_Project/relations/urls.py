
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import (
    LikesView, SavesView,
    SenderFriendshipRequestView, ReceiverFriendshipRequestView
)

# router = DefaultRouter()
# router.register(r'likes', LikesViewSet, basename='like')
# urlpatterns = router.urls

urlpatterns = [
    path('likes/', LikesView.as_view(), name='likes'),
    path('likes/<uuid:receiver>/', LikesView.as_view(), name='likes-detail'),

    path('saves/', SavesView.as_view(), name='saves'),
    path('saves/<uuid:receiver>/', SavesView.as_view(), name='saves-detail'),

    path('sender-friendship-requests/', SenderFriendshipRequestView.as_view(), name='sender-friendship-requests'),
    path('sender-friendship-requests/<uuid:receiver>/', SenderFriendshipRequestView.as_view(), name='sender-friendship-requests-detail'),

    path('receiver-friendship-requests/', ReceiverFriendshipRequestView.as_view(), name='receiver-friendship-requests'),
    path('receiver-friendship-requests/<uuid:sender>/', ReceiverFriendshipRequestView.as_view(), name='receiver-friendship-requests-detail'),
]