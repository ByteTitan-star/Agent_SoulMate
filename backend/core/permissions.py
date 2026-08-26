from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """仅允许 is_admin=True 的用户访问"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)
