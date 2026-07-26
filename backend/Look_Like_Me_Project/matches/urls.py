from django.urls import include, path, re_path

from .views import (
    # ValidateFaceView,
    EmbedFaceView,
)

urlpatterns = [
    path('embed-face/', EmbedFaceView.as_view(), name='embed_face'),
]