import jwt
import os
import datetime
from django.contrib.auth.hashers import check_password, make_password
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Usuario
from .serializers import UsuarioSerializer, RegistroSerializer
from .permisos import EsAdmin
from condominios.models import Condominio, Plan
from pagos import services_stripe as stripe_svc


def _generar_token(usuario):
    payload = {
        "usuario_id": usuario.usuario_id,
        "email":      usuario.email,
        "rol":        usuario.rol,
        "exp":        datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, os.environ.get("SECRET_KEY", ""), algorithm="HS256")


@extend_schema(
    tags=["Autenticación"],
    summary="Iniciar sesión",
    description="Devuelve un JWT válido por 7 días. Incluir en cabecera: `Authorization: Bearer <token>`",
    request={"application/json": {"example": {"email": "admin@sivic.com", "password": "secret123"}}},
    responses={200: UsuarioSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email    = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    try:
        usuario = Usuario.objects.get(email=email)
    except Usuario.DoesNotExist:
        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

    if not check_password(password, usuario.password_hash):
        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

    token = _generar_token(usuario)
    return Response({"access": token, "usuario": UsuarioSerializer(usuario).data})


@extend_schema(
    tags=["Autenticación"],
    summary="Registrar usuario",
    description="Crea un nuevo usuario (admin o guardia). Solo usar en setup inicial o por admin.",
    request=RegistroSerializer,
    responses={201: UsuarioSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def registro(request):
    ser = RegistroSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    if Usuario.objects.filter(email=d["email"]).exists():
        return Response({"error": "Email ya registrado"}, status=status.HTTP_400_BAD_REQUEST)

    usuario = Usuario.objects.create(
        nombre        = d["nombre"],
        email         = d["email"],
        password_hash = make_password(d["password"]),
        rol           = d["rol"],
    )
    token = _generar_token(usuario)
    return Response({"access": token, "usuario": UsuarioSerializer(usuario).data}, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Autenticación"],
    summary="Perfil del usuario autenticado",
    description="Retorna los datos del usuario cuyo token JWT está en la cabecera.",
    responses={200: UsuarioSerializer},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def yo(request):
    return Response(UsuarioSerializer(request.user).data)


@extend_schema(
    tags=["Autenticación"],
    summary="Listar usuarios",
    description="Lista todos los usuarios. Filtra por rol con `?rol=guardia` o `?rol=admin`. Solo admin.",
    responses={200: UsuarioSerializer(many=True)},
)
@api_view(["GET", "POST"])
@permission_classes([EsAdmin])
def listar_usuarios(request):
    if request.method == "POST":
        ser = RegistroSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if Usuario.objects.filter(email=d["email"]).exists():
            return Response({"error": "Email ya registrado"}, status=status.HTTP_400_BAD_REQUEST)
        usuario = Usuario.objects.create(
            nombre        = d["nombre"],
            email         = d["email"],
            password_hash = make_password(d["password"]),
            rol           = d.get("rol", "guardia"),
        )
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)

    rol = request.query_params.get("rol")
    qs  = Usuario.objects.all()
    if rol:
        qs = qs.filter(rol=rol)
    return Response(UsuarioSerializer(qs, many=True).data)


@api_view(["PATCH", "DELETE"])
@permission_classes([EsAdmin])
def gestionar_usuario(request, uid):
    try:
        usuario = Usuario.objects.get(pk=uid)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        usuario.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if "nombre" in request.data:
        usuario.nombre = request.data["nombre"]
    if "email" in request.data:
        if Usuario.objects.filter(email=request.data["email"]).exclude(pk=uid).exists():
            return Response({"error": "Email ya registrado"}, status=status.HTTP_400_BAD_REQUEST)
        usuario.email = request.data["email"]
    if request.data.get("password"):
        usuario.password_hash = make_password(request.data["password"])
    usuario.save()
    return Response(UsuarioSerializer(usuario).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def registro_completo(request):
    """
    Registro SaaS: crea admin + condominio + inicia Stripe Checkout.
    Body: { nombre, email, password, nombre_condominio, ubicacion, plan_id, url_exito, url_cancelacion }
    """
    nombre            = request.data.get("nombre", "").strip()
    email             = request.data.get("email", "").strip()
    password          = request.data.get("password", "")
    nombre_condominio = request.data.get("nombre_condominio", "").strip()
    ubicacion         = request.data.get("ubicacion", "").strip()
    plan_id           = request.data.get("plan_id")
    url_exito         = request.data.get("url_exito", "")
    url_cancelacion   = request.data.get("url_cancelacion", "")

    if not all([nombre, email, password, nombre_condominio, plan_id]):
        return Response(
            {"error": "Campos requeridos: nombre, email, password, nombre_condominio, plan_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response({"error": "La contraseña debe tener al menos 8 caracteres."}, status=status.HTTP_400_BAD_REQUEST)

    if Usuario.objects.filter(email=email).exists():
        return Response({"error": "El email ya está registrado."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({"error": "Plan no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if not plan.stripe_precio_id:
        return Response({"error": "El plan no tiene precio configurado en Stripe."}, status=status.HTTP_400_BAD_REQUEST)

    # Crear condominio y admin
    condominio = Condominio.objects.create(nombre=nombre_condominio, ubicacion=ubicacion or None)
    usuario    = Usuario.objects.create(
        nombre=nombre,
        email=email,
        password_hash=make_password(password),
        rol="admin",
        condominio=condominio,
    )

    # Crear sesión Stripe Checkout
    try:
        sesion = stripe_svc.crear_checkout_session(
            condominio,
            plan,
            url_exito   or f"{os.getenv('FRONTEND_URL','http://localhost:4200')}/login?pago=ok",
            url_cancelacion or f"{os.getenv('FRONTEND_URL','http://localhost:4200')}/login?pago=cancelado",
        )
    except Exception as e:
        # Si Stripe falla, eliminar lo creado para no dejar datos huérfanos
        usuario.delete()
        condominio.delete()
        return Response({"error": f"Error al crear sesión de pago: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    token = _generar_token(usuario)
    return Response({
        "access":       token,
        "usuario":      UsuarioSerializer(usuario).data,
        "checkout_url": sesion.url,
    }, status=status.HTTP_201_CREATED)
