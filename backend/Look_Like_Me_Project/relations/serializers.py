from auths.models import User
from auths.serializers import MinimalUserProfileSerializer
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from globals.utils import NonBlockedUserSlugField
from preferences.services import filter_privacy_visible_users
from rest_framework import serializers
from rest_framework.serializers import (
    CharField,
    CurrentUserDefault,
    HiddenField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
    SlugRelatedField,
    ValidationError,
)
from rest_framework.settings import api_settings
from rest_framework.validators import UniqueTogetherValidator

from .models import BlockedUser, Friendship, MatchInteraction

class MatchInteractionSerializer(ModelSerializer):
    """
    Serializer for creating and listing match interactions (likes and saves)
    Validates receiver accessibility, prevents self-interactions, and embeds nested profile data
    """

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

    def validate_receiver(self, receiver):
        """Validates that the receiver is not the sender, is not blocked, and has a visible profile"""
        user = self.context['request'].user

        if receiver.id == user.id:
            interaction_type = self.initial_data.get('type')

            if interaction_type == MatchInteraction.TypeChoices.LIKE:
                raise ValidationError("You cannot like your own profile.")

            if interaction_type == MatchInteraction.TypeChoices.SAVE:
                raise ValidationError("You cannot save your own profile.")

            raise ValidationError("You cannot interact with your own profile.")

        visible_users = filter_privacy_visible_users(
            User.objects.all(),
            user
        )

        if not visible_users.filter(id=receiver.id).exists():
            raise ValidationError(
                "This user profile is private or unavailable."
            )

        return receiver
    
    def to_representation(self, instance):
        """Replaces the receiver UID string with full nested user profile data"""
        rep = super().to_representation(instance)
        rep['receiver'] = MinimalUserProfileSerializer(
            instance.receiver,
            context=self.context
        ).data
        return rep

class SendFriendshipSerializer(ModelSerializer):
    """
    Serializer for sending new friendship requests
    Enforces model-level constraints by invoking full_clean() during validation 
    to handle bidirectional uniqueness and self-friendship checks
    """

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
        """
        Re-enforces model-level constraints (asymmetric uniqueness and self-friendship checks) 
        by instantiating the model and running full_clean(), mapping Django errors to DRF format
        """
        # SOURCE: https://docs.djangoproject.com/en/6.1/ref/models/instances/#validating-objects

        instance = Friendship(
            sender=attrs['sender'],
            receiver=attrs['receiver'],
        )
        try:
            instance.full_clean(exclude=['uid', 'created_at'])

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
        """Saves and returns the stashed friendship instance"""
        self._instance.save() # Otherwise default create() re-calls Friendship(**validated_data), which creates a redundant second model instance
        return self._instance

    def to_representation(self, instance):
        """Replaces the receiver UID with a nested user profile representation"""
        rep = super().to_representation(instance)
        rep['receiver'] = MinimalUserProfileSerializer(
            instance.receiver,
            context=self.context
        ).data
        return rep

class ReceiveFriendshipSerializer(ModelSerializer):
    """
    Used only for accepting a friendship request (PUT)
    No client-writable fields — status is set programmatically via perform_update,
    sender/receiver are already fixed on the existing instance and identified via the URL
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
        """Replaces the sender UID with a nested user profile representation"""
        rep = super().to_representation(instance)
        rep['sender'] = MinimalUserProfileSerializer(
            instance.sender,
            context=self.context
        ).data
        return rep

class AcceptedFriendshipSerializer(ModelSerializer):
    """
    Used only for listing accepted friendship records (GET)
    No client-writable fields
    """

    user = SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ['user', 'status', 'created_at']
        read_only_fields = fields  # nothing is writable from the client's payload

    def get_user(self, obj):
        """Determines whether the counterparty is the sender or receiver and returns their profile"""
        request = self.context.get('request')
        target_user = obj.receiver if obj.sender == request.user else obj.sender
        return MinimalUserProfileSerializer(target_user, context=self.context).data

class BlockedUserSerializer(ModelSerializer):
    """
    Serializer for blocking users that validates against self-blocking and duplicate block records, 
    and returns nested receiver profile data
    """

    sender = HiddenField(default=CurrentUserDefault())

    receiver = NonBlockedUserSlugField(
        queryset=User.objects.all(),
        slug_field='uid'
    )

    class Meta:
        model = BlockedUser
        fields = ['sender', 'receiver', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, attrs):
        """Validates that users cannot block themselves or create duplicate block records"""
        sender = attrs['sender']
        receiver = attrs['receiver']

        if sender == receiver:
            raise ValidationError("You cannot block yourself")

        if BlockedUser.objects.filter(sender=sender, receiver=receiver).exists():
            raise ValidationError("This user is already blocked")

        return attrs
    
    def to_representation(self, instance):
        """Replaces the receiver UID with a nested user profile representation"""
        rep = super().to_representation(instance)
        rep['receiver'] = MinimalUserProfileSerializer(
            instance.receiver,
            context=self.context
        ).data
        return rep
