import io
import json
import os
import threading
import requests as req_ext
import numpy as np
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from autenticacion.permisos import EsAdmin
from .models import Camara, ZonaRoi, PlanoCondominio, PosicionCamara
from .serializers import CamaraSerializer, ZonaRoiSerializer, PlanoCondominioSerializer, PosicionCamaraSerializer

SIVIC_IA_URL = os.getenv("SIVIC_IA_URL", "http://127.0.0.1:8002")


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analizar_frame_persona(request):
    """
    Analiza una imagen/frame con el microservicio entrenamientopersona.
    Usado para modo archivo (video/imagen subida por el usuario).
    Body: multipart/form-data con campo 'imagen'.
    """
    archivo = request.FILES.get('imagen')
    if not archivo:
        return Response({'error': 'Campo "imagen" requerido'}, status=400)

    try:
        import cv2
        datos = np.frombuffer(archivo.read(), dtype=np.uint8)
        frame = cv2.imdecode(datos, cv2.IMREAD_COLOR)
        if frame is None:
            return Response({'error': 'Imagen inválida'}, status=400)
        h, w = frame.shape[:2]
        if w > 640:
            frame = cv2.resize(frame, (640, int(h * 640 / w)))
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok:
            return Response({'error': 'Error al codificar imagen'}, status=500)
    except ImportError:
        return Response({'error': 'OpenCV no disponible'}, status=503)

    try:
        resp = req_ext.post(
            f"{SIVIC_IA_URL}/api/analizar",
            files={'file': ('frame.jpg', buf.tobytes(), 'image/jpeg')},
            data={'camara_id': 0, 'umbral_merodeo': 999},
            timeout=5,
        )
        return Response(resp.json())
    except req_ext.exceptions.ConnectionError:
        return Response({'error': 'Microservicio IA no disponible'}, status=503)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analizar_ia(request, pk):
    """
    Captura un frame de la cámara, lo envía al microservicio entrenamientopersona
    y devuelve las detecciones de personas/vehículos + alertas de reglas.

    POST /api/camaras/<id>/analizar_ia/
    Body opcional: { umbral_merodeo: 30 }
    """
    try:
        camara = Camara.objects.prefetch_related("zonas_roi").get(pk=pk)
    except Camara.DoesNotExist:
        return Response({'error': 'Cámara no encontrada'}, status=404)

    try:
        import cv2
    except ImportError:
        return Response({'error': 'OpenCV no disponible'}, status=503)

    # Capturar un frame de la cámara
    cap = cv2.VideoCapture(camara.rtsp_url, cv2.CAP_FFMPEG)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return Response({'error': 'No se pudo capturar frame de la cámara'}, status=503)

    # Redimensionar a 640px de ancho para acelerar inferencia
    h, w = frame.shape[:2]
    if w > 640:
        frame = cv2.resize(frame, (640, int(h * 640 / w)))

    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok:
        return Response({'error': 'Error al codificar frame'}, status=500)

    # Preparar zonas ROI para el microservicio
    zonas = [
        {
            'nombre':     z.tipo_zona,
            'puntos':     z.poligono_coordenadas,
            'normalizado': True,
        }
        for z in camara.zonas_roi.all()
    ]

    umbral_merodeo = request.data.get('umbral_merodeo', 30)

    try:
        resp = req_ext.post(
            f"{SIVIC_IA_URL}/api/analizar",
            files={'file': ('frame.jpg', buf.tobytes(), 'image/jpeg')},
            data={
                'camara_id':      camara.camara_id,
                'zonas_json':     json.dumps(zonas),
                'umbral_merodeo': umbral_merodeo,
            },
            timeout=5,
        )
        resultado = resp.json()
    except req_ext.exceptions.ConnectionError:
        return Response({'error': 'Microservicio IA no disponible (puerto 8002)'}, status=503)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

    # Mapear alertas a regla_id buscando por nombre en la tabla reglas_infraccion
    # El admin crea las reglas con estos nombres_regla en el panel web
    _MAPA_ALERTAS = {
        'zona_restringida_persona': 'persona_zona_restringida',
        'merodeo':                  'merodeo',
        'vehiculo_zona_restringida':'vehiculo_no_autorizado',
        'personas_peleando':        'personas_peleando',
        'caida_persona':            'caida_persona',
        'intrusion_nocturna':       'intrusion_nocturna',
        'acceso_fuera_horario':     'acceso_fuera_horario',
    }

    from reglas.models import ReglaInfraccion
    from eventos.services_ia import registrar_deteccion

    for alerta in resultado.get('alertas', []):
        nombre_regla = _MAPA_ALERTAS.get(alerta)
        if not nombre_regla:
            continue
        try:
            regla = ReglaInfraccion.objects.get(nombre_regla=nombre_regla)
            det   = next(
                (d for d in resultado.get('detalle_alertas', []) if d.get('tipo') == alerta),
                {}
            )
            confianza = det.get('confianza', 0.80)
            registrar_deteccion(camara.camara_id, regla.regla_id, confianza)
        except ReglaInfraccion.DoesNotExist:
            pass  # Regla no creada aún en el panel

    return Response(resultado)


