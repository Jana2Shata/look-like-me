from auths.models import User
from chats.services import ChatService
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from globals.utils import exclude_blocked_users
from matches.querysets import annotate_similarity_score
from rest_framework import exceptions, generics, mixins, permissions, status
from rest_framework.response import Response

from .mixins import FriendshipRequestMixin, MatchInteractionMixin
from .models import BlockedUser, Friendship, MatchInteraction
from .querysets import annotate_friendship_status, annotate_user_interactions
from .serializers import (
    AcceptedFriendshipSerializer,
    BlockedUserSerializer,
    ReceiveFriendshipSerializer,
    SendFriendshipSerializer,
)


class LikesView(MatchInteractionMixin):
    """API view for listing and managing 'like' interactions sent by the authenticated user"""

    type = 'like'

    def get_queryset(self):
        """
        Retrieves sent 'like' interactions annotated with target user profiles, 
        friendship statuses, similarity scores, and reciprocal interaction flags.
        """
        user = self.request.user
        qs = super().get_queryset()

        # Annotate the related receiver User objects
        user_qs = annotate_friendship_status(
            User.objects.select_related('image', 'privacy_preferences'), user
        )
        user_qs = annotate_similarity_score(user_qs, user)
        user_qs = annotate_user_interactions(user_qs, user)

        return qs.prefetch_related(Prefetch('receiver', queryset=user_qs))


class SavesView(MatchInteractionMixin):
    """API view for listing and managing 'save' interactions sent by the authenticated user"""

    type = 'save'

    def get_queryset(self):
        """
        Retrieves sent 'save' interactions annotated with target user profiles, 
        friendship statuses, similarity scores, and reciprocal interaction flags
        """
        user = self.request.user
        qs = super().get_queryset()

        user_qs = annotate_friendship_status(
            User.objects.select_related('image', 'privacy_preferences'), user
        )
        user_qs = annotate_similarity_score(user_qs, user)
        user_qs = annotate_user_interactions(user_qs, user)

        return qs.prefetch_related(Prefetch('receiver', queryset=user_qs))


class SenderFriendshipRequestView(FriendshipRequestMixin):
    """API view for sending, listing, and unsending pending outgoing friendship requests"""

    serializer_class = SendFriendshipSerializer
    lookup_field = 'receiver__uid' # Traverse FK → User.uid
    lookup_url_kwarg = 'receiver' # Matches the URL capture group name

    def get_queryset(self):
        """Retrieves pending friendship requests sent by the authenticated user, excluding blocked users"""
        user = self.request.user
        qs = Friendship.objects.filter(sender=user, status='pending')
        qs = exclude_blocked_users(qs, user, user_field='receiver_id')

        user_qs = annotate_friendship_status(
            User.objects.select_related('image', 'privacy_preferences'), user
        )
        user_qs = annotate_similarity_score(user_qs, user)
        user_qs = annotate_user_interactions(user_qs, user)

        return qs.prefetch_related(Prefetch('receiver', queryset=user_qs)).order_by('-created_at', 'id')

    def post(self, request, *args, **kwargs):
        """Sends a new friendship request"""
        return self.perform_create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Cancels/unsends a pending outgoing friendship request"""
        return self.perform_delete(request, *args, message='Unsent friendship request successfully', **kwargs)


class ReceiverFriendshipRequestView(FriendshipRequestMixin):
    """API view for listing, accepting, and declining incoming pending friendship requests"""

    serializer_class = ReceiveFriendshipSerializer
    lookup_field = 'sender__uid' # Traverse FK → User.uid
    lookup_url_kwarg = 'sender' # Matches the URL capture group name

    def get_queryset(self):
        """Retrieves pending friendship requests received by the authenticated user, excluding blocked senders"""
        user = self.request.user
        qs = Friendship.objects.filter(receiver= user, status='pending')
        qs = exclude_blocked_users(qs, user, user_field='sender_id')

        user_qs = annotate_friendship_status(
            User.objects.select_related('image', 'privacy_preferences'), user
        )
        user_qs = annotate_similarity_score(user_qs, user)
        user_qs = annotate_user_interactions(user_qs, user)

        return qs.prefetch_related(Prefetch('sender', queryset=user_qs)).order_by('-created_at', 'id')

    def put(self, request, *args, **kwargs):
        """Accepts an incoming friendship request"""
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Declines (deletes) an incoming friendship request"""
        return self.perform_delete(request, *args, message='Friendship request declined successfully', **kwargs)


