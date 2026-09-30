
from rest_framework import generics, permissions
from .models import PrivacyPreference
from .serializers import PrivacyPreferenceSerializer

class UserPrivacyPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = PrivacyPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _ = PrivacyPreference.objects.get_or_create(user=self.request.user)
        return obj
