from rest_framework import generics, permissions
from .models import PrivacyPreference
from .serializers import PrivacyPreferenceSerializer

class UserPrivacyPreferenceView(generics.RetrieveUpdateAPIView):
    """
    API view allowing authenticated users to retrieve and update 
    their profile visibility and match visibility preferences
    """
    serializer_class = PrivacyPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Retrieves the privacy preferences for the authenticated user, 
        lazily creating a default instance if one does not already exist
        """
        obj, _ = PrivacyPreference.objects.get_or_create(user=self.request.user)
        return obj
