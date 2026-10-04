from dj_rest_auth.registration.serializers import (
    RegisterSerializer, _signup_field_required,
    )
from dj_rest_auth.serializers import (
    UserDetailsSerializer, PasswordResetConfirmSerializer,
    PasswordResetSerializer, PasswordChangeSerializer,
    )
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from allauth.account.adapter import get_adapter
from allauth.account.utils import user_pk_to_url_str
from django_countries.serializer_fields import CountryField
from django_countries.serializers import CountryFieldMixin
from django.db import transaction

from .models import User
from relations.models import MatchInteraction
from .validators import validate_password
from django.conf import settings
from preferences.models import PrivacyPreference

# from matches.serializers import ImageSerializer

class CustomRegisterSerializer(RegisterSerializer):
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
        required=False,
        allow_null=True,
    )

    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    country = CountryField(
        required=False,
        allow_null=True,
    )

    def validate_password1(self, password):

        password = validate_password(password)

        return super().validate_password1(password)
        
    
    def validate_birth_date(self, value):
        from datetime import date
        if value >= date.today():
            raise serializers.ValidationError("Birth date must be in the past.")
        if value.year < 1900:
            raise serializers.ValidationError("Enter a valid birth date.")
        return value



    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            'name': self.validated_data.get('name', ''),
            'gender': self.validated_data.get('gender', None),
            'birth_date': self.validated_data.get('birth_date', None),
            'country': self.validated_data.get('country', None),

        })
        return data

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        user = adapter.save_user(request, user, self, commit=False)

        user.name = self.cleaned_data.get('name')
        user.gender = self.cleaned_data.get('gender')
        user.birth_date = self.cleaned_data.get('birth_date')
        user.country = self.cleaned_data.get('country')

        # Create profile with extra fields
        # user.profile.phone_number = self.cleaned_data.get('phone_number')
        # user.profile.company = self.cleaned_data.get('company')
        # user.profile.save()

        # self.custom_signup(request, user)

        user.save()

        PrivacyPreference.objects.create(user=user)

        return user
    


class CustomUserDetailsSerializer(UserDetailsSerializer): # Returned login response

    class Meta:
        model = User
        fields = ('uid', 'email', 'name')


class UserProfileSerializer(CountryFieldMixin, serializers.HyperlinkedModelSerializer):

    facial_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('uid', 'name', 'email', 'gender', 'birth_date', 'country', 'profile_photo', 'bio', 'facial_image')

        extra_kwargs = {
            'email': {'read_only': True}, 
            'uid': {'read_only': True}, 
            'facial_image': {'read_only': True}, 

            'name': {'required': False}, 
        }

    def get_facial_image(self, obj):
        
        request = self.context.get('request')
        image = getattr(obj, 'image', None)
        return request.build_absolute_uri(image.facial_image.url) if image and image.facial_image else None

        
class PublicUserProfileSerializer(CountryFieldMixin, serializers.ModelSerializer):

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

        # privacy Checks
        if visibility == PrivacyPreference.MatchVisibility.ME_ONLY:
            return image.get_display_url(request=request, blurred=True)

        if visibility == PrivacyPreference.MatchVisibility.FRIENDS_ONLY:
            # leverage existing annotation from annotate_friendship_status
            is_friends = getattr(obj, 'is_friends', False)
            if not is_friends:
                return image.get_display_url(request=request, blurred=True)

        # return image URL for EVERYONE or passed FRIENDS_ONLY check
        return image.get_display_url(request=request)

    def get_is_liked(self, obj):
        
        if hasattr(obj, 'is_liked'):
            return obj.is_liked
            
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return MatchInteraction.objects.filter(sender=request.user, receiver=obj, type='like').exists()

    def get_is_saved(self, obj):
        if hasattr(obj, 'is_saved'):
            return obj.is_saved
            
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return MatchInteraction.objects.filter(sender=request.user, receiver=obj, type='save').exists()

    def get_friendship_status(self, obj):
        if getattr(obj, 'is_friends', False):
            return 'friends'
        if getattr(obj, 'is_pending_sent', False):
            return 'pending_sent'
        if getattr(obj, 'is_pending_received', False):
            return 'pending_received'
        return None

    def get_similarity_score(self, obj):

        distance = getattr(obj, 'distance', None)
        if distance is not None:
            return round(1.0 - float(distance), 4)
        return None

class MinimalUserProfileSerializer(PublicUserProfileSerializer):

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
    
    def custom_validation(self, attrs):

        password = attrs.get('new_password1', '')
        password = validate_password(password)
        return get_adapter().clean_password(password)

        

class ValidationPasswordChangeSerializer(PasswordChangeSerializer):

    def custom_validation(self, attrs):

        password = attrs.get('new_password1', '')
        password = validate_password(password)
        return get_adapter().clean_password(password)
    

# SOURCE: traversing dj-rest-auth source codes with claude's help
def frontend_password_reset_url_generator(request, user, temp_key):
        uid = user_pk_to_url_str(user)
        return settings.HEADLESS_FRONTEND_URLS["account_reset_password_from_key"].format(uid=uid, token=temp_key)

class CustomPasswordResetSerializer(PasswordResetSerializer):

    def get_email_options(self):
        return {
            "url_generator": frontend_password_reset_url_generator,
        }