"""
=========================================================
AIMeals Backend
Email Sending (Gmail SMTP)

Responsibilities:
    - Send the OTP signup email via Gmail SMTP + an app
      password

Dependencies:
    - app.A_config.settings (GMAIL_ADDRESS, GMAIL_APP_PASSWORD
      — see notes below, these must be added to your actual
      settings class + .env)
    - app.C_logger.app_logger

Notes:
    - REQUIRES two new settings this session never had access
      to your real app/A_config.py to add safely:
        GMAIL_ADDRESS = "aimeals2024@gmail.com"
        GMAIL_APP_PASSWORD = "<16-character app password>"
      Add both as environment-variable-backed settings
      matching however CLAUDE_API_KEY is already defined
      there, and add the real values to your .env file. This
      module will raise a clear AttributeError on first use
      if they're missing, rather than fail silently.
    - Uses Gmail's SMTP relay (smtp.gmail.com:587, STARTTLS)
      with an app password — not OAuth/the Gmail API. See the
      earlier discussion in this conversation for why: this is
      simpler for a personal (non-Workspace) Gmail account and
      sufficient at this app's current email volume.
    - Deliberately narrow: this module only knows how to send
      the OTP email. If AIMeals ever needs other transactional
      emails (password reset, etc.), add functions here rather
      than growing a single generic "send any email" function.

Example usage:
    from app.core.email import send_otp_email

    send_otp_email("user@example.com", "482913", "Sunil")
=========================================================
"""

import smtplib
from email.mime.text import MIMEText

from app.A_config import settings
from app.C_logger import app_logger


def send_otp_email(to_email: str, otp_code: str, first_name: str) -> None:
    """
    Sends the AIMeals signup verification code to to_email.

    Raises whatever smtplib raises on failure (connection
    error, auth failure, etc.) — the caller
    (AuthService.request_signup_otp()) does not currently
    catch this, so a send failure surfaces as a 500 rather
    than silently pretending the email went out. Revisit if
    you want a friendlier "email service temporarily
    unavailable" response instead.
    """
    subject = "Your AIMeals verification code"
    body = (
        f"Hi {first_name},\n\n"
        f"Your AIMeals verification code is: {otp_code}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, "
        f"you can safely ignore this email.\n\n"
        f"— The AIMeals Team"
    )

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.GMAIL_ADDRESS
    message["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_ADDRESS, [to_email], message.as_string())
    except Exception as e:
        app_logger.exception(f"Failed to send OTP email to {to_email}: {e}")
        raise