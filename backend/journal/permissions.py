from rest_framework.permissions import SAFE_METHODS, BasePermission


class JournalPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in {"admin", "teacher"}

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        offering = getattr(obj, "offering", None)
        if offering is None and hasattr(obj, "session"):
            offering = obj.session.offering
        if request.user.role == "teacher":
            return bool(offering and offering.teacher.user_id == request.user.id)
        if request.user.role == "student" and request.method in SAFE_METHODS:
            student = getattr(obj, "student", None)
            return student is None or student.user_id == request.user.id
        return False


class AdminWritePolicyPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.role == "admin"

