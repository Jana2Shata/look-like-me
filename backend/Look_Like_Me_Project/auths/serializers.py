from datetime import date
from allauth.account.adapter import get_adapter
from allauth.account.utils import user_pk_to_url_str
from dj_rest_auth.registration.serializers import (
    RegisterSerializer,
    _signup_field_required,
)
from dj_rest_auth.serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    UserDetailsSerializer,
)
from django.conf import settings
from django.db import transaction
from django_countries.serializer_fields import CountryField
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from preferences.models import PrivacyPreference
from relations.models import MatchInteraction

from .models import User
from .validators import validate_password, validate_age_thirteen_plus

# from matches.serializers import ImageSerializer

class CustomRegisterSerializer(RegisterSerializer):
    """
    Custom user registration serializer that replaces the default username-based 
    signup with an email-only model and collects custom user attributes (name, 
    gender, birth date, country), automatically provisions a default PrivacyPreference 
    record upon successful user creation
    """
    "inherit FROM https://github.com/iMerica/dj-rest-auth/blob/master/dj_rest_auth/registration/serializers.py#L233"
    
    username = None  # Remove username field
    email = serializers.EmailField(
        required=_signup_field_required('email'),
        validators=[UniqueValidator(queryset=User.objects.all(),
            message="This email address is already in use.")],
    )

    name = serializers.CharField(required=True)

    gender = serializers.ChoiceField(
        choices=User.GenderChoices.choices,
        required=True,
    )

    birth_date = serializers.DateField(
        required=True,
    )

    country = CountryField(
        required=True,
    )

    def validate_password1(self, password):
        """Validates password strength against custom project rules"""
        password = validate_password(password)

        return super().validate_password1(password)
        
    
    def validate_birth_date(self, value):
        """Ensures the provided birth date is a valid historical date"""
        if value >= date.today():
            raise serializers.ValidationError("Birth date must be in the past.")
        if value.year < 1900:
            raise serializers.ValidationError("Enter a valid birth date.")
        return validate_age_thirteen_plus(value)


    def get_cleaned_data(self):
        """Extends base cleaned data with custom user profile attributes"""
        data = super().get_cleaned_data()
        data.update({
            'name': self.validated_data.get('name', ''),
            'gender': self.validated_data.get('gender', None),
            'birth_date': self.validated_data.get('birth_date', None),
            'country': self.validated_data.get('country', None),

        })
        return data

    @transaction.atomic
    def save(self, request):
        """Creates the user, assigns custom profile fields, and initializes privacy settings"""
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        user = adapter.save_user(request, user, self, commit=False)

        user.name = self.cleaned_data.get('name')
        user.gender = self.cleaned_data.get('gender')
        user.birth_date = self.cleaned_data.get('birth_date')
        user.country = self.cleaned_data.get('country')

        user.save()

        # Initialize default user privacy settings
        PrivacyPreference.objects.create(user=user)

        return user
    

class CustomUserDetailsSerializer(UserDetailsSerializer): # Returned login response
    """Returns essential authenticated user details upon login"""

    are_required_fields_filled = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('uid', 'email', 'name', 'gender', 'country', 'are_required_fields_filled', 'has_password',)

    def get_are_required_fields_filled(self, obj):
        """Returns True if gender and country are present"""
        return bool(obj.gender and obj.country and obj.birth_date)

    def get_has_password(self, obj):
        return obj.has_usable_password()

class UserProfileSerializer(CountryFieldMixin, serializers.HyperlinkedModelSerializer):
    """Serializer for managing and viewing the current user's full profile"""
    facial_image = serializers.SerializerMethodField()
    are_required_fields_filled = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('uid', 'name', 'email', 'gender', 'birth_date', 'country', 'profile_photo', 'bio', 'facial_image', 'are_required_fields_filled','has_password',)
        extra_kwargs = {
            'email': {'read_only': True}, 
            'uid': {'read_only': True}, 
            'facial_image': {'read_only': True}, 
            'are_required_fields_filled': {'read_only': True},
            'name': {'required': False}, 
            'gender': {'required': True},
            'country': {'required': True},
        }


    def validate_birth_date(self, value):
        if value >= date.today():
            raise serializers.ValidationError("Birth date must be in the past.")
        if value.year < 1900:
            raise serializers.ValidationError("Enter a valid birth date.")
        
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 13:
            user = self.instance

            # Delete only if the user had no birth date before this request
            if user and user.pk and user.birth_date is None:
                user.delete()

            raise serializers.ValidationError({
                "code": "underage",
                "detail": "You must be at least 13 years old to use this website."
            })
        return value

    def get_are_required_fields_filled(self, obj):
        """Returns True if gender and country are present"""
        return bool(obj.gender and obj.country and obj.birth_date)

    def get_has_password(self, obj):
        return obj.has_usable_password()
    
    def get_facial_image(self, obj):
        """Builds an absolute URI for the user's facial image if available."""
        request = self.context.get('request')
        image = getattr(obj, 'image', None)
        return request.build_absolute_uri(image.facial_image.url) if image and image.facial_image else None

        
