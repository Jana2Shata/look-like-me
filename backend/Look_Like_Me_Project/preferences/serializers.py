from rest_framework import serializers
from .models import PrivacyPreference

class ProfileVisibilityBooleanField(serializers.Field):

    def to_representation(self, value):

        return value == PrivacyPreference.ProfileVisibility.PUBLIC

    def to_internal_value(self, data):
        if not isinstance(data, bool):
            raise serializers.ValidationError(
                "Expected a boolean value."
            )

        return (
            PrivacyPreference.ProfileVisibility.PUBLIC
            if data
            else PrivacyPreference.ProfileVisibility.HIDDEN
        )


class PrivacyPreferenceSerializer(serializers.ModelSerializer):
    profile_visibility = ProfileVisibilityBooleanField()

    class Meta:
        model = PrivacyPreference
        fields = ['profile_visibility', 'match_visibility', 'updated_at']
        read_only_fields = ['updated_at']