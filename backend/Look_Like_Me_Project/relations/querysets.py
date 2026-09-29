
from django.db.models import Q, OuterRef, Exists
from .models import Friendship
from .models import MatchInteraction

def annotate_friendship_status(queryset, user):

    if not user or not user.is_authenticated:
        return queryset

    friends_qs = Friendship.objects.filter(
        Q(sender=OuterRef('pk'), receiver=user) |
        Q(sender=user, receiver=OuterRef('pk')),
        status='accepted',
    )

    pending_sent_qs = Friendship.objects.filter(
        sender=user,
        receiver=OuterRef('pk'),
        status='pending',
    )

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

    user_interactions = MatchInteraction.objects.filter(
        sender=user,
        receiver=OuterRef('pk')
    )
    
    return queryset.annotate(
        is_liked=Exists(user_interactions.filter(type='like')),
        is_saved=Exists(user_interactions.filter(type='save'))
    )