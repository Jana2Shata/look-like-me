from rest_framework.serializers import (
    ModelSerializer, SlugRelatedField,
    HiddenField, CurrentUserDefault,
    CharField, Serializer,
    ValidationError,
)
from rest_framework.validators import UniqueTogetherValidator
from django.core.exceptions import ValidationError as DjangoValidationError, NON_FIELD_ERRORS
from rest_framework.settings import api_settings

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


class SendFriendshipSerializer(ModelSerializer):

    # Automatically pulls request.user from context and hides the field from input validation
    sender = HiddenField(default=CurrentUserDefault())

    
    receiver = SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='uid',
        )
    
    class Meta:
        model = Friendship
        fields = ['sender', 'receiver', 'status', 'created_at']
        read_only_fields = ['created_at', 'status']
        


    def validate(self, attrs):
        # Since we re-defined the fields, the default serializer behavior ignores the model's constraints.
        # so here we re-enforce validation by calling model.full_clean()
        # SOURCE: https://docs.djangoproject.com/en/6.1/ref/models/instances/#validating-objects

        instance = Friendship(
            sender=attrs['sender'],
            receiver=attrs['receiver'],
            # status=attrs.get('status')
            # status is defaulted to 'pending' at the model
            # CONSIDER: will this work for accepting/declining?
        )
        try:
            instance.full_clean(exclude=['uid', 'created_at'])
            # auto-populated fields, so unnecessary to validate their values

        except DjangoValidationError as e:
                        
            error_dict = e.message_dict

            if NON_FIELD_ERRORS in error_dict:
                error_dict[api_settings.NON_FIELD_ERRORS_KEY] = error_dict.pop(NON_FIELD_ERRORS)
                # changes django's '__all__' dict key to 'detail'

            raise ValidationError(error_dict)


        # stash it so create() doesn't have to rebuild/re-query
        self._instance = instance
        return attrs

    def create(self, validated_data):
        self._instance.save() # Otherwise default create() re-calls Friendship(**validated_data), which creates a redundant second model instance
        return self._instance


class ReceiveFriendshipSerializer(ModelSerializer):
    """
    Used only for accepting a friendship request (PUT).
    No client-writable fields — status is set programmatically via perform_update,
    sender/receiver are already fixed on the existing instance and identified via the URL.
    """
    sender = SlugRelatedField(
            slug_field='uid',
            read_only=True
            )
    class Meta:
        model = Friendship
        fields = ['sender', 'status', 'created_at']
        read_only_fields = fields  # nothing is writable from the client's payload
