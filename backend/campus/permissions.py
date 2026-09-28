from rest_framework.permissions import SAFE_METHODS, BasePermission


class AcademicContentPermission(BasePermission):
    def has_permission(self, request, view):
        if getattr(view, "action", None) == "submit" and request.user.role == "student":
            return True
        return request.method in SAFE_METHODS or request.user.role in {"admin", "teacher"}

    def has_object_permission(self, request, view, obj):
        if getattr(view, "action", None) == "submit" and request.user.role == "student":
            return True
        if request.method in SAFE_METHODS or request.user.role == "admin":
            return True
        offering = getattr(obj, "offering", None)
        if offering is None and hasattr(obj, "assignment"):
            offering = obj.assignment.offering
        return request.user.role == "teacher" and offering and offering.teacher.user_id == request.user.id


class AdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "admin"