class PublicUserProfileSerializer(CountryFieldMixin, serializers.ModelSerializer):
    """
    Serializer for viewing other users' public profiles
    Applies privacy visibility rules, returns interaction states (likes/saves/friendship), 
    and converts distance vector scores into similarity percentages
    """

    # Creates a clickable link pointing to the user's detail view
    url = serializers.HyperlinkedIdentityField(
        view_name='user-detail',  # Required
        lookup_field='uid' # Default is pk
    )

    facial_image = serializers.SerializerMethodField()

    is_liked = serializers.SerializerMethodField()

    is_saved = serializers.SerializerMethodField()

    friendship_status = serializers.SerializerMethodField()

    similarity_score = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['url', 'uid', 'name', 'gender', 'birth_date', 'country', 'profile_photo', 'bio', 'facial_image', 'is_liked', 'is_saved', 'friendship_status', 'similarity_score']
        read_only_fields = fields

    def get_facial_image(self, obj):
        """
        Determines whether to show clear, blurred, or no facial image 
        based on viewer authentication and target user privacy preferences
        """
        request = self.context.get('request')
        image = getattr(obj, 'image', None)

        if not image or not image.facial_image:
            return None

        if not request or not request.user.is_authenticated:
            return None

        viewer = request.user

        if viewer.id == obj.id:
            return image.get_display_url(request=request)

        preference = getattr(obj, 'privacy_preferences', None)
        visibility = (
            preference.match_visibility 
            if preference 
            else PrivacyPreference.MatchVisibility.EVERYONE
        )

        # Apply visibility and privacy checks
        if visibility == PrivacyPreference.MatchVisibility.ME_ONLY:
            return image.get_display_url(request=request, blurred=True)

        if visibility == PrivacyPreference.MatchVisibility.FRIENDS_ONLY:
            is_friends = getattr(obj, 'is_friends', False)
            if not is_friends:
                return image.get_display_url(request=request, blurred=True)

        return image.get_display_url(request=request)
    

    def get_is_liked(self, obj):
        """Checks if the requesting user has liked this profile"""
        if hasattr(obj, 'is_liked'):
            return obj.is_liked
            
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        return MatchInteraction.objects.filter(sender=request.user, receiver=obj, type='like').exists()

    def get_is_saved(self, obj):
        """Checks if the requesting user has saved this profile."""
        if hasattr(obj, 'is_saved'):
            return obj.is_saved
            
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        return MatchInteraction.objects.filter(sender=request.user, receiver=obj, type='save').exists()

    def get_friendship_status(self, obj):
        """Evaluates friendship state between viewer and target user"""
        if getattr(obj, 'is_friends', False):
            return 'friends'
        if getattr(obj, 'is_pending_sent', False):
            return 'pending_sent'
        if getattr(obj, 'is_pending_received', False):
            return 'pending_received'
        return None

    def get_similarity_score(self, obj):
        """Converts annotated vector distance into a normalized similarity score"""
        distance = getattr(obj, 'distance', None)
        if distance is not None:
            return round(1.0 - float(distance), 4)
        return None

class MinimalUserProfileSerializer(PublicUserProfileSerializer):
    """Lightweight variant of PublicUserProfileSerializer supporting compact payloads"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('compact', False):
            excluded_fields = {'is_liked', 'is_saved', 'friendship_status'}
            for field_name in excluded_fields:
                self.fields.pop(field_name, None)

    class Meta:
        model = User
        fields = ['uid', 'name', 'gender', 'birth_date', 'country', 'profile_photo', 'facial_image', 'is_liked', 'is_saved', 'friendship_status', 'similarity_score']
        read_only_fields = fields

    @classmethod
    def get_unavailable_payload(cls, compact=False):
        """Provides a safe default placeholder payload for deleted or blocked users"""
        payload = {
            "uid": None,
            "name": "Unavailable User",
            "gender": None,
            "birth_date": None,
            "country": None,
            "profile_photo": None,
            "facial_image": None,
            "similarity_score": None,
        }

        if not compact:
            payload.update({
                "is_liked": False,
                "is_saved": False,
                "friendship_status": None,
            })

        return payload

class ValidationPasswordResetConfirmSerializer(PasswordResetConfirmSerializer):
    """Enforces strict custom password rules during password reset confirmation"""

    def custom_validation(self, attrs):

        password = attrs.get('new_password1', '')
        password = validate_password(password)
        return get_adapter().clean_password(password)

class ValidationPasswordChangeSerializer(PasswordChangeSerializer):
    """Enforces strict custom password rules during active user password changes"""

    def custom_validation(self, attrs):

        password = attrs.get('new_password1', '')
        password = validate_password(password)
        return get_adapter().clean_password(password)
    

# SOURCE: traversing dj-rest-auth source codes with claude's help
def frontend_password_reset_url_generator(request, user, temp_key):
    """Generates a frontend-targeted URL containing the user UID and reset token"""
    uid = user_pk_to_url_str(user)
    return settings.HEADLESS_FRONTEND_URLS["account_reset_password_from_key"].format(uid=uid, token=temp_key)

class CustomPasswordResetSerializer(PasswordResetSerializer):
    """Overrides password reset email options to point directly to the frontend application"""

    def get_email_options(self):
        return {
            "url_generator": frontend_password_reset_url_generator,
        }