from django.shortcuts import render
from rest_framework import mixins, viewsets, generics
from rest_framework import status, permissions, exceptions
from django.db import IntegrityError
from rest_framework.response import Response

from .models import MatchInteraction, Friendship,  BlockedUser
from .serializers import MatchInteractionSerializer, ReceiverActionSerializer


class MatchInteractionMixin(
    mixins.ListModelMixin,
    generics.GenericAPIView):
    """
    A viewset for creating, deleting, and listing MatchInteraction instances of specifictype.
    """

    permission_classes = [permissions.IsAuthenticated] 
    serializer_class = MatchInteractionSerializer
    type = None  # This should be set in the subclass to either 'like' or 'save'    

    def get_queryset(self):
        # Filter interactions where the current user is the sender and type is like
        return MatchInteraction.objects.filter(sender=self.request.user, type=self.type)


    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs) # provided by ListModelMixin



    def post(self, request, *args, **kwargs):
        data = {'receiver': request.data.get('receiver'),
                'type': self.type}
        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': f"{self.type.capitalize()}d successfully.",
                        #  'data': serializer.data
                         }, status=status.HTTP_201_CREATED)


    def delete(self, request, *args, **kwargs):
        receiver_serializer = ReceiverActionSerializer(data=request.data)
        receiver_serializer.is_valid(raise_exception=True)
        receiver = receiver_serializer.validated_data['receiver']

        deleted_count, objects_count = self.get_queryset().filter(receiver=receiver).delete() 
                            # get_queryset already filters by type and sender, so we just need to filter by receiver here
                            # queryset.delete calls pre and post deletion signals, but skips any overrirden model.delete(). it's fine here
        if not deleted_count:
            raise exceptions.NotFound(f"No existing {self.type} found for this user.")

        return Response({
            'detail':  f"Un{self.type}d successfully.",
        },
            status=status.HTTP_200_OK)
