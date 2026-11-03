"""Transactional email through SendGrid's v3 API. Falls back to the log in development."""
import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

SUBJECTS = {
    "signup": "Your Ruvia verification code",
    "login": "Your Ruvia sign in code",
    "reset": "Reset your Ruvia password",
}
LINES = {
    "signup": "Welcome to Ruvia. Use this code to confirm your email.",
    "login": "Use this code to sign in to Ruvia.",
    "reset": "Use this code to set a new password. If you did not ask for this, you can ignore this email.",
}


def _wrap(heading, body_html):
    return f"""
<div style="background:#F3EDE3;padding:32px 16px;font-family:Helvetica,Arial,sans-serif;color:#1F1C17">
  <div style="max-width:460px;margin:0 auto;background:#FBF8F2;border-radius:20px;padding:32px;border:1px solid #E0D6C5">
    <div style="font-family:Georgia,serif;font-size:26px;color:#56664A;margin-bottom:20px">Ruvia</div>
    <h1 style="font-family:Georgia,serif;font-weight:500;font-size:22px;margin:0 0 12px">{heading}</h1>
    {body_html}
    <p style="font-size:12px;color:#8C8273;margin-top:28px">Ruvia, a small health diary for the people you love.</p>
  </div>
</div>"""


def send_email(to, subject, html, text):
    if not settings.SENDGRID_API_KEY:
        log.warning("SENDGRID_API_KEY not set. Email to %s not sent. Subject: %s. Text: %s", to, subject, text)
        return False
    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": settings.SENDGRID_FROM_NAME},
                "subject": subject,
                "content": [{"type": "text/plain", "value": text}, {"type": "text/html", "value": html}],
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            log.error("SendGrid error %s: %s", resp.status_code, resp.text[:300])
            return False
        return True
    except requests.RequestException as exc:
        log.error("SendGrid request failed: %s", exc)
        return False


def send_otp(email, code, purpose):
    line = LINES.get(purpose, LINES["login"])
    html = _wrap(
        "Your code",
        f"""<p style="font-size:15px;line-height:1.5;color:#5B5347">{line}</p>
        <div style="font-size:34px;letter-spacing:10px;font-weight:700;background:#DDE3D0;color:#2F3A27;
        border-radius:14px;padding:16px;text-align:center;margin:20px 0">{code}</div>
        <p style="font-size:13px;color:#8C8273">The code works for 10 minutes.</p>""",
    )
    text = f"{line}\n\nCode: {code}\n\nThe code works for 10 minutes."
    return send_email(email, SUBJECTS.get(purpose, "Your Ruvia code"), html, text)


def send_invite(email, inviter_name):
    link = f"{settings.FRONTEND_URL}/signup?email={email}"
    html = _wrap(
        f"{inviter_name} invited you to their care circle",
        f"""<p style="font-size:15px;line-height:1.5;color:#5B5347">{inviter_name} uses Ruvia to keep a small daily
        health diary and would like you in their care circle. You choose what you share, and you can change it any time.</p>
        <p style="margin:24px 0"><a href="{link}" style="background:#56664A;color:#fff;text-decoration:none;
        padding:12px 20px;border-radius:999px;font-weight:600">Join Ruvia</a></p>""",
    )
    text = f"{inviter_name} invited you to their Ruvia care circle. Join here: {link}"
    return send_email(email, f"{inviter_name} invited you to Ruvia", html, text)
