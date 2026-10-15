import uuid
from django.db import models

from auths.models import User


class Conversation(models.Model):
    """
    Thin anchor table providing a unique identity for a conversation thread.
    Participants and messages reference this via Foreign Keys. 
    Designed to be minimal and extensible for future group chat support without schema changes.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Enables fast chats sorting

    def __str__(self):
        return f'Conversation {self.id}'
    

class ConversationParticipant(models.Model):
    """
    Junction table mapping users to conversations.
    Tracks participant read state (last_read_at) and enforces uniqueness 
    to prevent duplicate user entries per conversation
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participants', # how to access this ConversationParticipant of a Conversation obiect
        verbose_name='conversation participant', 
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        null=True,
        related_name='conversations',
        verbose_name='conversation participant user',
        
    )

    last_read_at = models.DateTimeField(
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'user'],
                name='unique_conversation_participant'
            )
        ]
    
    def __str__(self):
        return f'User {self.user} in Conversation {self.conversation_id}'
    

class Message(models.Model):
    """
    Represents an individual chat message belonging to a conversation
    Supports soft deletion via 'deleted_at' timestamps and includes a composite 
    index for optimal message history retrieval performance
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE, # deleting a conversation deletes all its messages
        related_name='messages',
        verbose_name='message conversation',
    )

    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
        verbose_name='message sender',
        
    )

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=['conversation', 'created_at'],
                name='idx_messages_conversation',
            ), # Composite index optimized for fetching conversation messages ordered by time
        ]

    def __str__(self):
        return f'Message {self.id} from {self.sender} in Conversation {self.conversation_id} \n[Content: {self.content[:30]}...]'