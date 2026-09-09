
from relations.models import BlockedUser
from rest_framework import serializers


def exclude_blocked_users(queryset, user, user_field='id'):
    """
    bi-directionally excludes blocked users from any user querySet
    """
    if not user or user.is_anonymous:
        return queryset

    blocked_by_me = BlockedUser.objects.filter(sender=user).values_list('receiver_id', flat=True)
    blocked_me = BlockedUser.objects.filter(receiver=user).values_list('sender_id', flat=True)

    all_blocked_ids = set(blocked_by_me).union(set(blocked_me))

    return queryset.exclude(**{f"{user_field}__in": all_blocked_ids})


class NonBlockedUserSlugField(serializers.SlugRelatedField):
    """
    Automatically filters out blocked users during payload validation
    """
    def get_queryset(self):

        qs = super().get_queryset()
        request = self.context.get('request')
        
        if request and request.user and request.user.is_authenticated:
            return exclude_blocked_users(qs, request.user, user_field=self.slug_field)
            
        return qs

# Source - https://stackoverflow.com/a/74504921
# Posted by Alvaro Rodriguez Scelza
# Retrieved 2026-08-14, License - CC BY-SA 4.0


