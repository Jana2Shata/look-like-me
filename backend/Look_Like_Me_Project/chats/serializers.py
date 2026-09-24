from rest_framework import serializers
from .models import Conversation, ConversationParticipant, Message
from auths.serializers import MinimalUserProfileSerializer


class MessageSerializer(serializers.ModelSerializer):
    conversation_uid = serializers.UUIDField(source='conversation.uid', read_only=True)
    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['uid', 'conversation_uid', 'sender', 'content', 'created_at']

    def get_sender(self, obj):

        blocked_user_ids = self.context.get('blocked_user_ids', set())

        if obj.sender_id in blocked_user_ids:
            return MinimalUserProfileSerializer.get_unavailable_payload()
        
        return MinimalUserProfileSerializer(obj.sender, context=self.context).data
    

class ConversationListSerializer(serializers.ModelSerializer):

    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['uid', 'updated_at', 'other_participant', 'last_message', 'unread_count']

    def get_other_participant(self, obj):

        request = self.context.get('request')
        user = request.user if request else None

        participant = next((p for p in obj.participants.all() if p.user_id != (user.id if user else None)), None)

        if not participant or not participant.user:
            return None

        blocked_user_ids = self.context.get('blocked_user_ids', set())

        if participant.user_id in blocked_user_ids:
            return MinimalUserProfileSerializer.get_unavailable_payload()
        
        return MinimalUserProfileSerializer(participant.user, context=self.context).data
    
    def get_last_message(self, obj):

        messages = getattr(obj, 'prefetched_messages', None)
        if messages is None:
            messages = obj.messages.filter(deleted_at__isnull=True).order_by('-created_at')[:1]
        
        latest = messages[0] if messages else None
        return MessageSerializer(latest, context=self.context).data if latest else None

    def get_unread_count(self, obj):
            
            request = self.context.get('request')
            if not request:
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

    conversation_uid = serializers.UUIDField(required=False, allow_null=True)
    recipient_uid = serializers.UUIDField(required=False, allow_null=True)
    content = serializers.CharField(max_length=5000)

    def validate(self, attrs):
        if not attrs.get('conversation_uid') and not attrs.get('recipient_uid'):
            raise serializers.ValidationError("Either conversation_uid or recipient_uid is required.")
        return attrs