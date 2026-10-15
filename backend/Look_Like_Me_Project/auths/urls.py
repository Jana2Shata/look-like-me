"""
URL configuration for authentication, user profiles, and account management endpoints
Integrates django-rest-framework-knox for token auth, django-rest-auth for authentication 
workflows, and allauth for email confirmation and password management
"""

# allauth and dj_rest_auth imports
from allauth.account.views import ConfirmEmailView
from dj_rest_auth.views import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
)
# django imports
from django.urls import include, path, re_path
from django.views.generic import TemplateView
# from django.contrib.auth.views import PasswordResetConfirmView

# local imports
from .views import (
    DeleteUserView,
    GoogleLogin,
    LoginView,
    LogoutAllView,
    LogoutView,
    ManageUserView,
    PublicUserDetailView,
)



urlpatterns = [
    # -------------------------------------------------------------------------
    # Authentication (Knox Token Auth) Endpoints
    # -------------------------------------------------------------------------
    path('login/', LoginView.as_view(), name='knox_login'),
    path('logout/', LogoutView.as_view(), name='knox_logout'),
    path('logoutall/', LogoutAllView.as_view(), name='knox_logoutall'),

    # -------------------------------------------------------------------------
    # Registration & Email Verification
    # -------------------------------------------------------------------------
    # path("", include("knox.urls")),
    re_path( # == Regex path
        "^registration/account-confirm-email/(?P<key>[-:\w]+)/$", # captures the trailing key part and names it 'key'
        ConfirmEmailView.as_view(),
        name="account_confirm_email",
    ),
    path('registration/', include('dj_rest_auth.registration.urls')),

    # -------------------------------------------------------------------------
    # User Profile & Public User Details
    # -------------------------------------------------------------------------
    path('profile/', ManageUserView.as_view(), name='user_profile'),
    path('profile/delete/', DeleteUserView.as_view(), name='user_delete'),
    path('users/<uid>/', PublicUserDetailView.as_view(), name='user-detail'),

    # -------------------------------------------------------------------------
    # Password Reset & Management Endpoints
    # -------------------------------------------------------------------------
    re_path(
        r'^password-reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/$',
        TemplateView.as_view(template_name='password_reset_confirm.html'),
        name='password_reset_confirm',
    ),
    re_path(r'password/reset/?$', PasswordResetView.as_view(), name='rest_password_reset'),
    # re_path(r'password/reset/confirm/?$', PasswordResetConfirmView.as_view(), name='rest_password_reset_confirm'),
    re_path(r'password/reset/confirm/?$', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    re_path(r'password/change/?$', PasswordChangeView.as_view(), name='rest_password_change'),

    path('google/', GoogleLogin.as_view(), name='google_login'),

]
