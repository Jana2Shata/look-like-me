from auths.serializers import MinimalUserProfileSerializer
from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    """
    Serializes individual message instances
    Includes computed conversation UIDs and safely serializes sender profiles, 
    returning an unavailable placeholder if the sender is blocked by the viewer
    """
    conversation_uid = serializers.UUIDField(source='conversation.uid', read_only=True)
    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['uid', 'conversation_uid', 'sender', 'content', 'created_at']

    def get_sender(self, obj):
        """Serializes the message sender, substituting a placeholder if blocked"""
        blocked_user_ids = self.context.get('blocked_user_ids', set())

        if obj.sender_id in blocked_user_ids:
            return MinimalUserProfileSerializer.get_unavailable_payload(compact=True)
        
        return MinimalUserProfileSerializer(obj.sender, context={**self.context, 'compact': True}).data
    

class ConversationListSerializer(serializers.ModelSerializer):
    """
    Serializes conversation threads for inbox list views
    Includes dynamic computation and prefetch optimization for the other participant, 
    the latest message, and unread message counts
    """
    
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['uid', 'updated_at', 'other_participant', 'last_message', 'unread_count']

    def get_other_participant(self, obj):
        """Identifies and serializes the other participant in a direct conversation thread"""

        request = self.context.get('request')
        user = request.user if request else None

        participant = next((p for p in obj.participants.all() if p.user_id != (user.id if user else None)), None)

        if not participant or not participant.user:
            return None

        blocked_user_ids = self.context.get('blocked_user_ids', set())

        if participant.user_id in blocked_user_ids:
            return MinimalUserProfileSerializer.get_unavailable_payload(compact=True)
        
        return MinimalUserProfileSerializer(participant.user, context={**self.context, 'compact': True}).data
    
    def get_last_message(self, obj):
        """Retrieves the most recent message, leveraging pre-fetched data if available."""

        messages = getattr(obj, 'prefetched_messages', None)
        if messages is not None:
            return MessageSerializer(messages[0], context=self.context).data if messages else None
        
        # Fallback if accessed outside ConversationViewSet
        latest = obj.messages.filter(deleted_at__isnull=True).order_by('-created_at').first()
        return MessageSerializer(latest, context=self.context).data if latest else None
    
    def get_unread_count(self, obj):
        """Calculates unread messages for the active user based on their last read timestamp"""

        if hasattr(obj, 'unread_count'):
            return obj.unread_count

        # Fallback if accessed outside ConversationViewSet
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        
        user = request.user
        user_participant = next((p for p in obj.participants.all() if p.user_id == user.id), None)

        if not user_participant:
            return 0
        
        qs = obj.messages.filter(deleted_at__isnull=True).exclude(sender_id=user.id)

        if user_participant.last_read_at:
            qs = qs.filter(created_at__gt=user_participant.last_read_at)

        return qs.count()

class SendMessageSerializer(serializers.Serializer):
    """Validates payload data required to dispatch a new chat message"""

    conversation_uid = serializers.UUIDField(required=False, allow_null=True)
    recipient_uid = serializers.UUIDField(required=False, allow_null=True)
    content = serializers.CharField(max_length=5000)

    def validate(self, attrs):
        """Ensures that either an existing conversation target or recipient target is provided"""
        if not attrs.get('conversation_uid') and not attrs.get('recipient_uid'):
            raise serializers.ValidationError("Either conversation_uid or recipient_uid is required.")
        return attrs