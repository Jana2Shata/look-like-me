from django.db.models import Q
from .models import PrivacyPreference
from relations.models import Friendship


def filter_privacy_visible_users(queryset, user):
    """
    Keep users if:
    1. their profile is PUBLIC
    2. their profile is HIDDEN BUT they are accepted friends with the requesting user
    """
    friend_ids_pairs = Friendship.objects.filter(
        Q(sender=user, status=Friendship.StatusChoices.ACCEPTED) | 
        Q(receiver=user, status=Friendship.StatusChoices.ACCEPTED)
    ).values_list('sender_id', 'receiver_id')

    accepted_friend_ids = {
        id for pair in friend_ids_pairs for id in pair if id != user.id
    }

    return queryset.filter(
        Q(privacy_preferences__profile_visibility=PrivacyPreference.ProfileVisibility.PUBLIC) |
        Q(privacy_preferences__isnull=True) | 
        Q(
            privacy_preferences__profile_visibility=PrivacyPreference.ProfileVisibility.HIDDEN,
            id__in=accepted_friend_ids
        )
    )

def filter_privacy_visible_users(queryset, user):
    """
    Keep users if:
    1. Their profile is PUBLIC
    2. Their profile is HIDDEN but they are accepted friends
        with the requesting user
    3. They have no PrivacyPreference record (default = PUBLIC)
    """

    friend_ids_pairs = Friendship.objects.filter(
        Q(sender=user, status=Friendship.StatusChoices.ACCEPTED
        )|
        Q(receiver=user, status=Friendship.StatusChoices.ACCEPTED
        )
    ).values_list('sender_id', 'receiver_id')

    accepted_friend_ids = {
        friend_id
        for pair in friend_ids_pairs
        for friend_id in pair
        if friend_id != user.id
    }

    return queryset.filter(
        Q(privacy_preferences__profile_visibility=PrivacyPreference.ProfileVisibility.PUBLIC)|
        Q(privacy_preferences__isnull=True)|
        Q(  privacy_preferences__profile_visibility=PrivacyPreference.ProfileVisibility.HIDDEN,
            id__in=accepted_friend_ids
        )
    )