"""
Reutilizado del viejo backend SmartCondominium.
Envía notificaciones push via Firebase Cloud Messaging (FCM).
"""
import os
import json
import firebase_admin
from firebase_admin import messaging, credentials

_CHANNEL_ID = "high_importance_channel"


def _ensure_init():
    if not firebase_admin._apps:
        raw  = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        info = json.loads(raw) if raw else {}
        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred)


def send_token(token: str, title: str, body: str, data: dict | None = None):
    _ensure_init()
    data = {str(k): str(v) for k, v in (data or {}).items()}
    data.setdefault("click_action", "FLUTTER_NOTIFICATION_CLICK")

    msg = messaging.Message(
        token        = token,
        notification = messaging.Notification(title=title or "Alerta SIVIC", body=body or ""),
        data         = data,
        android      = messaging.AndroidConfig(
            priority     = "high",
            notification = messaging.AndroidNotification(
                sound      = "default",
                channel_id = _CHANNEL_ID,
                priority   = "max",
            ),
        ),
        apns = messaging.APNSConfig(
            headers = {"apns-priority": "10"},
            payload = messaging.APNSPayload(aps=messaging.Aps(sound="default")),
        ),
    )
    return messaging.send(msg)
