
from django.db.models import Q, OuterRef, Exists
from relations.models import Friendship

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