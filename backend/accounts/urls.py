from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/signup/", views.SignUpView.as_view()),
    path("auth/verify/", views.VerifyEmailView.as_view()),
    path("auth/resend/", views.ResendCodeView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/login/code/", views.LoginCodeRequestView.as_view()),
    path("auth/login/code/verify/", views.LoginCodeVerifyView.as_view()),
    path("auth/password/forgot/", views.ForgotPasswordView.as_view()),
    path("auth/password/reset/", views.ResetPasswordView.as_view()),
    path("auth/password/change/", views.ChangePasswordView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
]
