"""
URL routing configuration for chat conversations.
Registers `ConversationViewSet` with Django REST Framework's DefaultRouter 
to automatically generate standard RESTful endpoints for conversation threads.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet

# Initialize the DRF DefaultRouter and register conversation routes
router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
]