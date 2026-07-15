from django.db import models
from auths.models import User
import uuid

# Create your models here.
class Friendship(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests',
        verbose_name='friendship request sender',
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_friend_requests',
        verbose_name='friendship request receiver',
    )

    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        # 'declined' is not stored — record is deleted on decline

    status = models.CharField(
        max_length=10, # for memory i guess
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                name='unique_friendship_pair'
                # Prevents duplicate friend requests from the same user
            )
        ]
    
    def __str__(self):
        return f'{self.sender} → {self.receiver} [{self.status}]'


class MatchInteraction(models.Model):
    """
    Tracks likes and saves between users.
    """

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_interactions',
        verbose_name='interaction sender',
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_interactions',
        verbose_name='interaction receiver',
    )

    class TypeChoices(models.TextChoices):
        LIKE = 'like', 'Like'
        SAVE = 'save', 'Save'

    type = models.CharField(
        max_length=4,
        choices=TypeChoices.choices,
    )


    created_at = models.DateTimeField(auto_now_add=True)

    deleted_at = models.DateTimeField(
        null=True,
        # Soft delete: null means not deleted, timestamp means when it was deleted
    )



    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver', 'type'],
                name='unique_sender_receiver_type'
                )
        ]

    def __str__(self):
        return f'{self.sender} {self.type}d {self.receiver}'
    



class BlockedUser(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocking',
        verbose_name='blocker',
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by', # CONSIDER: this should not be accessible!! HOW!!
        verbose_name='blocked user',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                name='unique_block_pair'
                )
        ]

        indexes = [
            models.Index(fields=['receiver'], name='idx_blocked_id'),
        ] # Extra index on receiver_id:
          # needed to check "has this user been blocked by anyone?" efficiently
        

    def __str__(self):
        return f'{self.sender} blocked {self.receiver}'