from rest_framework.permissions import SAFE_METHODS, BasePermission


class AdminWritePermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.role == "admin"


class AdminOnlyPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "admin"