# ─────────────────────────────────────────────
# Planos del condominio
# ─────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def planos_list(request):
    """
    GET  /api/planos/              — lista planos (filtra por ?condominio=<id>)
    POST /api/planos/              — crea plano y sube imagen al bucket sivic-planos
         multipart: imagen (jpg/jpeg/png), nombre, condominio_id
    """
    if request.method == 'GET':
        qs = PlanoCondominio.objects.prefetch_related('posiciones__camara').all()
        condominio_id = request.query_params.get('condominio')
        if condominio_id:
            qs = qs.filter(condominio_id=condominio_id)
        return Response(PlanoCondominioSerializer(qs, many=True).data)

    # POST ─────────────────────────────────────
    archivo      = request.FILES.get('imagen')
    nombre       = request.data.get('nombre', 'Plano Principal')
    condominio_id = request.data.get('condominio_id')

    if not archivo or not condominio_id:
        return Response({'error': 'Campos requeridos: imagen, condominio_id'}, status=400)

    ext = archivo.name.rsplit('.', 1)[-1].lower() if '.' in archivo.name else ''
    if ext not in ('jpg', 'jpeg', 'png'):
        return Response({'error': 'Solo se aceptan imágenes JPG, JPEG o PNG'}, status=400)

    content_type = 'image/png' if ext == 'png' else 'image/jpeg'
    file_path    = f"planos/{condominio_id}/{archivo.name}"
    bucket       = 'sivic-planos'
    supa_url     = settings.SUPABASE_URL.rstrip('/')
    supa_key     = settings.SUPABASE_SERVICE_KEY.strip()

    try:
        upload = req_ext.post(
            f"{supa_url}/storage/v1/object/{bucket}/{file_path}",
            headers={
                'Authorization': f'Bearer {supa_key}',
                'apikey':        supa_key,
                'Content-Type':  content_type,
                'x-upsert':      'true',
            },
            data=archivo.read(),
            timeout=30,
        )
        if upload.status_code not in (200, 201):
            return Response({'error': f'Error al subir imagen: {upload.text}'}, status=500)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

    imagen_url = f"{supa_url}/storage/v1/object/public/{bucket}/{file_path}"

    from condominios.models import Condominio
    try:
        condominio = Condominio.objects.get(pk=condominio_id)
    except Condominio.DoesNotExist:
        return Response({'error': 'Condominio no encontrado'}, status=404)

    plano = PlanoCondominio.objects.create(
        condominio=condominio,
        nombre=nombre,
        imagen_url=imagen_url,
    )
    return Response(PlanoCondominioSerializer(plano).data, status=201)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def plano_detail(request, pk):
    try:
        plano = PlanoCondominio.objects.prefetch_related('posiciones__camara').get(pk=pk)
    except PlanoCondominio.DoesNotExist:
        return Response({'error': 'Plano no encontrado'}, status=404)

    if request.method == 'GET':
        return Response(PlanoCondominioSerializer(plano).data)

    plano.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def posiciones_list(request, plano_pk):
    """
    GET  — lista posiciones del plano
    POST — crea o actualiza posición: { camara_id, pos_x, pos_y }
    """
    try:
        plano = PlanoCondominio.objects.get(pk=plano_pk)
    except PlanoCondominio.DoesNotExist:
        return Response({'error': 'Plano no encontrado'}, status=404)

    if request.method == 'GET':
        qs = PosicionCamara.objects.filter(plano=plano).select_related('camara')
        return Response(PosicionCamaraSerializer(qs, many=True).data)

    camara_id = request.data.get('camara_id')
    pos_x     = request.data.get('pos_x')
    pos_y     = request.data.get('pos_y')

    if camara_id is None or pos_x is None or pos_y is None:
        return Response({'error': 'Campos requeridos: camara_id, pos_x, pos_y'}, status=400)

    try:
        camara = Camara.objects.get(pk=camara_id)
    except Camara.DoesNotExist:
        return Response({'error': 'Cámara no encontrada'}, status=404)

    posicion, created = PosicionCamara.objects.update_or_create(
        plano=plano, camara=camara,
        defaults={'pos_x': pos_x, 'pos_y': pos_y},
    )
    return Response(PosicionCamaraSerializer(posicion).data, status=201 if created else 200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def posicion_detail(request, plano_pk, camara_pk):
    try:
        pos = PosicionCamara.objects.get(plano_id=plano_pk, camara_id=camara_pk)
        pos.delete()
        return Response(status=204)
    except PosicionCamara.DoesNotExist:
        return Response({'error': 'Posición no encontrada'}, status=404)
