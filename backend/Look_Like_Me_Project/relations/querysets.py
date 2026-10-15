from django.db.models import Exists, OuterRef, Q
from .models import Friendship, MatchInteraction

def annotate_friendship_status(queryset, user):
    """
    Annotates a user queryset with boolean flags representing the friendship relationship 
    between each target user and the requesting user:
    - is_friends: True if an accepted friendship exists in either direction
    - is_pending_sent: True if the requesting user sent a pending friend request to the target
    - is_pending_received: True if the target user sent a pending friend request to the requesting user

    Args:
        queryset: The Django queryset of User objects to annotate
        user: The requesting user

    Returns:
        QuerySet: The annotated queryset containing friendship state booleans
    """
    if not user or not user.is_authenticated:
        return queryset

    # Subquery for accepted friendships in either direction (bidirectional check)
    friends_qs = Friendship.objects.filter(
        Q(sender=OuterRef('pk'), receiver=user) |
        Q(sender=user, receiver=OuterRef('pk')),
        status='accepted',
    )

    # Subquery for pending friend requests sent by the requesting user
    pending_sent_qs = Friendship.objects.filter(
        sender=user,
        receiver=OuterRef('pk'),
        status='pending',
    )

    # Subquery for pending friend requests received from the target user
    pending_received_qs = Friendship.objects.filter(
        sender=OuterRef('pk'),
        receiver=user,
        status='pending',
    )

    return queryset.annotate(
        is_friends=Exists(friends_qs),
        is_pending_sent=Exists(pending_sent_qs),
        is_pending_received=Exists(pending_received_qs),
    )


def annotate_user_interactions(queryset, user):
    """
    Annotates a user queryset with interaction flags indicating whether 
    the requesting user has 'liked' or 'saved' each target user

    Args:
        queryset: The Django queryset of User objects to annotate
        user: The requesting user interacting with the targets

    Returns:
        QuerySet: The annotated queryset containing 'is_liked' and 'is_saved' boolean flags
    """
    user_interactions = MatchInteraction.objects.filter(
        sender=user,
        receiver=OuterRef('pk')
    )
    
    return queryset.annotate(
        is_liked=Exists(user_interactions.filter(type='like')),
        is_saved=Exists(user_interactions.filter(type='save'))
    )