from dj_rest_auth.registration.serializers import RegisterSerializer, _signup_field_required
from dj_rest_auth.serializers import (
    UserDetailsSerializer, PasswordResetConfirmSerializer,
    PasswordResetSerializer, PasswordChangeSerializer,
    )
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from allauth.account.adapter import get_adapter
from allauth.account.utils import user_pk_to_url_str

from .models import User
from .validators import validate_password
from django.conf import settings

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

    country = serializers.CharField(
        max_length=100,
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

        user.save()

        # # Create profile with extra fields
        # user.profile.phone_number = self.cleaned_data.get('phone_number')
        # user.profile.company = self.cleaned_data.get('company')
        # user.profile.save()

        # self.custom_signup(request, user)
        return user
    


class CustomUserDetailsSerializer(UserDetailsSerializer): # Returned login response

    class Meta:
        model = User
        fields = ('uid', 'email', 'name')



class UserProfileSerializer(serializers.HyperlinkedModelSerializer):

    extra_kwargs = {
        'email': {'read_only': True}, # email is read-only, can't be updated
    }
    class Meta:
        model = User
        fields = ('uid', 'name', 'email', 'gender', 'birth_date', 'country', 'profile_photo', 'bio')

        extra_kwargs = {
            'email': {'read_only': True}, # email is read-only, can't be updated
            'name': {'required': False}, # name is required
        }
        
class PublicUserProfileSerializer(serializers.ModelSerializer):

    # Creates a clickable link pointing to the user's detail view
    url = serializers.HyperlinkedIdentityField(
        view_name='user-detail',  # Required
        lookup_field='uid' # Default is pk
    )

    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['url', 'uid', 'name', 'gender', 'birth_date', 'country', 'profile_photo', 'bio', 'image']
        read_only = fields

    def get_image(self, obj):
        request = self.context.get('request')
        # if # TODO: preferences check
        #     return None
        image = getattr(obj, 'images', None)
        return request.build_absolute_uri(image.image.url) if image and image.image else None


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