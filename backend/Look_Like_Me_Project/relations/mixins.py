from django.shortcuts import render
from rest_framework import mixins, viewsets, generics
from rest_framework import status, permissions, exceptions
from django.db import IntegrityError
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import MatchInteraction, Friendship,  BlockedUser
from .serializers import (
    MatchInteractionSerializer,
    )
from auths.models import User


class MatchInteractionMixin(
    mixins.ListModelMixin,
    generics.GenericAPIView):
    """
    A mixin for creating, deleting, and listing MatchInteraction instances of specifictype.
    """

    permission_classes = [permissions.IsAuthenticated] 
    serializer_class = MatchInteractionSerializer
    type = None  # This should be set in the subclass to either 'like' or 'save'    

    def get_queryset(self):
        # Filter interactions where the current user is the sender and type is what the subclass specified
        return MatchInteraction.objects.filter(sender=self.request.user, type=self.type)


    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs) # provided by ListModelMixin



    def post(self, request, *args, **kwargs):
        data = {'receiver': request.data.get('receiver'),
                'type': self.type}
        serializer = self.get_serializer(data=data, context={'request': request})
            # data only accept a single source, either the request.data or code-defined, so we merged them
            # into a single new dict before passing.
            # we still pass the request in context so that the serializer can access request.user for the sender field

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': f"{self.type.capitalize()}d successfully.",
                        #  'data': serializer.data
                         }, status=status.HTTP_201_CREATED)


    def delete(self, request, *args, **kwargs):
        receiver_uid = kwargs.get('receiver')
        receiver = get_object_or_404(User, uid=receiver_uid)

        deleted_count, detailed_objects_count = self.get_queryset().filter(receiver=receiver).delete() 
                        # get_queryset already filters by type and sender, so we just need to filter by receiver here
                        # queryset.delete calls pre and post deletion signals, but skips any overrirden model.delete(). it's fine here
        if not deleted_count:
            raise exceptions.NotFound(f"No existing {self.type} found for this user.")

        return Response({
            'detail':  f"Un{self.type}d successfully.",
        },
            status=status.HTTP_200_OK)




class FriendshipRequestMixin(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView):
    """
    A mixin for creating, updating, deleting, and listing Friendship requests.
    """

    permission_classes = [permissions.IsAuthenticated] 
    serializer_class = None # Must be overriden by the subclass
    lookup_field = None # Must be overriden by the subclass
    lookup_url_kwarg  = None # Must be overriden by the subclass


    # def get_queryset(self):
        # Must be overriden by the subclass


    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs) # provided by ListModelMixin



    def perform_create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data, context={'request': request})     

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': "Friendship request sent successfully.",
                        #  'data': serializer.data
                            }, status=status.HTTP_201_CREATED)


    def perform_update(self, serializer): # Overriding the default behavior to enable code-sourced change of the 'status' field
        serializer.save(status='accepted')


    def perform_delete(self, request, *args, message='Record deleted successfully', **kwargs):

        deleted_count, detailed_objects_count = self.get_object().delete()
                    # get_object already filters by get_queryset AND lookup_field from the path argument
                    # note that this is model.delete() not queryset.delete 
        if not deleted_count:
            raise exceptions.NotFound(f"No existing friendship request found for this user.")

        return Response({
            'detail':  message,
        },
            status=status.HTTP_200_OK)