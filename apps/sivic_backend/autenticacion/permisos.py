from rest_framework.permissions import BasePermission


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "rol", None) == "admin")


class EsGuardia(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "rol", None) in ("admin", "guardia"))
