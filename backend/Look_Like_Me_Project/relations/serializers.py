from rest_framework.serializers import (
    ModelSerializer, SlugRelatedField,
    HiddenField, CurrentUserDefault,
    CharField, Serializer,
    ValidationError, SerializerMethodField
)
from rest_framework.validators import UniqueTogetherValidator
from django.core.exceptions import ValidationError as DjangoValidationError, NON_FIELD_ERRORS
from rest_framework.settings import api_settings

from .models import Friendship, MatchInteraction, BlockedUser
from auths.models import User
from auths.serializers import MinimalUserProfileSerializer
from globals.utils import NonBlockedUserSlugField    

"""
    Saves/likes are created/deleted only, not updated.
    The frontend already works with uid (through the user detail endpoint)
"""
class MatchInteractionSerializer(ModelSerializer):

    # Automatically pulls request.user from context and hides the field from input validation
    sender = HiddenField(default=CurrentUserDefault())

    receiver = NonBlockedUserSlugField(
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

    
    # replace string uid with full nested receiver profile data
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receiver'] = MinimalUserProfileSerializer(
            instance.receiver,
            context=self.context
        ).data
        return rep


class SendFriendshipSerializer(ModelSerializer):

    # Automatically pulls request.user from context and hides the field from input validation
    sender = HiddenField(default=CurrentUserDefault())

    
    receiver = NonBlockedUserSlugField(
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

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receiver'] = MinimalUserProfileSerializer(
            instance.receiver,
            context=self.context
        ).data
        return rep


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

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['sender'] = MinimalUserProfileSerializer(
            instance.sender,
            context=self.context
        ).data
        return rep

class AcceptedFriendshipSerializer(ModelSerializer):
    """
    Used only for listing accepted friendship records (GET).
    No client-writable fields
    """

    user = SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ['user', 'status', 'created_at']
        read_only_fields = fields  # nothing is writable from the client's payload

    def get_user(self, obj):
        request = self.context.get('request')
        target_user = obj.receiver if obj.sender == request.user else obj.sender
        return MinimalUserProfileSerializer(target_user, context=self.context).data


class BlockedUserSerializer(ModelSerializer):

    sender = HiddenField(default=CurrentUserDefault())

    # validates and looks up target receiver by 'uid' during POST
    receiver = NonBlockedUserSlugField(
        queryset=User.objects.all(),
        slug_field='uid'
    )

    class Meta:
        model = BlockedUser
        fields = ['sender', 'receiver', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, attrs):
        sender = attrs['sender']
        receiver = attrs['receiver']

        # prevent self-blocking
        if sender == receiver:
            raise ValidationError("You cannot block yourself")

        # prevent duplicate blocks
        if BlockedUser.objects.filter(sender=sender, receiver=receiver).exists():
            raise ValidationError("This user is already blocked")

        return attrs
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receiver'] = MinimalUserProfileSerializer(
            instance.receiver,
            context=self.context
        ).data
        return rep
