# django imports
from django.contrib.auth import login, logout
from django.middleware import csrf
from django.db.models import Q, OuterRef, Exists, Prefetch

# rest_framework imports
from rest_framework import generics, permissions
from rest_framework.settings import api_settings
from rest_framework.response import Response
from rest_framework import status

# dj-rest-auth imports
from dj_rest_auth.serializers import LoginSerializer

# knox imports
from knox.views import LoginView, LogoutView, LogoutAllView
from knox.auth import TokenAuthentication

# local apps import
from .models import User
from .serializers import ( 
    UserProfileSerializer,
    PublicUserProfileSerializer,
    CustomUserDetailsSerializer,
    )
from relations.models import Friendship, MatchInteraction
from matches.querysets import annotate_similarity_score
from relations.querysets import annotate_friendship_status, annotate_user_interactions
from globals.utils import exclude_blocked_users
from chats.services import ChatService     

        




class LoginView(LoginView):
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

    # def get_post_response_data(self, request, token, instance):
        
    #     data = super().get_post_response_data(request, token, instance)
    #     data['user'] = CustomUserDetailsSerializer(request.user, context={'request': request}).data
    #     return data



class LogoutView(LogoutView):
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
        
        logout(request)                                  # django deletes the session cookie

        if user and user.is_authenticated:
            ChatService.revoke_all_user_sockets(user)

        if not response:
            response = self.get_post_response(request)

        return response


class LogoutAllView(LogoutAllView):
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
        
        logout(request)                                  # django deletes the session cookie

        if user and user.is_authenticated:
            ChatService.revoke_all_user_sockets(user)

        if not response:
            response = self.get_post_response(request)

        return response
    

    # TODO define model serializer
class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""

    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = User.objects.all()

    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user


class DeleteUserView(generics.DestroyAPIView):
    """Delete the authenticated user"""

    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = User.objects.all()

    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user

    def delete(self, request, *args, **kwargs):
        self.destroy(request, *args, **kwargs)
        return Response({"detail": "User account deleted successfully."}, status=status.HTTP_200_OK)


class PublicUserDetailView(generics.RetrieveAPIView):
    
    serializer_class = PublicUserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uid'

    def get_queryset(self):
        user = self.request.user

        qs = exclude_blocked_users(User.objects.all(), user)
        
        qs = annotate_friendship_status(qs, user)
        qs = annotate_similarity_score(qs, user)
        qs = annotate_user_interactions(qs, user)

        return qs.select_related('image')

