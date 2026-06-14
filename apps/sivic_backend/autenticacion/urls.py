from django.urls import path
from . import views

urlpatterns = [
    path("login/",    views.login),
    path("registro/", views.registro),
    path("yo/",       views.yo),
    path("usuarios/",              views.listar_usuarios),
    path("usuarios/<int:uid>/",    views.gestionar_usuario),
]
