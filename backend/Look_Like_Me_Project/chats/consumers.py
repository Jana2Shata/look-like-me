from urllib.parse import parse_qs
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .services import ChatService   

class ChatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get('user')
        
        # store session_key on connect
        session = self.scope.get('session')
        self.session_key = session.session_key if session else None

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        query_string = parse_qs(self.scope.get('query_string', b'').decode('utf8'))
        expected_account_uid = query_string.get('account_uid', [None])[0]

        if not expected_account_uid:
            await self.close(code=4000)
            return

        if str(self.user.uid) != expected_account_uid:
            await self.close(code=4003)
            return

        self.conversation_uid = self.scope['url_route']['kwargs']['conversation_uid']
        self.room_group_name = f'chat_{self.conversation_uid}'

        can_access, close_code = await ChatService.validate_consumer_access(
            self.user, 
            self.conversation_uid, 
            session_key=self.session_key
        )
        if not can_access:
            await self.close(code=close_code)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.channel_layer.group_add(
            f"user_{self.user.uid}",
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.channel_layer.group_discard(
                f"user_{self.user.uid}",
                self.channel_name
            )

    async def access_revoked(self, event):

        revoked_uids = event.get("user_uids", [])

        if str(self.user.uid) in revoked_uids:
            await self.close(code=4003)


    async def user_logout(self, event):

        await self.close(code=4001) 

    async def receive_json(self, content):
        action = content.get('action')

        if action == 'typing':

            can_access, close_code = await ChatService.validate_consumer_access(
                self.user,
                self.conversation_uid,
                session_key=self.session_key
            )
            if not can_access:
                await self.close(code=close_code)
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

        can_access, code = await ChatService.validate_consumer_access(
            self.user, 
            self.conversation_uid,
            session_key=self.session_key
        )
        
        if not can_access:
            await self.close(code=code)
            return
        
        await self.send_json({
            'action': 'new_message',
            'data': event['message']
        })

    async def message_deleted_event(self, event):

        can_access, code = await ChatService.validate_consumer_access(
            self.user, 
            self.conversation_uid,
            session_key=self.session_key
        )
        
        if not can_access:
            await self.close(code=code)
            return
        
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