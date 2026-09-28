from django.db.models import Count, Q
from rest_framework import viewsets

from .models import Faculty, Group, Program, Room, Student, Subject, Teacher
from .permissions import AdminWritePermission
from .serializers import FacultySerializer, GroupSerializer, ProgramSerializer, RoomSerializer, StudentSerializer, SubjectSerializer, TeacherSerializer


class AcademicModelViewSet(viewsets.ModelViewSet):
    permission_classes = [AdminWritePermission]


class FacultyViewSet(AcademicModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    search_fields = ("code", "name_tj", "name_ru", "name_en")
    ordering_fields = ("code", "name_ru")


class ProgramViewSet(AcademicModelViewSet):
    queryset = Program.objects.select_related("faculty")
    serializer_class = ProgramSerializer
    filterset_fields = ("faculty", "degree")
    search_fields = ("code", "name_tj", "name_ru", "name_en")


class GroupViewSet(AcademicModelViewSet):
    serializer_class = GroupSerializer
    filterset_fields = ("program", "course", "is_active")
    search_fields = ("code", "program__name_tj", "program__name_ru", "program__name_en")
    ordering_fields = ("code", "course", "admission_year")

    def get_queryset(self):
        user = self.request.user
        queryset = Group.objects.select_related("program", "curator__user").annotate(student_count=Count("students", filter=Q(students__status="active")))
        if user.role == "teacher":
            return queryset.filter(Q(offerings__teacher__user=user) | Q(curator__user=user)).distinct()
        if user.role == "student":
            return queryset.filter(students__user=user)
        return queryset


class RoomViewSet(AcademicModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    search_fields = ("code", "building")
    ordering_fields = ("building", "code", "capacity")


class SubjectViewSet(AcademicModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    search_fields = ("code", "name_tj", "name_ru", "name_en")
    ordering_fields = ("code", "name_ru", "credits")


class StudentViewSet(AcademicModelViewSet):
    serializer_class = StudentSerializer
    filterset_fields = ("group", "status")
    search_fields = ("student_id", "user__first_name", "user__last_name", "user__email", "group__code")
    ordering_fields = ("student_id", "user__last_name", "admission_date")

    def get_queryset(self):
        queryset = Student.objects.select_related("user", "group").prefetch_related("movements__author")
        user = self.request.user
        if user.role == "student":
            return queryset.filter(user=user)
        if user.role == "teacher":
            return queryset.filter(group__offerings__teacher__user=user).distinct()
        return queryset


class TeacherViewSet(AcademicModelViewSet):
    serializer_class = TeacherSerializer
    filterset_fields = ("faculty",)
    search_fields = ("employee_id", "user__first_name", "user__last_name", "user__email")

    def get_queryset(self):
        queryset = Teacher.objects.select_related("user", "faculty")
        if self.request.user.role == "teacher":
            return queryset.filter(user=self.request.user)
        return queryset

