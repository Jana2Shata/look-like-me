from django.urls import include, path, re_path

from .views import (
    # ValidateFaceView,
    EmbedFaceView,
    MatchesFeed,
    TempMatchesFeed,
)

from auths.views import PublicUserDetailView

urlpatterns = [
    path('embed-face/', EmbedFaceView.as_view(), name='embed_face'),
    path('feed/', MatchesFeed.as_view(), name='matches_feed'),
    path('feed/<int:id>/', TempMatchesFeed.as_view(), name='temp_matches_feed'),
    path('users/<uid>/', PublicUserDetailView.as_view(), name='user-detail'),
]