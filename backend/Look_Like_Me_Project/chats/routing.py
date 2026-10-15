"""
WebSocket URL routing configuration
Maps incoming WebSocket connection paths to their respective ASGI consumers
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Routes chat WebSocket connections, capturing the conversation UUID in the URL route kwargs
    re_path(r'^ws/chat/(?P<conversation_uid>[^/.]+)/$', consumers.ChatConsumer.as_asgi()),
]