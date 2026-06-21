from rest_framework.permissions import BasePermission


def filtrar_por_condominio(qs, request, campo="condominio_id"):
    """Restringe el queryset al condominio del usuario cuando es admin o guardia."""
    rol = getattr(request.user, "rol", None)
    if rol in ("admin", "guardia"):
        cid = getattr(request.user, "condominio_id", None)
        if cid:
            return qs.filter(**{campo: cid})
    return qs


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
