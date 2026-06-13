import io
import os
import threading
import numpy as np
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from autenticacion.permisos import EsAdmin
from .models import Camara, ZonaRoi
from .serializers import CamaraSerializer, ZonaRoiSerializer


# ─────────────────────────────────────────────
# ViewSets existentes
# ─────────────────────────────────────────────

class CamaraViewSet(viewsets.ModelViewSet):
    """US-04: CRUD cámaras (admin). US-11: lista activas (guardia)."""
    serializer_class   = CamaraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Camara.objects.prefetch_related("zonas_roi").all()
        condominio_id = self.request.query_params.get("condominio")
        if condominio_id:
            qs = qs.filter(condominio_id=condominio_id)
        solo_activas = self.request.query_params.get("activas")
        if solo_activas:
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [EsAdmin()]
        return [IsAuthenticated()]


class ZonaRoiViewSet(viewsets.ModelViewSet):
    """US-03: Definir regiones de interés (ROI) por cámara."""
    serializer_class   = ZonaRoiSerializer
    permission_classes = [EsAdmin]

    def get_queryset(self):
        qs = ZonaRoi.objects.select_related("camara").all()
        camara_id = self.request.query_params.get("camara")
        if camara_id:
            qs = qs.filter(camara_id=camara_id)
        return qs


# ─────────────────────────────────────────────
# MJPEG Stream proxy (RTSP → navegador)
# ─────────────────────────────────────────────

# Forzar transporte TCP para RTSP: la mayoría de apps de cámara para
# celular y routers WiFi no soportan/permiten el RTP por UDP (default
# de FFmpeg), lo que hace que cv2.VideoCapture() falle silenciosamente.
os.environ.setdefault(
    'OPENCV_FFMPEG_CAPTURE_OPTIONS',
    'rtsp_transport;tcp|stimeout;5000000|timeout;5000000'
)


def _generar_frames(rtsp_url: str):
    """Genera frames MJPEG desde una URL RTSP/HTTP via OpenCV."""
    try:
        import cv2
    except ImportError:
        return

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
            if not ok:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   buf.tobytes() + b'\r\n')
    finally:
        cap.release()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stream_camara(request, pk):
    """Proxy MJPEG: GET /api/camaras/<id>/stream/?token=<jwt>"""
    try:
        camara = Camara.objects.get(pk=pk)
    except Camara.DoesNotExist:
        return Response({'error': 'Cámara no encontrada'}, status=404)

    resp = StreamingHttpResponse(
        _generar_frames(camara.rtsp_url),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )
    resp['Cache-Control'] = 'no-cache'
    resp['Access-Control-Allow-Origin'] = '*'
    return resp


# ─────────────────────────────────────────────
# Probar conexión RTSP
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def probar_conexion(request):
    """Prueba si una URL RTSP es accesible. Body: { rtsp_url }"""
    url = request.data.get('rtsp_url', '').strip()
    if not url:
        return Response({'ok': False, 'mensaje': 'URL requerida'}, status=400)
    try:
        import cv2
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap.release()
            return Response({'ok': False, 'mensaje': 'No se pudo conectar (revisa IP/puerto, que el celular esté en la misma red WiFi y que la app de cámara esté abierta)'})
        ret, _ = cap.read()
        cap.release()
        if ret:
            return Response({'ok': True, 'mensaje': 'Conexión exitosa'})
        return Response({'ok': False, 'mensaje': 'Conectó al servidor pero no llegó video (revisa usuario/contraseña/ruta del stream)'})
    except ImportError:
        return Response({'ok': False, 'mensaje': 'OpenCV no disponible en el servidor'})
    except Exception as e:
        return Response({'ok': False, 'mensaje': str(e)})


# ─────────────────────────────────────────────
# Análisis IA de frame / imagen
# ─────────────────────────────────────────────

_yolo_model  = None
_yolo_cargando = False
_yolo_lock   = threading.Lock()


def _cargar_modelo():
    global _yolo_model, _yolo_cargando
    with _yolo_lock:
        if _yolo_model is not None or _yolo_cargando:
            return _yolo_model
        ruta = getattr(settings, 'YOLO_MODEL_PATH', '')
        if not ruta:
            return None
        _yolo_cargando = True
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO(ruta)
            print(f"[SIVIC] Modelo YOLO cargado: {ruta}")
        except Exception as e:
            print(f"[SIVIC] Error cargando modelo YOLO: {e}")
        finally:
            _yolo_cargando = False
    return _yolo_model


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analizar_frame(request):
    """
    Analiza una imagen con el modelo YOLO entrenado.
    Body: multipart/form-data con campo 'imagen' (archivo jpg/png).
    Devuelve: { detecciones: [{clase, confianza, bbox:{x,y,w,h}}] }
    Todos los valores de bbox están normalizados 0-1.
    """
    archivo = request.FILES.get('imagen')
    if not archivo:
        return Response({'error': 'Campo "imagen" requerido'}, status=400)

    model = _cargar_modelo()
    if model is None:
        # Sin modelo: devuelve array vacío (no error fatal)
        return Response({'detecciones': [], 'aviso': 'YOLO_MODEL_PATH no configurado'})

    try:
        import cv2
        datos  = np.frombuffer(archivo.read(), dtype=np.uint8)
        frame  = cv2.imdecode(datos, cv2.IMREAD_COLOR)
        if frame is None:
            return Response({'error': 'Imagen inválida'}, status=400)

        resultados  = model(frame, verbose=False)[0]
        h, w        = frame.shape[:2]
        detecciones = []

        for box in resultados.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detecciones.append({
                'clase':      resultados.names[int(box.cls[0])],
                'confianza':  round(float(box.conf[0]), 3),
                'bbox': {
                    'x': x1 / w,
                    'y': y1 / h,
                    'w': (x2 - x1) / w,
                    'h': (y2 - y1) / h,
                },
            })

        return Response({'detecciones': detecciones})

    except ImportError:
        return Response({'detecciones': [], 'aviso': 'OpenCV no disponible'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
