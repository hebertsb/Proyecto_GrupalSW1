import json
import jwt
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer

GRUPO_ALERTAS = "sivic_alertas"


class AlertasConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        token = self._token_query()
        if not self._token_valido(token):
            await self.close(code=4001)
            return
        await self.channel_layer.group_add(GRUPO_ALERTAS, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GRUPO_ALERTAS, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass  # clientes no envían mensajes al servidor

    # Handler que channels invoca cuando llega un mensaje al grupo
    async def nueva_alerta(self, event):
        await self.send(text_data=json.dumps({
            "tipo":          "alerta",
            "evento_id":     event["evento_id"],
            "camara_nombre": event["camara_nombre"],
            "regla_nombre":  event["regla_nombre"],
            "confianza_ia":  event["confianza_ia"],
            "timestamp":     event["timestamp"],
            "imagen_url":    event.get("imagen_url", ""),
        }))

    # ── helpers ──────────────────────────────────────────────────────────────

    def _token_query(self) -> str:
        qs = self.scope.get("query_string", b"").decode()
        for parte in qs.split("&"):
            if parte.startswith("token="):
                return parte[6:]
        return ""

    def _token_valido(self, token: str) -> bool:
        if not token:
            return False
        try:
            jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return True
        except Exception:
            return False