class FriendshipView(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView
):
    """API view for listing established friendships and un-friending (removing) connections"""

    permission_classes = [permissions.IsAuthenticated] 
    serializer_class = AcceptedFriendshipSerializer
        
    def get_queryset(self):
        """Retrieves accepted friendships where the current user is either sender or receiver"""
        user = self.request.user
        qs = Friendship.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status='accepted'
        )

        # Exclude accepted connections involving blocked users on either side
        qs = exclude_blocked_users(qs, user, user_field='sender_id')
        qs = exclude_blocked_users(qs, user, user_field='receiver_id')

        user_qs = annotate_friendship_status(
            User.objects.select_related('image', 'privacy_preferences'), user
        )
        user_qs = annotate_similarity_score(user_qs, user)
        user_qs = annotate_user_interactions(user_qs, user)

        return qs.prefetch_related(
            Prefetch('sender', queryset=user_qs),
            Prefetch('receiver', queryset=user_qs),
        ).order_by('-created_at', 'id')


    def get(self, request, *args, **kwargs):
        """Lists all established friendships"""
        return self.list(request, *args, **kwargs) # provided by ListModelMixin


    def delete(self, request, *args, **kwargs):
        """Terminates an existing friendship and revokes active chat access between the users"""
        user_uid = kwargs.get('user')
        user = get_object_or_404(User, uid=user_uid)

        deleted_count, _ = self.get_queryset().filter(
            Q(receiver=user) | Q(sender=user)).delete() 
        
        if not deleted_count:
            raise exceptions.NotFound(f"No existing friendship found with this user.")

        ChatService.revoke_chat_access_between_users(request.user, user)

        return Response({
            'detail':  f"Friendship cancelled successfully.",
        },
        status=status.HTTP_200_OK)
    

class BlockedUserView(
    mixins.ListModelMixin,
    generics.GenericAPIView
):
    """API view for listing, creating, and removing user block records"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BlockedUserSerializer

    def get_queryset(self):
        """Retrieves block records created by the authenticated user"""
        user = self.request.user

        receiver_qs = User.objects.select_related('image', 'privacy_preferences')
        receiver_qs = annotate_friendship_status(receiver_qs, user)
        receiver_qs = annotate_similarity_score(receiver_qs, user)

        # Fetch only block records created by the logged-in user (the sender)
        return BlockedUser.objects.filter(sender=user).prefetch_related(
            Prefetch('receiver', queryset=receiver_qs)
        ).order_by('-created_at', 'id')

    def get(self, request, *args, **kwargs):
        """Lists all blocked users"""
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Creates a block record within an atomic transaction, cleaning up 
        all existing friendships, match interactions, and revoking real-time chat access upon commit
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        sender = request.user
        receiver = serializer.validated_data['receiver']

        with transaction.atomic():
            serializer.save()

            # Clean up all existing relationships upon block
            Friendship.objects.filter(
                Q(sender=sender, receiver=receiver) | Q(sender=receiver, receiver=sender)
            ).delete()

            MatchInteraction.objects.filter(
                Q(sender=sender, receiver=receiver) | Q(sender=receiver, receiver=sender)
            ).delete()
            
            # Revoke chat access only after the transaction successfully commits
            transaction.on_commit(
                lambda: ChatService.revoke_chat_access_between_users(sender, receiver)
            )
        
        return Response(
            {'detail': "User blocked successfully."},
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, *args, **kwargs):
        """Removes a block record (unblocks a user)"""
        receiver_uid = kwargs.get('receiver')
        receiver = get_object_or_404(User, uid=receiver_uid)

        deleted_count, _ = self.get_queryset().filter(receiver=receiver).delete()
        if not deleted_count:
            raise exceptions.NotFound("No block record found for this user.")

        return Response(
            {'detail': "User unblocked successfully."},
            status=status.HTTP_200_OK
        )

