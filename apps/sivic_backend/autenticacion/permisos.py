from rest_framework.permissions import BasePermission


class EsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "rol", None) == "superadmin")


class EsAdmin(BasePermission):
    """Admin del condominio. SuperAdmin también puede hacer todo lo que hace un Admin."""
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "rol", None) in ("admin", "superadmin"))


class EsGuardia(BasePermission):
    """Cualquier usuario autenticado con rol válido."""
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "rol", None) in ("admin", "guardia", "superadmin"))
