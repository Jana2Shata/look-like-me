import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ConversationParticipant
from .models import Conversation
from globals.utils import exclude_blocked_users


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.conversation_uid = self.scope['url_route']['kwargs']['conversation_uid']
        self.room_group_name = f'chat_{self.conversation_uid}'

        is_participant = await self.verify_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        action = content.get('action')

        if action == 'typing':

            is_valid_room = await self.verify_participant()
            if not is_valid_room:
                await self.close(code=4003)
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_event',
                    'sender_uid': str(self.user.uid),
                    'is_typing': content.get('is_typing', False)
                }
            )

    async def chat_message_event(self, event):
        await self.send_json({
            'action': 'new_message',
            'data': event['message']
        })

    async def message_deleted_event(self, event):
        await self.send_json({
            'action': 'message_deleted',
            'message_uid': event['message_uid']
        })

    async def typing_event(self, event):
        if event['sender_uid'] != str(self.user.uid):
            await self.send_json({
                'action': 'user_typing',
                'sender_uid': event['sender_uid'],
                'is_typing': event['is_typing']
            })

    @database_sync_to_async
    def verify_participant(self):
        qs = Conversation.objects.filter(
            uid=self.conversation_uid,
            participants__user=self.user
        )

        qs = exclude_blocked_users(
            qs,
            user=self.user,
            user_field='participants__user__id'
        )

        return qs.exists()
