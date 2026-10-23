# django imports
from django.contrib.auth import login, logout
from django.middleware import csrf
from django.conf import settings


# dj-rest-auth imports
from dj_rest_auth.serializers import LoginSerializer
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# knox imports
from knox.views import LoginView, LogoutView, LogoutAllView

# rest_framework imports
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.settings import api_settings


# local apps import
from auths.permissions import IsProfileComplete
from chats.services import ChatService
from globals.utils import exclude_blocked_users
from matches.querysets import annotate_similarity_score
from preferences.services import filter_privacy_visible_users
from relations.querysets import (
    annotate_friendship_status,
    annotate_user_interactions,
)
from .models import User
from .serializers import (
    CustomUserDetailsSerializer,
    PublicUserProfileSerializer,
    UserProfileSerializer,
)

class LoginView(LoginView):
    """
    Handles user login using Django REST Framework Knox and Django sessions
    Validates credentials, establishes a session, refreshes CSRF tokens, 
    and returns session expiry alongside user details
    """
    # login view extending KnoxLoginView
    
    # authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.AllowAny,]

    # rate limiting by DRF & dj-rest-auth
    throttle_scope = 'login'

    def post(self, request, format=None):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        login(request, user) # creates the session, sets sessionid cookie
        csrf.get_token(request) # refreshes the csrftoken cookie

        # return super(LoginView, self).post(request, format=format) # create the knox token and return the response with the token in the body
        return Response({
            'expiry': request.session.get_expiry_date(),
            'user': CustomUserDetailsSerializer(user).data,
        })
    

class LogoutView(LogoutView):
    """
    Handles single-token user logout, deletes the Knox token, terminates 
    the Django session, and revokes all active WebSocket connections for the user
    """
    # logout view extending KnoxLogoutView
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES

    def get_post_response(self, request):
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)      
    

    def post(self, request, format=None):
        # Override the post method to handle comprehensive logout
        user = request.user
        response = None

        if request._auth is not None:
            response = super().post(request, format=None)  # Knox deletes the json token
        
        logout(request) # django deletes the session cookie

        if user and user.is_authenticated:
            ChatService.revoke_all_user_sockets(user)

        if not response:
            response = self.get_post_response(request)

        return response


class LogoutAllView(LogoutAllView):
    """
    Handles global logout across all user tokens, clears all Knox tokens, 
    terminates the Django session, and revokes all active WebSocket connections
    """
    # logout view extending KnoxLogoutView
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES

    def get_post_response(self, request):

        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK) 

    def post(self, request, format=None):
        # Override the post method to handle comprehensive logout
        user = request.user
        response = None

        if request._auth is not None:
            response = super().post(request, format=None)  # Knox deletes the json token
        
        logout(request) # django deletes the session cookie

        if user and user.is_authenticated:
            ChatService.revoke_all_user_sockets(user)

        if not response:
            response = self.get_post_response(request)

        return response


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Provides retrieval and update endpoints for the authenticated user's profile"""

    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = User.objects.all()

    def get_object(self):
        """Retrieve and return the currently authenticated user"""
        return self.request.user


class DeleteUserView(generics.DestroyAPIView):
    """Provides an endpoint for the authenticated user to permanently delete their account"""

    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = User.objects.all()

    def get_object(self):
        """Retrieve and return the currently authenticated user"""
        return self.request.user

    def delete(self, request, *args, **kwargs):
        self.destroy(request, *args, **kwargs)
        return Response({"detail": "User account deleted successfully."}, status=status.HTTP_200_OK)


class PublicUserDetailView(generics.RetrieveAPIView):
    """
    Retrieves another user's public profile by uid
    Filters out blocked and privacy-restricted users while annotating friendship status, 
    similarity scores, and user interaction states
    """

    serializer_class = PublicUserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileComplete]
    lookup_field = 'uid'

    def get_queryset(self):
        user = self.request.user

        qs = exclude_blocked_users(User.objects.all(), user)
        qs = filter_privacy_visible_users(qs, user)
        
        qs = annotate_friendship_status(qs, user)
        qs = annotate_similarity_score(qs, user)
        qs = annotate_user_interactions(qs, user)

        return qs.select_related('image', 'privacy_preferences')

class GoogleLogin(SocialLoginView):
    """
    API view endpoint for authenticating users via Google OAuth2
    Integrates Google's OAuth2 adapter, client, and frontend callback routing 
    to process social login credentials from client applications

    SOURCES:
        - https://dev.to/kihuni/how-to-add-google-oauth-to-django-rest-api-29h9
        - https://dj-rest-auth.readthedocs.io/en/latest/guides/social-auth/?h=goog#2-configure-django-settings
    """
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.HEADLESS_FRONTEND_URLS.get("google_oauth_callback")
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.user = serializer.validated_data['user']


        login(request, self.user) # creates the session, sets sessionid cookie
        csrf.get_token(request) # refreshes the csrftoken cookie

        return Response({
            'expiry': request.session.get_expiry_date(),
            'user': CustomUserDetailsSerializer(self.user, context={'request': request}).data,
        })

