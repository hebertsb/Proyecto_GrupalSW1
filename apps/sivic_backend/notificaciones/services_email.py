"""
Reutilizado del viejo backend SmartCondominium.
Envía emails via Resend.
"""
import os
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM    = os.environ.get("RESEND_FROM", "onboarding@resend.dev")


def send_email(to_emails, subject: str, html: str):
    if not RESEND_API_KEY:
        raise RuntimeError("Falta RESEND_API_KEY en .env")

    if isinstance(to_emails, str):
        to_emails = [to_emails]

    resend.api_key = RESEND_API_KEY
    try:
        resend.Emails.send({
            "from":    RESEND_FROM,
            "to":      to_emails,
            "subject": subject,
            "html":    html,
        })
        return 200
    except Exception as e:
        print(f"Error email Resend: {e}")
        raise
