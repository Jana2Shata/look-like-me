from django.urls import include, path, re_path

from .views import (
    ValidateFaceView,
    EmbedFaceView,
)

urlpatterns = [
    path('validate-face/', ValidateFaceView.as_view(), name='validate_face'),
    path('embed-face/', EmbedFaceView.as_view(), name='embed_face'),
]