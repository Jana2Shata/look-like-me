from rest_framework import serializers
from .models import PrivacyPreference

class ProfileVisibilityBooleanField(serializers.Field):
    """
    Custom serializer field that bridges database-level text choices 
    ('PUBLIC' / 'HIDDEN') and API-level boolean values ('True' / 'False')
    """
    def to_representation(self, value):
        """Converts the stored profile visibility text choice into a boolean value"""
        return value == PrivacyPreference.ProfileVisibility.PUBLIC

    def to_internal_value(self, data):
        """Validates incoming boolean data and maps it back to profile visibility choices"""
        if not isinstance(data, bool):
            raise serializers.ValidationError("Expected a boolean value.")

        return (
            PrivacyPreference.ProfileVisibility.PUBLIC
            if data
            else PrivacyPreference.ProfileVisibility.HIDDEN
        )


class PrivacyPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for managing user privacy and visibility preferences
    Utilizes 'ProfileVisibilityBooleanField' to expose user-friendly boolean toggles 
    for profile visibility alongside match visibility choices
    """

    profile_visibility = ProfileVisibilityBooleanField()

    class Meta:
        model = PrivacyPreference
        fields = ['profile_visibility', 'match_visibility', 'updated_at']
        read_only_fields = ['updated_at']