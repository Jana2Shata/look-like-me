from django.db import models
from auths.models import User
import uuid

# Create your models here.
class PrivacyPreference(models.Model):

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class ProfileVisibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        HIDDEN = 'hidden', 'Hidden'

    class MatchVisibility(models.TextChoices):
        EVERYONE = 'everyone', 'Everyone'
        FRIENDS_ONLY = 'friends_only', 'Friends Only'
        ME_ONLY = 'me_only', 'Me Only'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='privacy_preferences',
        verbose_name='privacy preference owner',
    )

    profile_visibility = models.CharField(
        max_length=10,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
    )

    match_visibility = models.CharField(
        max_length=12,
        choices=MatchVisibility.choices,
        default=MatchVisibility.EVERYONE,
    )

    updated_at = models.DateTimeField(auto_now=True)
   

    def __str__(self):
        return f'Privacy settings for {self.user}\n[Profile Visibility: {self.profile_visibility}\nMatch Visibility: {self.match_visibility}]'
