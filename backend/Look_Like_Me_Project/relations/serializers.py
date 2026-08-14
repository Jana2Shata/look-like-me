from rest_framework.serializers import (
    ModelSerializer, SlugRelatedField,
    HiddenField, CurrentUserDefault,
    CharField, Serializer
)
from rest_framework.validators import UniqueTogetherValidator

from .models import Friendship, MatchInteraction, BlockedUser
from auths.models import User

"""
    Saves/likes are created/deleted only, not updated.
    The frontend already works with uid (through the user detail endpoint)
"""
class MatchInteractionSerializer(ModelSerializer):

    # Automatically pulls request.user from context and hides the field from input validation
    sender = HiddenField(default=CurrentUserDefault())

    
    receiver = SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='uid',
        )
    

    class Meta:
        model = MatchInteraction
        fields = ['sender', 'receiver', 'type', 'created_at']
        read_only_fields = ['created_at'] # 'type' is safely coded, not taken from user input

        validators = [
            UniqueTogetherValidator(
                queryset=MatchInteraction.objects.all(),
                fields=['sender', 'receiver', 'type'],
                message= f"This action has already been performed"
            )
        ]

class ReceiverActionSerializer(Serializer):
    """
    Validates just the `receiver` field. Used for DELETE method, 
    where 'sender' and 'type' are already known from context.
    """
    receiver = SlugRelatedField(queryset=User.objects.all(), slug_field='uid')