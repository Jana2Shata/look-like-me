from django.shortcuts import render
from rest_framework import mixins, viewsets, generics
from rest_framework import status, permissions, exceptions
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404


from .models import MatchInteraction, Friendship,  BlockedUser
from .serializers import (
    SendFriendshipSerializer, ReceiveFriendshipSerializer
    )
from .mixins import MatchInteractionMixin, FriendshipRequestMixin
from auths.models import User


class LikesView(MatchInteractionMixin):
    type = 'like'


class SavesView(MatchInteractionMixin):
    type = 'save'



class SenderFriendshipRequestView(FriendshipRequestMixin):

    serializer_class = SendFriendshipSerializer
    lookup_field = 'receiver__uid'       # traverse FK → User.uid
    lookup_url_kwarg = 'receiver'        # matches the URL capture group name

    def get_queryset(self):
        # Filter requests where the current user is the sender and status is pending
        return Friendship.objects.filter(sender=self.request.user, status='pending')

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
        return Friendship.objects.filter(receiver=self.request.user, status='pending')

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.perform_delete(request, *args, message='Friendship request declined successfully', **kwargs)

