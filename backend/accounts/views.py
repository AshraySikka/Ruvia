import logging

from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .emails import send_otp
from .models import EmailOTP, User

log = logging.getLogger(__name__)


class OTPThrottle(AnonRateThrottle):
    rate = "20/hour"


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "display_name", "email_verified", "sex", "birth_year", "timezone",
            "water_goal_ml", "track_cycle", "onboarded", "city", "latitude", "longitude", "theme", "avatar_hue",
            "checkins_per_day", "first_checkin_time", "checkin_interval_hours", "water_reminders",
            "water_interval_hours", "quiet_start", "quiet_end", "followups_enabled", "cycle_notifications",
            "weekly_summary", "date_joined",
        ]
        read_only_fields = ["id", "email", "email_verified", "date_joined"]

    def validate_checkins_per_day(self, v):
        if not 0 <= v <= 6:
            raise serializers.ValidationError("Pick between 0 and 6 check-ins a day.")
        return v

    def validate_checkin_interval_hours(self, v):
        if not 1 <= v <= 12:
            raise serializers.ValidationError("Pick an interval between 1 and 12 hours.")
        return v

    def validate_water_goal_ml(self, v):
        if not 500 <= v <= 6000:
            raise serializers.ValidationError("Pick a goal between 500 and 6000 ml.")
        return v


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": UserSerializer(user).data}


def clean_email(value):
    return (value or "").strip().lower()


def issue_and_send(email, purpose):
    if EmailOTP.recent_count(email, minutes=60) >= 6:
        return False, "Too many codes requested. Try again in an hour."
    last = EmailOTP.objects.filter(email=email).first()
    if last and (timezone.now() - last.created_at).total_seconds() < 30:
        return False, "Please wait a few seconds before asking for another code."
    code = EmailOTP.issue(email, purpose)
    sent = send_otp(email, code, purpose)
    if not sent and settings.DEBUG:
        log.warning("DEV OTP for %s (%s): %s", email, purpose, code)
    return True, ""


def after_verified(user):
    from care.services import claim_invites
    claim_invites(user)


class SignUpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        password = request.data.get("password") or ""
        first_name = (request.data.get("first_name") or "").strip()[:60]
        if not email or "@" not in email:
            return Response({"detail": "Enter a valid email."}, status=400)
        existing = User.objects.filter(email=email).first()
        if existing and existing.email_verified:
            return Response({"detail": "An account with this email already exists. Try signing in."}, status=400)
        user = existing or User(email=email)
        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)
        user.first_name = first_name or user.first_name
        user.set_password(password)
        user.save()
        ok, msg = issue_and_send(email, "signup")
        if not ok:
            return Response({"detail": msg}, status=429)
        return Response({"detail": "We sent a 6 digit code to your email.", "email": email}, status=201)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        ok, msg = EmailOTP.verify(email, "signup", request.data.get("code"))
        if not ok:
            return Response({"detail": msg}, status=400)
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"detail": "Account not found."}, status=404)
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        after_verified(user)
        return Response(tokens_for(user))


class ResendCodeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        purpose = request.data.get("purpose", "signup")
        if purpose not in ("signup", "login", "reset"):
            return Response({"detail": "Unknown purpose."}, status=400)
        if User.objects.filter(email=email).exists():
            ok, msg = issue_and_send(email, purpose)
            if not ok:
                return Response({"detail": msg}, status=429)
        return Response({"detail": "If that email has an account, a new code is on its way."})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        user = authenticate(request, email=email, password=request.data.get("password") or "")
        if not user:
            return Response({"detail": "Email or password is not right."}, status=400)
        if not user.email_verified:
            issue_and_send(email, "signup")
            return Response({"detail": "Confirm your email first. We sent you a code.", "needs_verification": True,
                             "email": email}, status=403)
        return Response(tokens_for(user))


class LoginCodeRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        if User.objects.filter(email=email, is_active=True).exists():
            ok, msg = issue_and_send(email, "login")
            if not ok:
                return Response({"detail": msg}, status=429)
        return Response({"detail": "If that email has an account, a sign in code is on its way."})


class LoginCodeVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        ok, msg = EmailOTP.verify(email, "login", request.data.get("code"))
        if not ok:
            return Response({"detail": msg}, status=400)
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            return Response({"detail": "Account not found."}, status=404)
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
            after_verified(user)
        return Response(tokens_for(user))


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        if User.objects.filter(email=email, is_active=True).exists():
            ok, msg = issue_and_send(email, "reset")
            if not ok:
                return Response({"detail": msg}, status=429)
        return Response({"detail": "If that email has an account, a reset code is on its way."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = clean_email(request.data.get("email"))
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            return Response({"detail": "That code does not match."}, status=400)
        password = request.data.get("password") or ""
        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)
        ok, msg = EmailOTP.verify(email, "reset", request.data.get("code"))
        if not ok:
            return Response({"detail": msg}, status=400)
        user.set_password(password)
        user.email_verified = True
        user.save()
        return Response(tokens_for(user))


class LogoutView(APIView):
    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh")).blacklist()
        except (TokenError, Exception):
            pass
        return Response(status=204)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request):
        """Permanently deletes the account and every record tied to it."""
        if not request.user.check_password(request.data.get("password") or ""):
            return Response({"detail": "Password is not right."}, status=400)
        with transaction.atomic():
            request.user.delete()
        return Response(status=204)


class ChangePasswordView(APIView):
    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get("current") or ""):
            return Response({"detail": "Current password is not right."}, status=400)
        try:
            password_validation.validate_password(request.data.get("password") or "", user)
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)
        user.set_password(request.data["password"])
        user.save()
        return Response(tokens_for(user))
