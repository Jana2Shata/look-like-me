
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import (
    LikesView, SavesView
)

# router = DefaultRouter()
# router.register(r'likes', LikesViewSet, basename='like')
# urlpatterns = router.urls

urlpatterns = [
    path('likes/', LikesView.as_view(), name='likes'),
    path('saves/', SavesView.as_view(), name='saves'),
]