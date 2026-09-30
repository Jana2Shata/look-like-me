from django.urls import path
from .views import UserPrivacyPreferenceView

urlpatterns = [
    path('privacy-preferences/', UserPrivacyPreferenceView.as_view(), name='privacy-preferences'),
]