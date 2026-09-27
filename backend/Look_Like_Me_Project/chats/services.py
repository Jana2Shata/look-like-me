from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from auths.models import User
from rest_framework.exceptions import PermissionDenied, ValidationError
from globals.utils import exclude_blocked_users 
from relations.models import Friendship
from .models import Conversation, ConversationParticipant, Message

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from .serializers import MessageSerializer

class ChatService:

    @staticmethod
    def validate_can_chat(sender, receiver):
        if sender.id == receiver.id:
            raise ValidationError("You cannot message yourself.")

        is_accessible = exclude_blocked_users(
            User.objects.filter(id=receiver.id),
            user=sender,
            user_field='id'
        ).exists()

        if not is_accessible:
            raise PermissionDenied("Messaging is unavailable between these users.")

        if not Friendship.objects.filter(status=Friendship.StatusChoices.ACCEPTED).filter(
            Q(sender=sender, receiver=receiver) | Q(sender=receiver, receiver=sender)
        ).exists():
            raise PermissionDenied("You can only message accepted friends.")

    @staticmethod
    @database_sync_to_async
    def validate_consumer_access(user, conversation_uid):

        if not user or not user.is_authenticated:
            return False

        try:
            conversation = Conversation.objects.filter(
                participants__user=user,
                uid=conversation_uid
            ).first()

            if not conversation:
                return False

            other_participant = conversation.participants.exclude(user=user).select_related('user').first()
            if not other_participant:
                return False

            ChatService.validate_can_chat(user, other_participant.user)
            return True

        except (ValidationError, PermissionDenied):
            return False
        except Exception:
            return False

    @staticmethod
    def send_message(sender, content, recipient_uid=None, conversation_uid=None, request=None):
        if not recipient_uid and not conversation_uid:
            raise ValidationError("Either recipient_uid or conversation_uid must be provided.")

        with transaction.atomic():

            if conversation_uid:
                conversation = get_object_or_404(
                    Conversation.objects.filter(participants__user=sender),
                    uid=conversation_uid
                )
                other_participant = conversation.participants.exclude(user=sender).select_related('user').first()
                if other_participant:
                    ChatService.validate_can_chat(sender, other_participant.user)
            else:
                recipient = get_object_or_404(User, uid=recipient_uid)
                ChatService.validate_can_chat(sender, recipient)

                first_id, second_id = sorted([sender.id, recipient.id])
                list(User.objects.select_for_update().filter(id__in=[first_id, second_id]).order_by('id'))

                conversation = Conversation.objects.filter(
                    participants__user=sender
                ).filter(
                    participants__user=recipient
                ).first()

                if not conversation:
                    conversation = Conversation.objects.create()
                    ConversationParticipant.objects.bulk_create([
                        ConversationParticipant(conversation=conversation, user=sender),
                        ConversationParticipant(conversation=conversation, user=recipient),
                    ])

            message = Message.objects.create(
                conversation=conversation,
                sender=sender,
                content=content
            )
            conversation.save(update_fields=['updated_at'])

            serialized_data = MessageSerializer(message, context={'request': request}).data
            conversation_room = f"chat_{conversation.uid}"

            # Broadcar deletion event via webSocket
            transaction.on_commit(
                lambda: async_to_sync(get_channel_layer().group_send)(
                    conversation_room,
                    {
                        "type": "chat_message_event",
                        "message": serialized_data,
                    }
                )
            )
        return message

    @staticmethod
    def delete_own_message(user, message_uid):
        message = get_object_or_404(Message, uid=message_uid)

        if message.sender_id != user.id:
            raise PermissionDenied("You can only delete your own messages.")

        if message.deleted_at is not None:
            raise ValidationError("Message is already deleted.")

        message.deleted_at = timezone.now()
        message.save(update_fields=['deleted_at'])

        conversation_room = f"chat_{message.conversation.uid}"
        serialized_uid = str(message.uid)

        # Broadcar deletion event via webSocket

        async_to_sync(get_channel_layer().group_send)(
            conversation_room,
            {
                "type": "message_deleted_event",
                "message_uid": serialized_uid,
            }
        )

        return message

    @staticmethod
    def revoke_chat_access_between_users(user_a, user_b):

        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        conversation = Conversation.objects.filter(
            participants__user=user_a
        ).filter(
            participants__user=user_b
        ).first()

        if conversation:
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.uid}",
                {
                    "type": "access_revoked",
                    "user_uids": [str(user_a.uid), str(user_b.uid)],
                }
            )

    @staticmethod
    def revoke_all_user_sockets(user):

        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        async_to_sync(channel_layer.group_send)(
            f"user_{user.uid}",
            {
                "type": "user_logout",
            }
        )