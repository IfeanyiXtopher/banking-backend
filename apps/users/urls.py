from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('login/mfa/', views.mfa_verify, name='auth-mfa-verify'),
    path('logout/', views.logout_view, name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', views.ProfileView.as_view(), name='auth-profile'),
    path('profile/update-request/', views.profile_update_request_create, name='auth-profile-update-request'),
    path('change-password/', views.change_password, name='auth-change-password'),
    path('password-reset/', views.password_reset_request, name='auth-password-reset'),
    path('password-reset/confirm/', views.password_reset_confirm, name='auth-password-reset-confirm'),
    path('kyc/upload/', views.kyc_upload, name='auth-kyc-upload'),
    path('mfa/toggle/', views.mfa_toggle, name='auth-mfa-toggle'),
]
