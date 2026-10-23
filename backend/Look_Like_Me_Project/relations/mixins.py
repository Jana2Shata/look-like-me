from auths.models import User
from django.shortcuts import get_object_or_404
from globals.utils import exclude_blocked_users
from rest_framework import exceptions, generics, mixins, permissions, status
from rest_framework.response import Response

from auths.permissions import IsProfileComplete
from .models import MatchInteraction
from .serializers import MatchInteractionSerializer 

class MatchInteractionMixin(
    mixins.ListModelMixin,
    generics.GenericAPIView
):
    """
    Reusable mixin providing listing, creation, and deletion endpoints 
    for specific types of match interactions (e.g., 'like' or 'save').
    Subclasses must define the `type` attribute
    """

    permission_classes = [permissions.IsAuthenticated, IsProfileComplete] 
    serializer_class = MatchInteractionSerializer
    type = None  # This should be set in the subclass to either 'like' or 'save'    

    def get_queryset(self):
        """
        Retrieves interactions where the current user is the sender and the type matches 'self.type'
        Excludes interactions with blocked receivers
        """
        qs = MatchInteraction.objects.filter(sender=self.request.user, type=self.type)
        qs = exclude_blocked_users(qs, self.request.user, user_field='receiver_id')

        return qs.order_by('-created_at', 'id')


    def get(self, request, *args, **kwargs):
        """Lists all match interactions of the specified type"""
        return self.list(request, *args, **kwargs) # provided by ListModelMixin


    def post(self, request, *args, **kwargs):
        """Creates a new match interaction combining request data with the subclass-defined type"""
        data = {
            'receiver': request.data.get('receiver'),
            'type': self.type
        }
        # Merge request data with subclass type while preserving request context for sender injection
        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': f"{self.type.capitalize()}d successfully.",},
            status=status.HTTP_201_CREATED
        )


    def delete(self, request, *args, **kwargs):
        """Deletes a match interaction based on the receiver's UID"""
        receiver_uid = kwargs.get('receiver')
        receiver = get_object_or_404(User, uid=receiver_uid)

        # get_queryset filters by sender and type; filter by receiver to target the specific interaction
        deleted_count, _ = self.get_queryset().filter(receiver=receiver).delete() 

        if not deleted_count:
            raise exceptions.NotFound(f"No existing {self.type} found for this user.")

        return Response(
            {'detail':  f"Un{self.type}d successfully.",},
            status=status.HTTP_200_OK
        )


class FriendshipRequestMixin(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView
):
    """
    Reusable mixin providing listing, updating, and deletion endpoints 
    for friendship requests. Subclasses must define serializers and lookup fields.
    """

    permission_classes = [permissions.IsAuthenticated, IsProfileComplete] 
    serializer_class = None # Must be overriden by the subclass
    lookup_field = None # Must be overriden by the subclass
    lookup_url_kwarg  = None # Must be overriden by the subclass


    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs) # provided by ListModelMixin


    def perform_create(self, request, *args, **kwargs):
        """Validates and creates a new friendship request."""
        serializer = self.get_serializer(data=request.data, context={'request': request})     
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': "Friendship request sent successfully.",},
            status=status.HTTP_201_CREATED
        )


    def perform_update(self, serializer):
        """Overrides default update behavior to explicitly set friendship status to 'accepted'"""
        serializer.save(status='accepted')


    def perform_delete(self, request, *args, message='Record deleted successfully', **kwargs):
        """Deletes a specific friendship request record using model deletion signals"""
        deleted_count, _ = self.get_object().delete()

        if not deleted_count:
            raise exceptions.NotFound(f"No existing friendship request found for this user.")

        return Response(
            {'detail':  message,},
            status=status.HTTP_200_OK
        )