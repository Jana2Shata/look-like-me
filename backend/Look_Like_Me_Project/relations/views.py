from django.db import transaction
from rest_framework import mixins, viewsets, generics
from rest_framework import status, permissions, exceptions
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from django.db.models import Prefetch, Q

from .querysets import annotate_friendship_status
from .models import MatchInteraction, Friendship,  BlockedUser
from .serializers import (
    SendFriendshipSerializer, ReceiveFriendshipSerializer,
    AcceptedFriendshipSerializer, BlockedUserSerializer
    )
from .mixins import MatchInteractionMixin, FriendshipRequestMixin
from auths.models import User
from globals.utils import exclude_blocked_users  


class LikesView(MatchInteractionMixin):
    type = 'like'

    def get_queryset(self):
        qs = super().get_queryset()
        # Annotate the related receiver User objects
        user_qs = annotate_friendship_status(
            User.objects.select_related('image'), self.request.user
        )
        return qs.prefetch_related(Prefetch('receiver', queryset=user_qs))


class SavesView(MatchInteractionMixin):
    type = 'save'

    def get_queryset(self):
        qs = super().get_queryset()
        user_qs = annotate_friendship_status(
            User.objects.select_related('image'), self.request.user
        )
        return qs.prefetch_related(Prefetch('receiver', queryset=user_qs))



class SenderFriendshipRequestView(FriendshipRequestMixin):

    serializer_class = SendFriendshipSerializer
    lookup_field = 'receiver__uid'       # traverse FK → User.uid
    lookup_url_kwarg = 'receiver'        # matches the URL capture group name

    def get_queryset(self):
        # Filter requests where the current user is the sender and status is pending
        qs = Friendship.objects.filter(sender=self.request.user, status='pending')
        # Exclude requests sent to users who are now blocked
        qs = exclude_blocked_users(qs, self.request.user, user_field='receiver_id')

        user_qs = annotate_friendship_status(
            User.objects.select_related('image'), self.request.user
        )
        return qs.prefetch_related(Prefetch('receiver', queryset=user_qs))

    def post(self, request, *args, **kwargs):
        return self.perform_create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.perform_delete(request, *args, message='Unsent friendship request successfully', **kwargs)


class ReceiverFriendshipRequestView(FriendshipRequestMixin):

    serializer_class = ReceiveFriendshipSerializer
    lookup_field = 'sender__uid'       # traverse FK → User.uid
    lookup_url_kwarg = 'sender'        # matches the URL capture group name

    def get_queryset(self):
        # Filter requests where the current user is the sender and status is pending
        qs = Friendship.objects.filter(receiver=self.request.user, status='pending')
        # Exclude incoming requests from blocked senders
        qs = exclude_blocked_users(qs, self.request.user, user_field='sender_id')

        user_qs = annotate_friendship_status(
            User.objects.select_related('image'), self.request.user
        )
        return qs.prefetch_related(Prefetch('sender', queryset=user_qs))

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.perform_delete(request, *args, message='Friendship request declined successfully', **kwargs)



class FriendshipView(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView):

    """
    A viewset for deleting and listing Friendship instances.
    """

    permission_classes = [permissions.IsAuthenticated] 
    serializer_class = AcceptedFriendshipSerializer
        

    def get_queryset(self):
        # Filter friendships where the current user is either the sender or the receiver, and status is 'accepted'
        qs = Friendship.objects.filter(
        # Q allows for more complex DB queries (beyond mere AND)
        # The pipe | performs OR, while simple comma , translates as AND
        Q(sender=self.request.user) | Q(receiver=self.request.user),
        status='accepted'
        )

        # Filter both sides of accepted friendships
        qs = exclude_blocked_users(qs, self.request.user, user_field='sender_id')
        qs = exclude_blocked_users(qs, self.request.user, user_field='receiver_id')

        user_qs = annotate_friendship_status(
            User.objects.select_related('image'), self.request.user
        )
        return qs.prefetch_related(
            Prefetch('sender', queryset=user_qs),
            Prefetch('receiver', queryset=user_qs),
        )


    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs) # provided by ListModelMixin


    def delete(self, request, *args, **kwargs):
        user_uid = kwargs.get('user')
        user = get_object_or_404(User, uid=user_uid)

        deleted_count, detailed_objects_count = self.get_queryset().filter(
            Q(receiver=user) | Q(sender=user)).delete() 
                # get_queryset already filters by type and sender, so we just need to filter by user here
                # Because of our established logic, where two users can never have more than one friendship record
                # between them, it's safe to use OR because the user can be either the sender or the receiver, but will
                # never appear more than once
                # queryset.delete calls pre and post deletion signals, but skips any overrirden model.delete(). it's fine here
        if not deleted_count:
            raise exceptions.NotFound(f"No existing friendship found with this user.")

        return Response({
            'detail':  f"Friendship cancelled successfully.",
        },
            status=status.HTTP_200_OK)
    


class BlockedUserView(
    mixins.ListModelMixin,
    generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BlockedUserSerializer

    def get_queryset(self):
        # Fetch only block records created by the logged-in user (the sender)
        return BlockedUser.objects.filter(sender=self.request.user).select_related('receiver', 'receiver__image')

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

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
        
        return Response(
            {'detail': "User blocked successfully."},
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, *args, **kwargs):
        receiver_uid = kwargs.get('receiver')
        receiver = get_object_or_404(User, uid=receiver_uid)

        deleted_count, detailed_objects_count = self.get_queryset().filter(receiver=receiver).delete()
        if not deleted_count:
            raise exceptions.NotFound("No block record found for this user.")

        return Response(
            {'detail': "User unblocked successfully."},
            status=status.HTTP_200_OK
        )

