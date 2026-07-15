from django.db import models
from auths.models import User
import uuid

class Conversation(models.Model):
    """
    Thin anchor table — identity for a conversation thread.
    Participants and messages hang off this via FK.
    Intentionally minimal: supports group chats later with no schema change.
    """
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'Conversation {self.id}'
    

class ConversationParticipant(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participants', # how to access this ConversationParticipant of a Conversation obiect
        verbose_name='conversation participant', 
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
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

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE, # deleting a conversation deletes all its messages
        related_name='messages',
        verbose_name='message conversation',
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='message sender',
        # OR (for soft delete):
        # on_delete=models.SET_NULL,
        # null=True,
        
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
            ), # Composite index for the most common query:
                # fetch all messages in a conversation ordered by time
        ]

    def __str__(self):
        return f'Message {self.id} from {self.sender} in Conversation {self.conversation_id} \n[Content: {self.content[:30]}...]'